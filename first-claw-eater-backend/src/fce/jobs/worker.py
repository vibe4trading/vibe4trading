from __future__ import annotations

import os
import socket
import threading
import time
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fce.contracts.events import make_event_v1
from fce.contracts.payloads import RunFailedPayloadV1
from fce.db.engine import get_engine, new_session
from fce.db.event_store import append_event
from fce.db.init_db import init_db
from fce.db.models import DatasetRow, JobRow, RunRow
from fce.jobs.handlers import (
    handle_dataset_import_job,
    handle_run_execute_live_job,
    handle_run_execute_replay_job,
)
from fce.jobs.types import (
    JOB_TYPE_DATASET_IMPORT,
    JOB_TYPE_RUN_EXECUTE_LIVE,
    JOB_TYPE_RUN_EXECUTE_REPLAY,
)
from fce.observability.logging import configure_logging
from fce.settings import get_settings


class _JobHeartbeater:
    def __init__(self, *, job_id, worker_id: str, interval_seconds: float) -> None:
        self.job_id = job_id
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        if self.interval_seconds <= 0:
            return
        self._thread.start()

    def stop(self) -> None:
        if self.interval_seconds <= 0:
            return
        self._stop.set()
        self._thread.join(timeout=self.interval_seconds * 2)

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            session = new_session()
            try:
                job = session.get(JobRow, self.job_id)
                if job is None:
                    return
                if job.status != "running" or job.locked_by != self.worker_id:
                    return

                now = datetime.now(UTC)
                job.heartbeat_at = now
                job.updated_at = now
                session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()


class JobWorker:
    def __init__(self, *, poll_seconds: float = 1.0) -> None:
        settings = get_settings()
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"
        self.log = structlog.get_logger("jobs.worker").bind(
            service="worker", worker_id=self.worker_id
        )
        self.poll_seconds = poll_seconds
        self.heartbeat_interval_seconds = float(settings.job_heartbeat_interval_seconds)
        self.stale_after_seconds = float(settings.job_stale_after_seconds)
        self.max_running_replay_jobs = int(settings.job_max_running_run_execute_replay)

        # Optional: restrict this worker to certain job types.
        raw = (settings.worker_job_types or "").strip()
        self.allowed_job_types: set[str] | None = (
            {t.strip() for t in raw.split(",") if t.strip()} if raw else None
        )

    def run_forever(self) -> None:
        engine = get_engine()
        init_db(engine)

        self.log.info(
            "worker_started",
            allowed_job_types=sorted(self.allowed_job_types) if self.allowed_job_types else None,
        )

        while True:
            did_work = self._try_process_one()
            if not did_work:
                time.sleep(self.poll_seconds)

    def _try_process_one(self) -> bool:
        session = new_session()
        try:
            self._recover_stale_jobs(session)
            job = self._claim_next_job(session)
            if job is None:
                return False

            self._execute_job(session, job)
            return True
        finally:
            session.close()

    def _recover_stale_jobs(self, session: Session) -> None:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=self.stale_after_seconds)

        stmt = (
            select(JobRow)
            .where(
                JobRow.status == "running",
                JobRow.heartbeat_at.is_not(None),
                JobRow.heartbeat_at < stale_before,
            )
            .order_by(JobRow.heartbeat_at)
            .with_for_update(skip_locked=True)
        )
        stale = list(session.execute(stmt).scalars().all())
        if not stale:
            session.rollback()
            return

        self.log.warning(
            "stale_jobs_recovered",
            count=len(stale),
            job_ids=[str(j.job_id) for j in stale[:10]],
        )

        for job in stale:
            job.last_error = (
                f"recovered stale lock (locked_by={job.locked_by}, heartbeat_at={job.heartbeat_at})"
            )
            job.locked_at = None
            job.locked_by = None
            job.heartbeat_at = None
            job.available_at = now
            job.updated_at = now

            if job.attempts >= job.max_attempts:
                job.status = "failed"
            else:
                job.status = "pending"

            # Best-effort: reflect the requeue in the parent entity status.
            if job.dataset_id is not None:
                ds = session.get(DatasetRow, job.dataset_id)
                if ds is not None and ds.status == "running":
                    ds.status = "pending"
                    ds.updated_at = now

            if job.run_id is not None:
                run = session.get(RunRow, job.run_id)
                if run is not None and run.status == "running":
                    run.status = "pending"
                    run.updated_at = now

        session.commit()

    def _claim_next_job(self, session: Session) -> JobRow | None:
        now = datetime.now(UTC)

        # Best-effort global cap for replay runs, so multiple workers don't pile up LLM calls.
        if self.max_running_replay_jobs > 0:
            running_replay = session.execute(
                select(func.count())
                .select_from(JobRow)
                .where(JobRow.status == "running", JobRow.job_type == JOB_TYPE_RUN_EXECUTE_REPLAY)
            ).scalar_one()
        else:
            running_replay = 0

        stmt = select(JobRow).where(JobRow.status == "pending", JobRow.available_at <= now)
        if self.allowed_job_types is not None:
            stmt = stmt.where(JobRow.job_type.in_(sorted(self.allowed_job_types)))
        if self.max_running_replay_jobs > 0 and running_replay >= self.max_running_replay_jobs:
            stmt = stmt.where(JobRow.job_type != JOB_TYPE_RUN_EXECUTE_REPLAY)

        stmt = stmt.order_by(JobRow.created_at).with_for_update(skip_locked=True).limit(1)
        job = session.execute(stmt).scalar_one_or_none()
        if job is None:
            session.rollback()
            return None

        job.status = "running"
        job.locked_at = now
        job.locked_by = self.worker_id
        job.heartbeat_at = now
        job.attempts += 1
        job.updated_at = now
        session.commit()

        self.log.info(
            "job_claimed",
            job_id=str(job.job_id),
            job_type=job.job_type,
            run_id=str(job.run_id) if job.run_id else None,
            dataset_id=str(job.dataset_id) if job.dataset_id else None,
            attempts=job.attempts,
        )
        return job

    def _execute_job(self, session: Session, job: JobRow) -> None:
        now = datetime.now(UTC)
        heartbeater = _JobHeartbeater(
            job_id=job.job_id,
            worker_id=self.worker_id,
            interval_seconds=self.heartbeat_interval_seconds,
        )
        heartbeater.start()
        try:
            self.log.info(
                "job_started",
                job_id=str(job.job_id),
                job_type=job.job_type,
                run_id=str(job.run_id) if job.run_id else None,
                dataset_id=str(job.dataset_id) if job.dataset_id else None,
            )
            if job.job_type == JOB_TYPE_DATASET_IMPORT:
                handle_dataset_import_job(session, job)
            elif job.job_type == JOB_TYPE_RUN_EXECUTE_REPLAY:
                handle_run_execute_replay_job(session, job)
            elif job.job_type == JOB_TYPE_RUN_EXECUTE_LIVE:
                handle_run_execute_live_job(session, job)
            else:
                raise ValueError(f"Unknown job_type={job.job_type}")

            job.status = "completed"
            job.updated_at = now
            session.commit()

            self.log.info(
                "job_completed",
                job_id=str(job.job_id),
                job_type=job.job_type,
                run_id=str(job.run_id) if job.run_id else None,
                dataset_id=str(job.dataset_id) if job.dataset_id else None,
            )
        except Exception as exc:
            self.log.error(
                "job_failed",
                job_id=str(job.job_id),
                job_type=job.job_type,
                run_id=str(job.run_id) if job.run_id else None,
                dataset_id=str(job.dataset_id) if job.dataset_id else None,
                error=repr(exc),
            )
            session.rollback()

            # Update job + any referenced dataset/run status in a fresh transaction.
            try:
                job2 = session.get(JobRow, job.job_id)
                if job2 is not None:
                    job2.last_error = repr(exc)
                    job2.updated_at = datetime.now(UTC)

                    if job2.attempts >= job2.max_attempts:
                        job2.status = "failed"
                    else:
                        job2.status = "pending"

                if job.dataset_id is not None:
                    ds = session.get(DatasetRow, job.dataset_id)
                    if ds is not None:
                        ds.status = "failed"
                        ds.error = repr(exc)
                        ds.updated_at = datetime.now(UTC)

                if job.run_id is not None:
                    run = session.get(RunRow, job.run_id)
                    if run is not None:
                        run.status = "failed"
                        run.ended_at = datetime.now(UTC)
                        run.updated_at = datetime.now(UTC)

                    append_event(
                        session,
                        ev=make_event_v1(
                            event_type="run.failed",
                            source="jobs.worker",
                            observed_at=datetime.now(UTC),
                            dedupe_key="failed",
                            run_id=job.run_id,
                            payload=RunFailedPayloadV1(
                                run_id=job.run_id,
                                error=repr(exc),
                            ).model_dump(mode="json"),
                        ),
                        dedupe_scope="run",
                    )

                session.commit()
            except SQLAlchemyError:
                session.rollback()
                raise
        finally:
            heartbeater.stop()


def main() -> None:
    configure_logging()
    JobWorker().run_forever()


if __name__ == "__main__":
    main()
