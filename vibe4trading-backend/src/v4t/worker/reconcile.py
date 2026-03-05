from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

import structlog
from sqlalchemy import select

from v4t.db.engine import new_session
from v4t.db.models import JobRow
from v4t.worker.dispatch import dispatch_job_id

_LOG: Final = structlog.get_logger("worker.reconcile")


def dispatch_pending_jobs_once(*, limit: int = 200) -> int:
    limit = max(0, int(limit))
    if limit == 0:
        return 0

    now = datetime.now(UTC)
    session = new_session()
    try:
        stmt = (
            select(JobRow)
            .where(JobRow.status == "pending", JobRow.available_at <= now)
            .order_by(JobRow.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(session.execute(stmt).scalars().all())

        dispatched = 0
        changed = 0
        for job in jobs:
            payload = job.payload or {}
            if payload.get("celery_task_id"):
                continue
            try:
                task_id = dispatch_job_id(job_id=job.job_id, job_type=job.job_type)
            except Exception as exc:
                job.last_error = f"dispatch_failed: {repr(exc)}"
                job.updated_at = now
                changed += 1
                continue

            job.payload = {**payload, "celery_task_id": task_id}
            job.updated_at = now
            dispatched += 1
            changed += 1

        if changed:
            session.commit()
        else:
            session.rollback()

        if dispatched:
            _LOG.info("pending_jobs_dispatched", count=dispatched)
        return dispatched
    finally:
        session.close()
