from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from v4t.arena.runner import execute_arena_submission
from v4t.db.models import JobRow
from v4t.ingest.dataset_import import import_dataset
from v4t.orchestrator.live_run import execute_live_run
from v4t.orchestrator.replay_run import execute_replay_run
from v4t.settings import get_settings


def _require_id(value: UUID | None, *, field: str) -> UUID:
    if value is None:
        raise ValueError(f"Job missing required {field}")
    return value


def _require_payload_uuid(job: JobRow, *, key: str) -> UUID:
    raw = (job.payload or {}).get(key)
    if raw is None:
        raise ValueError(f"Job missing required payload.{key}")
    return UUID(str(raw))


def handle_dataset_import_job(session: Session, job: JobRow) -> None:
    dataset_id = _require_id(job.dataset_id, field="dataset_id")
    import_dataset(session, dataset_id=dataset_id)


def handle_run_execute_replay_job(session: Session, job: JobRow) -> None:
    run_id = _require_id(job.run_id, field="run_id")
    execute_replay_run(session, run_id=run_id)


def handle_run_execute_live_job(session: Session, job: JobRow) -> None:
    run_id = _require_id(job.run_id, field="run_id")

    settings = get_settings()
    max_ticks: int | None = None
    if settings.celery_always_eager:
        v = int(settings.live_max_ticks)
        max_ticks = v if v > 0 else None

    execute_live_run(session, run_id=run_id, max_ticks=max_ticks)


def handle_arena_execute_submission_job(session: Session, job: JobRow) -> None:
    submission_id = _require_payload_uuid(job, key="submission_id")
    execute_arena_submission(session, submission_id=submission_id)
