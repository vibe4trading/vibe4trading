from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FCE_", env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/fce",
        description="SQLAlchemy database URL.",
    )

    log_level: str = "info"

    # Optional: OpenAI-compatible gateway (OpenRouter, etc.).
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "stub"

    # Optional model allowlist (comma-separated). When set, only these model keys are allowed.
    # "stub" is always allowed.
    llm_model_allowlist: str | None = None

    # LLM reliability knobs.
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    # LLM budgets / guardrails (0 disables that budget).
    # These are best-effort caps to avoid runaway spend in MVP.
    llm_max_decision_calls_per_run: int = 500
    llm_max_summary_calls_per_run: int = 5
    llm_max_sentiment_item_summaries_per_dataset: int = 200

    # Internal job worker reliability knobs.
    job_heartbeat_interval_seconds: float = 10.0
    job_stale_after_seconds: float = 300.0

    # Concurrency caps (best-effort when multiple workers run).
    job_max_running_run_execute_replay: int = 1

    # Optional: restrict a worker to a comma-separated allowlist of job types.
    # Example: "dataset_import,run_execute_replay" or "run_execute_live".
    worker_job_types: str | None = None

    # Vendors
    dexscreener_base_url: str = "https://api.dexscreener.com"
    dexscreener_timeout_seconds: float = 10.0
    sentiment_rss_feeds: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def parse_csv_set(raw: str | None) -> set[str] | None:
    """Parse a comma-separated string into a set.

    Returns None when unset/empty, meaning "no restriction".
    """

    if raw is None:
        return None
    items = {s.strip() for s in raw.split(",") if s.strip()}
    return items or None
