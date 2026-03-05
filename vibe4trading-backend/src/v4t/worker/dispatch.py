from __future__ import annotations

import importlib
from uuid import UUID

from v4t.db.models import JobRow
from v4t.jobs.types import (
    JOB_TYPE_ARENA_EXECUTE_SUBMISSION,
    JOB_TYPE_DATASET_IMPORT,
    JOB_TYPE_RUN_EXECUTE_LIVE,
    JOB_TYPE_RUN_EXECUTE_REPLAY,
)
from v4t.settings import get_settings
from v4t.worker.celery_app import celery_app

_TASK_NAME_BY_JOB_TYPE: dict[str, str] = {
    JOB_TYPE_DATASET_IMPORT: "v4t.worker.tasks.dataset_import_job",
    JOB_TYPE_RUN_EXECUTE_REPLAY: "v4t.worker.tasks.run_execute_replay_job",
    JOB_TYPE_RUN_EXECUTE_LIVE: "v4t.worker.tasks.run_execute_live_job",
    JOB_TYPE_ARENA_EXECUTE_SUBMISSION: "v4t.worker.tasks.arena_execute_submission_job",
}


def dispatch_job(*, job: JobRow) -> str:
    """Dispatch a JobRow to Celery and return the celery task id."""

    return dispatch_job_id(job_id=job.job_id, job_type=job.job_type)


def dispatch_job_id(*, job_id: UUID, job_type: str) -> str:
    job_id_str = str(job_id)
    always_eager = bool(get_settings().celery_always_eager)
    celery_app.conf.task_always_eager = always_eager
    celery_app.conf.task_eager_propagates = always_eager

    task_name = _TASK_NAME_BY_JOB_TYPE.get(job_type)
    if task_name is None:
        raise ValueError(f"Unknown job_type={job_type}")

    if bool(getattr(celery_app.conf, "task_always_eager", False)):
        importlib.import_module("v4t.worker.tasks")

        task = celery_app.tasks.get(task_name)
        if task is None:
            raise RuntimeError(f"Celery task not registered: {task_name}")
        res = task.apply_async(args=[job_id_str])
    else:
        res = celery_app.send_task(task_name, args=[job_id_str])

    return str(res.id)
