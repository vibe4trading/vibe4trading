from __future__ import annotations

import os
import socket
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from v4t.contracts.events import make_event
from v4t.contracts.payloads import RunFailedPayload
from v4t.db.engine import new_session
from v4t.db.event_store import append_event
from v4t.db.models import (
    ArenaSubmissionRow,
    ArenaSubmissionRunRow,
    DatasetRow,
    JobRow,
    RunRow,
)
from v4t.jobs.handlers import (
    handle_arena_execute_submission_job,
    handle_dataset_import_job,
    handle_run_execute_live_job,
    handle_run_execute_replay_job,
)
from v4t.jobs.types import (
    JOB_TYPE_ARENA_EXECUTE_SUBMISSION,
    JOB_TYPE_DATASET_IMPORT,
    JOB_TYPE_RUN_EXECUTE_LIVE,
    JOB_TYPE_RUN_EXECUTE_REPLAY,
)
from v4t.settings import get_settings

_LOG: Final = structlog.get_logger("worker.job_executor")


class JobShouldRetry(Exception):
    def __init__(self, *, job_id: UUID, countdown_seconds: int, max_retries: int, exc: Exception):
        super().__init__(str(exc))
        self.job_id = job_id
        self.countdown_seconds = countdown_seconds
        self.max_retries = max_retries
        self.exc = exc


class _JobHeartbeater:
    def __init__(self, *, job_id: UUID, worker_id: str, interval_seconds: float) -> None:
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
                _LOG.error("heartbeat_commit_failed", job_id=str(self.job_id), exc_info=True)
                session.rollback()
            finally:
                session.close()


@dataclass(frozen=True)
class WorkerIdent:
    worker_id: str

    @staticmethod
    def for_task(*, celery_task_id: str | None) -> WorkerIdent:
        base = f"{socket.gethostname()}:{os.getpid()}"
        return WorkerIdent(worker_id=f"{base}:{celery_task_id}" if celery_task_id else base)


def _now() -> datetime:
    return datetime.now(UTC)


def _is_stale(job: JobRow, *, stale_after_seconds: float) -> bool:
    if stale_after_seconds <= 0:
        return False
    if job.heartbeat_at is None:
        return False
    return job.heartbeat_at < (_now() - timedelta(seconds=stale_after_seconds))


def _retry_countdown_seconds(*, attempt: int) -> int:
    # Small exponential backoff, capped.
    # attempt is 1-based (attempt==1 is the first execution attempt).
    return min(60, 2 ** min(attempt, 6))


def execute_job_or_raise(job_id: UUID, *, celery_task_id: str | None = None) -> None:
    """Execute a domain JobRow once.

    On a retryable failure, raises JobShouldRetry (after updating DB state).
    On a terminal failure, raises the original exception (after updating DB state).
    """

    settings = get_settings()
    stale_after_seconds = float(settings.job_stale_after_seconds)
    heartbeat_interval_seconds = float(settings.job_heartbeat_interval_seconds)

    worker_ident = WorkerIdent.for_task(celery_task_id=celery_task_id)

    session = new_session()
    try:
        job = session.get(JobRow, job_id)
        if job is None:
            raise ValueError(f"job_id not found: {job_id}")

        if job.status == "completed":
            _LOG.info("job_noop_completed", job_id=str(job_id), job_type=job.job_type)
            return
        if job.status in {"failed", "cancelled"}:
            _LOG.info("job_noop_terminal", job_id=str(job_id), job_type=job.job_type)
            return

        # Only one task should execute a job at a time. We enforce this with an atomic UPDATE.
        now = _now()
        stale_cutoff = now - timedelta(seconds=stale_after_seconds)

        if job.status == "running" and not _is_stale(job, stale_after_seconds=stale_after_seconds):
            _LOG.warning(
                "job_already_running",
                job_id=str(job_id),
                job_type=job.job_type,
                locked_by=job.locked_by,
            )
            return

        if job.status == "running":
            _LOG.warning(
                "job_running_stale_takeover",
                job_id=str(job_id),
                job_type=job.job_type,
                locked_by=job.locked_by,
                heartbeat_at=job.heartbeat_at.isoformat() if job.heartbeat_at else None,
            )

        claim = session.execute(
            update(JobRow)
            .where(
                JobRow.job_id == job_id,
                (
                    (JobRow.status == "pending")
                    | (
                        (JobRow.status == "running")
                        & (JobRow.heartbeat_at.is_(None) | (JobRow.heartbeat_at < stale_cutoff))
                    )
                ),
            )
            .values(
                status="running",
                locked_at=now,
                locked_by=worker_ident.worker_id,
                heartbeat_at=now,
                attempts=JobRow.attempts + 1,
                updated_at=now,
            )
        )
        if int(getattr(claim, "rowcount", 0) or 0) != 1:
            session.rollback()
            _LOG.warning("job_claim_raced", job_id=str(job_id))
            return

        session.commit()
        job = session.get(JobRow, job_id)
        if job is None:
            raise RuntimeError(f"Claimed job_id not found: {job_id}")

        heartbeater = _JobHeartbeater(
            job_id=job.job_id,
            worker_id=worker_ident.worker_id,
            interval_seconds=heartbeat_interval_seconds,
        )
        heartbeater.start()
        try:
            _LOG.info(
                "job_started",
                job_id=str(job.job_id),
                job_type=job.job_type,
                attempts=job.attempts,
                max_attempts=job.max_attempts,
                run_id=str(job.run_id) if job.run_id else None,
                dataset_id=str(job.dataset_id) if job.dataset_id else None,
            )

            if job.job_type == JOB_TYPE_DATASET_IMPORT:
                handle_dataset_import_job(session, job)
            elif job.job_type == JOB_TYPE_RUN_EXECUTE_REPLAY:
                handle_run_execute_replay_job(session, job)
            elif job.job_type == JOB_TYPE_RUN_EXECUTE_LIVE:
                handle_run_execute_live_job(session, job)
            elif job.job_type == JOB_TYPE_ARENA_EXECUTE_SUBMISSION:
                handle_arena_execute_submission_job(session, job)
            else:
                raise ValueError(f"Unknown job_type={job.job_type}")

            # Success.
            job.status = "completed"
            job.locked_at = None
            job.locked_by = None
            job.heartbeat_at = None
            job.updated_at = _now()
            session.commit()

            _LOG.info(
                "job_completed",
                job_id=str(job.job_id),
                job_type=job.job_type,
                run_id=str(job.run_id) if job.run_id else None,
                dataset_id=str(job.dataset_id) if job.dataset_id else None,
            )
            return
        except Exception as exc:
            _LOG.error(
                "job_failed",
                job_id=str(job.job_id),
                job_type=job.job_type,
                run_id=str(job.run_id) if job.run_id else None,
                dataset_id=str(job.dataset_id) if job.dataset_id else None,
                error=repr(exc),
            )
            session.rollback()

            # Update job + parents in a fresh transaction.
            try:
                job2 = session.get(JobRow, job.job_id)
                if job2 is None:
                    raise

                job2.last_error = repr(exc)
                job2.updated_at = _now()

                terminal = int(job2.attempts) >= int(job2.max_attempts)
                job2.status = "failed" if terminal else "pending"
                job2.locked_at = None
                job2.locked_by = None
                job2.heartbeat_at = None
                if not terminal:
                    countdown = _retry_countdown_seconds(attempt=int(job2.attempts))
                    job2.available_at = _now() + timedelta(seconds=countdown)

                # Best-effort: reflect state back to referenced entities.
                if job2.dataset_id is not None:
                    ds = session.get(DatasetRow, job2.dataset_id)
                    if ds is not None:
                        if terminal:
                            ds.status = "failed"
                            ds.error = repr(exc)
                        else:
                            if ds.status == "running":
                                ds.status = "pending"
                        ds.updated_at = _now()

                if job2.run_id is not None:
                    run = session.get(RunRow, job2.run_id)
                    if run is not None:
                        if terminal:
                            run.status = "failed"
                            run.ended_at = _now()
                        else:
                            if run.status == "running":
                                run.status = "pending"
                        run.updated_at = _now()

                        if terminal and run.kind == "tournament":
                            link = (
                                session.execute(
                                    select(ArenaSubmissionRunRow).where(
                                        ArenaSubmissionRunRow.run_id == job2.run_id
                                    )
                                )
                                .scalars()
                                .one_or_none()
                            )
                            if link is not None:
                                link.status = "failed"
                                link.error = repr(exc)
                                link.ended_at = _now()
                                link.updated_at = _now()
                                sub = session.get(ArenaSubmissionRow, link.submission_id)
                                if sub is not None and sub.status not in {"finished", "failed"}:
                                    sub.status = "failed"
                                    sub.error = repr(exc)
                                    sub.ended_at = _now()
                                    sub.updated_at = _now()

                    if terminal:
                        append_event(
                            session,
                            ev=make_event(
                                event_type="run.failed",
                                source="worker.celery",
                                observed_at=_now(),
                                dedupe_key="failed",
                                run_id=job2.run_id,
                                payload=RunFailedPayload(
                                    run_id=job2.run_id,
                                    error=repr(exc),
                                ).model_dump(mode="json"),
                            ),
                            dedupe_scope="run",
                        )

                session.commit()

                if terminal:
                    raise

                countdown = _retry_countdown_seconds(attempt=int(job2.attempts))
                max_retries = max(0, int(job2.max_attempts) - 1)
                raise JobShouldRetry(
                    job_id=job2.job_id,
                    countdown_seconds=countdown,
                    max_retries=max_retries,
                    exc=exc,
                ) from exc
            except SQLAlchemyError:
                session.rollback()
                raise
        finally:
            heartbeater.stop()
    finally:
        session.close()


def recover_stale_jobs_once() -> int:
    """Release stale running jobs back to pending/failed.

    Returns number of recovered jobs.
    """

    settings = get_settings()
    stale_after_seconds = float(settings.job_stale_after_seconds)
    if stale_after_seconds <= 0:
        return 0

    session = new_session()
    try:
        cutoff = _now() - timedelta(seconds=stale_after_seconds)
        stale = list(
            session.execute(
                select(JobRow)
                .where(
                    JobRow.status == "running",
                    JobRow.heartbeat_at.is_not(None),
                    JobRow.heartbeat_at < cutoff,
                )
                .order_by(JobRow.heartbeat_at)
                .with_for_update(skip_locked=True)
            ).scalars()
        )
        if not stale:
            session.rollback()
            return 0

        _LOG.warning(
            "stale_jobs_recovered",
            count=len(stale),
            job_ids=[str(j.job_id) for j in stale[:10]],
        )

        now = _now()
        for job in stale:
            job.last_error = (
                f"recovered stale lock (locked_by={job.locked_by}, heartbeat_at={job.heartbeat_at})"
            )
            job.locked_at = None
            job.locked_by = None
            job.heartbeat_at = None
            job.updated_at = now

            if int(job.attempts) >= int(job.max_attempts):
                job.status = "failed"
            else:
                job.status = "pending"
                job.available_at = now

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
        return len(stale)
    finally:
        session.close()
