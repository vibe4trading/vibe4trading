from __future__ import annotations

from uuid import UUID

import structlog

from v4t.worker.celery_app import celery_app
from v4t.worker.job_executor import JobShouldRetry, execute_job_or_raise, recover_stale_jobs_once
from v4t.worker.reconcile import dispatch_pending_jobs_once

_LOG = structlog.get_logger("worker.tasks")


@celery_app.task(bind=True)
def dataset_import_job(self, job_id: str) -> None:  # noqa: ANN001
    _execute(self, job_id=job_id)


@celery_app.task(bind=True)
def run_execute_replay_job(self, job_id: str) -> None:  # noqa: ANN001
    _execute(self, job_id=job_id)


@celery_app.task(bind=True)
def run_execute_live_job(self, job_id: str) -> None:  # noqa: ANN001
    _execute(self, job_id=job_id)


@celery_app.task(bind=True)
def arena_execute_submission_job(self, job_id: str) -> None:  # noqa: ANN001
    _execute(self, job_id=job_id)


def _execute(task, *, job_id: str) -> None:  # noqa: ANN001
    job_uuid = UUID(str(job_id))
    try:
        execute_job_or_raise(job_uuid, celery_task_id=getattr(task.request, "id", None))
    except JobShouldRetry as jr:
        _LOG.warning(
            "job_retry_scheduled",
            job_id=str(jr.job_id),
            countdown_seconds=jr.countdown_seconds,
            max_retries=jr.max_retries,
            error=repr(jr.exc),
        )
        raise task.retry(
            exc=jr.exc,
            countdown=jr.countdown_seconds,
            max_retries=jr.max_retries,
        ) from jr


@celery_app.task
def recover_stale_jobs() -> int:
    """Periodic housekeeping task to recover stale job locks."""

    return recover_stale_jobs_once()


@celery_app.task
def dispatch_pending_jobs() -> int:
    return dispatch_pending_jobs_once()
