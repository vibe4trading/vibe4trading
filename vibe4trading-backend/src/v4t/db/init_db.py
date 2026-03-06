from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError

from v4t.db import models as _models
from v4t.db.base import Base

_ = _models

_INDEX_DDL = (
    "CREATE INDEX IF NOT EXISTS ix_events_run_event_type_ingested_event_id ON events (run_id, event_type, ingested_at, event_id)",
    "CREATE INDEX IF NOT EXISTS ix_events_event_type_ingested_event_id ON events (event_type, ingested_at, event_id)",
    "CREATE INDEX IF NOT EXISTS ix_jobs_dispatch_pending ON jobs (available_at, created_at) WHERE status = 'pending'",
    "CREATE INDEX IF NOT EXISTS ix_jobs_stale_heartbeat ON jobs (heartbeat_at) WHERE status = 'running' AND heartbeat_at IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_datasets_created_at ON datasets (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_runs_created_at_run_id ON runs (created_at, run_id)",
    "CREATE INDEX IF NOT EXISTS ix_arena_submissions_created_at_submission_id ON arena_submissions (created_at, submission_id)",
)


def _ensure_users_model_allowlist_override_column(engine: Engine) -> None:
    with engine.begin() as connection:
        try:
            connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS model_allowlist_override VARCHAR(1024)"
                )
            )
            connection.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_groups VARCHAR(1024)")
            )
            return
        except (OperationalError, ProgrammingError):
            inspector = inspect(connection)
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "model_allowlist_override" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN model_allowlist_override VARCHAR(1024)")
                )
            if "oidc_groups" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN oidc_groups VARCHAR(1024)"))


def _ensure_llm_models_api_key_column(engine: Engine) -> None:
    with engine.begin() as connection:
        try:
            connection.execute(text("ALTER TABLE llm_models ADD COLUMN IF NOT EXISTS api_key TEXT"))
            return
        except (OperationalError, ProgrammingError):
            inspector = inspect(connection)
            model_columns = {column["name"] for column in inspector.get_columns("llm_models")}
            if "api_key" in model_columns:
                return
            connection.execute(text("ALTER TABLE llm_models ADD COLUMN api_key TEXT"))


def _ensure_indexes(engine: Engine) -> None:
    with engine.begin() as connection:
        for ddl in _INDEX_DDL:
            connection.execute(text(ddl))


def init_db(engine: Engine) -> None:
    # MVP bootstrap: create tables if missing. Alembic can take over later.
    Base.metadata.create_all(bind=engine)
    _ensure_users_model_allowlist_override_column(engine)
    _ensure_llm_models_api_key_column(engine)
    _ensure_indexes(engine)
