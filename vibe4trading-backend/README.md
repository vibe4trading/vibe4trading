# Vibe4Trading Backend

Internal-pipeline (modular monolith) backend for the Vibe4Trading hackathon MVP.

See `ARCHITECTURE.md` for the process topology (API + Celery workers + Beat).

## Ports

- API: `http://localhost:8000`
- Postgres (Docker Compose): `localhost:5433` -> container `db:5432`
- Redis (Docker Compose): `localhost:6379` -> container `redis:6379`

## Local dev

```bash
uv sync
uv run uvicorn v4t.api.app:app --reload --port 8000
```

Celery worker (default queue):

```bash
uv run celery -A v4t.worker.celery_app:celery_app worker --loglevel=info --queues=default --concurrency=2
```

Celery worker (live queue):

```bash
uv run celery -A v4t.worker.celery_app:celery_app worker --loglevel=info --queues=live --concurrency=1
```

Beat (scheduler, recommended):

```bash
uv run celery -A v4t.worker.celery_app:celery_app beat --loglevel=info
```

Note: the live worker runs long-lived jobs; keep it in a separate terminal so dataset imports +
replay runs can still execute.

## Golden commands

```bash
uv sync
uv run pytest
uv run ruff format .
uv run ruff check .
```

## Docker Compose

From this directory:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

This starts:

- `db` (Postgres)
- `migrate` (one-shot Alembic migrations)
- `api` (FastAPI)
- `worker` (Celery worker, default queue)
- `worker_live` (Celery worker, live queue)
- `beat` (Celery beat scheduler)
- `redis` (Celery broker/result backend)

## Environment

Copy/adjust `.env.example` for local/dev.
