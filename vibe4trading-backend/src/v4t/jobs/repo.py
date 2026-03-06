from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from v4t.db.models import JobRow
from v4t.utils.datetime import now as utc_now

logger = structlog.get_logger()


def enqueue_job(
    session: Session,
    *,
    job_type: str,
    payload: dict[str, Any],
    run_id: UUID | None = None,
    dataset_id: UUID | None = None,
) -> JobRow:
    now = utc_now()
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


def enqueue_unique_job(
    session: Session,
    *,
    job_type: str,
    payload: dict[str, Any],
    run_id: UUID | None = None,
    dataset_id: UUID | None = None,
) -> JobRow:
    if run_id is not None:
        existing = session.execute(
            select(JobRow)
            .where(JobRow.job_type == job_type, JobRow.run_id == run_id)
            .order_by(JobRow.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    now = utc_now()
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

    with session.begin_nested():
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            if run_id is None:
                raise
            existing2 = session.execute(
                select(JobRow)
                .where(JobRow.job_type == job_type, JobRow.run_id == run_id)
                .order_by(JobRow.created_at.desc())
                .limit(1)
            ).scalar_one()
            return existing2

    return job


def dispatch_and_update_job(session: Session, job: JobRow) -> None:
    """Dispatch job to Celery and update with task_id. Raises on failure."""
    from v4t.worker.dispatch import dispatch_job

    try:
        task_id = dispatch_job(job=job)
        job.payload = {**job.payload, "celery_task_id": task_id}
        session.commit()
    except Exception as exc:
        logger.error("job_dispatch_failed", job_id=job.job_id, error=str(exc))
        session.rollback()
        raise
