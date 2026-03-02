from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from fce.db.models import JobRow
from fce.ingest.dataset_import import import_dataset
from fce.orchestrator.live_run import execute_live_run
from fce.orchestrator.replay_run import execute_replay_run


def _require_id(value: UUID | None, *, field: str) -> UUID:
    if value is None:
        raise ValueError(f"Job missing required {field}")
    return value


def handle_dataset_import_job(session: Session, job: JobRow) -> None:
    dataset_id = _require_id(job.dataset_id, field="dataset_id")
    import_dataset(session, dataset_id=dataset_id)


def handle_run_execute_replay_job(session: Session, job: JobRow) -> None:
    run_id = _require_id(job.run_id, field="run_id")
    execute_replay_run(session, run_id=run_id)


def handle_run_execute_live_job(session: Session, job: JobRow) -> None:
    run_id = _require_id(job.run_id, field="run_id")
    execute_live_run(session, run_id=run_id)
