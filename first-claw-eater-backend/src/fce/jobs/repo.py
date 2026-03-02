from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from fce.db.models import JobRow


def enqueue_job(
    session: Session,
    *,
    job_type: str,
    payload: dict,
    run_id: UUID | None = None,
    dataset_id: UUID | None = None,
) -> JobRow:
    now = datetime.now(UTC)
    job = JobRow(
        job_type=job_type,
        status="pending",
        payload=payload,
        run_id=run_id,
        dataset_id=dataset_id,
        available_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.flush()
    return job
