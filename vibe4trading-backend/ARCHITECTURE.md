# Backend Architecture (API + Celery Worker)

This backend is a **modular monolith** codebase, deployed as multiple **processes**:

- **API**: FastAPI (HTTP)
- **Worker(s)**: Celery workers (background execution)
- **Scheduler**: Celery Beat (periodic tasks / housekeeping)

The goal is to keep *one* Python codebase (shared types, DB models, orchestration logic), while
running API and background work as separate services for reliability and scale.

This structure is intentionally aligned with the patterns used in `projects/trans-in-home/backend`
(Celery + Redis broker, task routing via queues, Beat schedule for periodic tasks).

## Service Topology

**Dependencies**

- Postgres: system of record
- Redis: Celery broker + result backend

**Runtime services**

- `migrate`:
  - Runs `alembic upgrade head`
  - Used in Docker Compose so migrations run once before API/workers start

- `api`:
  - Runs `uvicorn v4t.api.app:app`
  - Creates domain rows (datasets, runs, arena submissions, etc.)
  - Enqueues Celery tasks for background execution

- `worker`:
  - Runs `celery -A v4t.worker.celery_app:celery_app worker`
  - Executes short/medium jobs (dataset imports, replay runs, arena submissions)

- `worker_live`:
  - Runs `celery -A v4t.worker.celery_app:celery_app worker --queues=live`
  - Executes long-lived live-run jobs (kept isolated so they don't block other work)

- `beat`:
  - Runs `celery -A v4t.worker.celery_app:celery_app beat`
  - Enqueues periodic tasks (housekeeping, stale recovery, optional re-dispatch)

- Optional: `flower` for monitoring.

## Code Layout

The important split is **entrypoints**, not separate repos:

```text
src/v4t/
  api/                  # FastAPI routers + schemas
  worker/               # Celery app + tasks (+ beat schedule)
  jobs/                 # Domain job types + handler functions
  db/                   # SQLAlchemy models + sessions
  ingest/               # Dataset import logic
  orchestrator/         # Replay/live execution logic
  arena/                # Arena/tournament execution
  contracts/            # Pydantic contracts (events, payloads, IDs)
  observability/        # Logging helpers
  settings.py           # Shared settings (API + worker)
```

`v4t.api.*` must not import Celery unless it is only needed at request time (to keep API startup
fast and avoid circular imports). `v4t.worker.*` is allowed to import the heavy execution modules.

## Job Model (DB) vs Celery Tasks

Celery is the **queue / execution transport**. The database is the **system of record**.

We keep a `jobs` table (`JobRow`) for:

- durable audit trail (what was requested, when)
- user-facing status (if/when we expose it)
- retries / terminal failure bookkeeping
- bridging domain semantics (dataset/run failure) with task execution

### Mapping

Domain job type -> Celery task -> Worker queue:

- `dataset_import` -> `v4t.worker.tasks.dataset_import_job` -> `default`
- `run_execute_replay` -> `v4t.worker.tasks.run_execute_replay_job` -> `default`
- `arena_execute_submission` -> `v4t.worker.tasks.arena_execute_submission_job` -> `default`
- `run_execute_live` -> `v4t.worker.tasks.run_execute_live_job` -> `live`

Queues are used as the primary concurrency control mechanism:

- `default` can run with concurrency 2+ (throughput)
- `live` should usually run with concurrency 1 (long-lived loop)

## Task Execution Semantics

Each task is a thin wrapper that:

1. Loads the `JobRow` from Postgres
2. Marks it `running` (increments attempts, sets a heartbeat)
3. Calls the existing domain handler (import/run/arena)
4. Marks the job `completed` on success
5. On failure:
   - updates `JobRow.last_error`
   - sets parent `DatasetRow` / `RunRow` back to `pending` when the job will retry
   - marks parent rows as `failed` on terminal failure
   - emits `run.failed` event for terminal run failures

Retries are driven by **job.max_attempts**. Celery retries are used only as the transport for
"try again later"; the DB remains the source of truth for whether the job is terminal.

Idempotency rule: tasks must be safe to re-run. If a job is already `completed`, tasks should
no-op.

## Scheduling (Celery Beat)

Beat is used for periodic tasks, similar to `trans-in-home`'s `beat_schedule` pattern.

Recommended periodic tasks:

- `recover_stale_jobs`:
  - finds jobs stuck in `running` with an old `heartbeat_at`
  - releases them back to `pending` (or marks `failed` if out of attempts)
  - optional: re-dispatches a new Celery task for recovered jobs

This gives a safety net for worker crashes and ensures long-lived jobs can be monitored.

## Local Dev

### Docker Compose (recommended)

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

### Manual

```bash
uv sync

# Terminal 1: API
uv run uvicorn v4t.api.app:app --reload --port 8000

# Terminal 2: Worker (default queue)
uv run celery -A v4t.worker.celery_app:celery_app worker --loglevel=info --queues=default --concurrency=2

# Terminal 3: Live worker (live queue)
uv run celery -A v4t.worker.celery_app:celery_app worker --loglevel=info --queues=live --concurrency=1

# Terminal 4: Beat (optional but recommended)
uv run celery -A v4t.worker.celery_app:celery_app beat --loglevel=info
```

## Environment Variables

All settings are prefixed with `V4T_`.

- `V4T_DATABASE_URL`
- `V4T_REDIS_URL`
- `V4T_LOG_LEVEL`

Optional (recommended for operations):

- `V4T_JOB_STALE_AFTER_SECONDS`
- `V4T_JOB_HEARTBEAT_INTERVAL_SECONDS`

Optional (dev/scripts):

- `V4T_CELERY_ALWAYS_EAGER=1` executes tasks in-process (no Redis required)

## Operational Notes

- Treat Celery as **at-least-once**. Design tasks to be idempotent.
- Prefer queue separation (`default` vs `live`) over complicated global locks.
- Keep task payloads small; pass IDs and load heavy objects from Postgres.
