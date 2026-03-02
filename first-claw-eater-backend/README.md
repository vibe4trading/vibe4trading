# First Claw Eater Backend

Internal-pipeline (modular monolith) backend for the First Claw Eater hackathon MVP.

## Ports

- API: `http://localhost:8000`
- Postgres (Docker Compose): `localhost:5433` -> container `db:5432`

## Local dev

```bash
uv sync
uv run uvicorn fce.api.app:app --reload --port 8000
```

Worker (jobs):

```bash
uv run python -m fce.worker
```

Live worker (optional):

```bash
FCE_WORKER_JOB_TYPES=run_execute_live uv run python -m fce.worker
```

Note: the live worker runs long-lived jobs; for local dev, run it in a separate terminal
so dataset imports + replay runs can still execute.

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

- `api` (FastAPI)
- `worker` (dataset_import + run_execute_replay)
- `worker_live` (run_execute_live)

## Environment

Copy/adjust `.env.example` for local/dev.
