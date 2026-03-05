from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

import v4t.worker.job_executor as exec_mod
from v4t.db.models import EventRow, JobRow, RunConfigSnapshotRow, RunRow
from v4t.jobs.types import JOB_TYPE_RUN_EXECUTE_REPLAY
from v4t.worker.job_executor import JobShouldRetry, execute_job_or_raise


def _make_run_and_job(db_session, *, now: datetime, max_attempts: int) -> tuple[RunRow, JobRow]:
    cfg = RunConfigSnapshotRow(config={}, created_at=now)
    db_session.add(cfg)
    db_session.flush()

    run = RunRow(
        kind="single_window",
        visibility="private",
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=cfg.config_id,
        status="running",
        started_at=now,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.flush()

    job = JobRow(
        job_type=JOB_TYPE_RUN_EXECUTE_REPLAY,
        status="pending",
        payload={},
        attempts=0,
        max_attempts=max_attempts,
        available_at=now,
        locked_at=None,
        locked_by=None,
        heartbeat_at=None,
        last_error=None,
        run_id=run.run_id,
        dataset_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.commit()

    return run, job


def test_worker_does_not_mark_run_failed_when_job_will_retry(db_session, monkeypatch) -> None:
    now = datetime.now(UTC)
    run, job = _make_run_and_job(db_session, now=now, max_attempts=3)

    def boom(session, job):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(exec_mod, "handle_run_execute_replay_job", boom)

    try:
        execute_job_or_raise(job.job_id, celery_task_id="test")
    except JobShouldRetry:
        pass

    db_session.refresh(job)
    db_session.refresh(run)

    assert job.attempts == 1
    assert job.status == "pending"
    assert job.locked_by is None
    assert job.heartbeat_at is None

    assert run.status == "pending"
    assert run.ended_at is None

    failed_cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(EventRow.run_id == run.run_id, EventRow.event_type == "run.failed")
    ).scalar_one()
    assert int(failed_cnt) == 0


def test_worker_marks_run_failed_on_terminal_job_failure(db_session, monkeypatch) -> None:
    now = datetime.now(UTC)
    run, job = _make_run_and_job(db_session, now=now, max_attempts=1)

    def boom(session, job):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(exec_mod, "handle_run_execute_replay_job", boom)

    try:
        execute_job_or_raise(job.job_id, celery_task_id="test")
    except RuntimeError:
        pass

    db_session.refresh(job)
    db_session.refresh(run)

    assert job.attempts == 1
    assert job.status == "failed"
    assert job.locked_by is None
    assert job.heartbeat_at is None

    assert run.status == "failed"
    assert run.ended_at is not None

    failed_cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(EventRow.run_id == run.run_id, EventRow.event_type == "run.failed")
    ).scalar_one()
    assert int(failed_cnt) == 1
