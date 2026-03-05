from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging
from kombu import Queue

from v4t.observability.logging import configure_logging
from v4t.settings import get_settings


@setup_logging.connect
def _configure_celery_logging(*_args, **_kwargs) -> None:
    # Ensure structlog is configured when running under `celery worker`.
    configure_logging()


_settings = get_settings()
redis_url = _settings.redis_url
always_eager = bool(_settings.celery_always_eager)


celery_app = Celery(
    "v4t",
    broker=redis_url,
    backend=redis_url,
    include=[
        "v4t.worker.tasks",
    ],
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    task_always_eager=always_eager,
    task_eager_propagates=always_eager,
)


# Queues: keep live runs isolated (long-lived tasks).
celery_app.conf.task_default_queue = "default"
celery_app.conf.task_queues = (
    Queue("default"),
    Queue("live"),
)


celery_app.conf.task_routes = {
    "v4t.worker.tasks.dataset_import_job": {"queue": "default"},
    "v4t.worker.tasks.run_execute_replay_job": {"queue": "default"},
    "v4t.worker.tasks.arena_execute_submission_job": {"queue": "default"},
    "v4t.worker.tasks.run_execute_live_job": {"queue": "live"},
    "v4t.worker.tasks.recover_stale_jobs": {"queue": "default"},
    "v4t.worker.tasks.dispatch_pending_jobs": {"queue": "default"},
}


# Periodic tasks (Beat)
celery_app.conf.beat_schedule = {
    "recover-stale-jobs": {
        "task": "v4t.worker.tasks.recover_stale_jobs",
        "schedule": crontab(minute="*/1"),
    },
    "dispatch-pending-jobs": {
        "task": "v4t.worker.tasks.dispatch_pending_jobs",
        "schedule": 10.0,
    },
}
