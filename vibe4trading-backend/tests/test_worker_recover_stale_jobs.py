from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from v4t.db.models import DatasetRow, JobRow, RunRow
from v4t.settings import get_settings
from v4t.worker.job_executor import recover_stale_jobs_once


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def test_recover_stale_jobs_disabled_returns_zero(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("V4T_JOB_STALE_AFTER_SECONDS", "0")
    get_settings.cache_clear()

    assert recover_stale_jobs_once() == 0


def test_recover_stale_jobs_releases_stale_job_and_parents(db_session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("V4T_JOB_STALE_AFTER_SECONDS", "10")
    get_settings.cache_clear()

    now_before = datetime.now(UTC)
    stale_heartbeat = now_before - timedelta(seconds=60)

    ds = DatasetRow(
        category="spot",
        source="demo",
        start=now_before - timedelta(hours=2),
        end=now_before - timedelta(hours=1),
        params={"market_id": "spot:demo:DEMO"},
        status="running",
        error=None,
        created_at=now_before,
        updated_at=now_before,
    )
    db_session.add(ds)
    db_session.flush()

    run = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=uuid4(),
        status="running",
        created_at=now_before,
        updated_at=now_before,
    )
    db_session.add(run)
    db_session.flush()

    job = JobRow(
        job_type="dataset_import",
        status="running",
        payload={},
        attempts=1,
        max_attempts=3,
        available_at=now_before,
        locked_at=now_before,
        locked_by="w",
        heartbeat_at=stale_heartbeat,
        last_error=None,
        dataset_id=ds.dataset_id,
        run_id=run.run_id,
        created_at=now_before,
        updated_at=now_before,
    )
    db_session.add(job)
    db_session.commit()

    recovered = recover_stale_jobs_once()
    assert recovered == 1

    now_after = datetime.now(UTC)
    db_session.expire_all()
    job2 = db_session.get(JobRow, job.job_id)
    assert job2 is not None
    assert job2.status == "pending"
    assert job2.locked_by is None
    assert job2.heartbeat_at is None
    assert _as_utc(now_before) <= _as_utc(job2.available_at) <= _as_utc(now_after)
    assert job2.last_error and "recovered stale lock" in job2.last_error

    ds2 = db_session.get(DatasetRow, ds.dataset_id)
    run2 = db_session.get(RunRow, run.run_id)
    assert ds2 is not None and ds2.status == "pending"
    assert run2 is not None and run2.status == "pending"

    assert recover_stale_jobs_once() == 0


def test_recover_stale_jobs_does_not_touch_fresh_job(db_session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("V4T_JOB_STALE_AFTER_SECONDS", "10")
    get_settings.cache_clear()

    now = datetime.now(UTC)
    job = JobRow(
        job_type="dataset_import",
        status="running",
        payload={},
        attempts=1,
        max_attempts=3,
        available_at=now,
        locked_at=now,
        locked_by="w",
        heartbeat_at=now,
        last_error=None,
        dataset_id=None,
        run_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.commit()

    assert recover_stale_jobs_once() == 0
    db_session.refresh(job)
    assert job.status == "running"


def test_recover_stale_jobs_ignores_running_job_without_heartbeat(db_session, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("V4T_JOB_STALE_AFTER_SECONDS", "10")
    get_settings.cache_clear()

    now = datetime.now(UTC)
    job = JobRow(
        job_type="dataset_import",
        status="running",
        payload={},
        attempts=1,
        max_attempts=3,
        available_at=now,
        locked_at=now,
        locked_by="w",
        heartbeat_at=None,
        last_error=None,
        dataset_id=None,
        run_id=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.commit()

    assert recover_stale_jobs_once() == 0
    db_session.refresh(job)
    assert job.status == "running"
