from __future__ import annotations

import re
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_MODEL_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="V4T_", env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/v4t",
        description="SQLAlchemy database URL.",
    )
    db_pool_size: int = Field(default=20, description="SQLAlchemy pool size for non-SQLite DBs.")
    db_max_overflow: int = Field(
        default=30,
        description="Additional DB connections allowed above the base pool size.",
    )
    db_pool_timeout_seconds: float = Field(
        default=30.0,
        description="Seconds to wait for a pooled DB connection before failing.",
    )

    # Celery broker/result backend.
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL used by Celery as broker + result backend.",
    )

    celery_always_eager: bool = Field(
        default=False,
        description="Execute Celery tasks in-process (no broker).",
    )

    live_max_ticks: int = Field(
        default=0,
        description="When running eager live jobs, cap ticks (0 disables).",
    )

    log_level: str = "info"

    # Optional: OpenAI-compatible gateway (OpenRouter, etc.).
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "stub"
    llm_report_model: str | None = Field(
        default=None,
        description=(
            "Model key used for arena submission report generation. "
            "When unset, falls back to the submission's own model_key."
        ),
    )

    # Optional model allowlist (comma-separated). When set, only these model keys are allowed.
    # "stub" is always allowed.
    llm_model_allowlist: str | None = None

    # LLM reliability knobs.
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_max_concurrent_requests: int = Field(
        default=3,
        description="Maximum concurrent outbound LLM HTTP requests per process.",
    )
    llm_max_queued_requests: int | None = Field(
        default=None,
        description=(
            "Maximum number of queued outbound LLM requests per process. "
            "Defaults to 3x llm_max_concurrent_requests when unset."
        ),
    )

    # LLM budgets / guardrails (0 disables that budget).
    # These are best-effort caps to avoid runaway spend in MVP.
    llm_max_decision_calls_per_run: int = 500
    llm_max_summary_calls_per_run: int = 5
    llm_max_sentiment_item_summaries_per_dataset: int = 200

    # Internal job worker reliability knobs.
    job_heartbeat_interval_seconds: float = 10.0
    job_stale_after_seconds: float = 300.0

    # Runtime behavior (not user-modifiable).

    replay_base_interval_seconds: int = Field(
        default=3600,
        description="Replay: base interval for scheduler ticks (seconds).",
    )
    replay_price_tick_seconds: int = Field(
        default=60,
        description="Replay: price tick cadence (seconds).",
    )

    live_base_interval_seconds: int = Field(
        default=60,
        description="Live: base interval for scheduler ticks (seconds).",
    )
    live_price_tick_seconds: int = Field(
        default=5,
        description="Live: price tick cadence (seconds).",
    )

    replay_prompt_lookback_bars: int = Field(
        default=72,
        description="Replay: number of bars included in prompt context.",
    )
    replay_prompt_timeframe: str = Field(
        default="1h",
        description="Replay: OHLCV timeframe for prompt bars (e.g., 1h, 1m).",
    )
    replay_prompt_time_offset_seconds: int = Field(
        default=0,
        description="Replay: prompt-only time masking offset (seconds).",
    )

    live_prompt_lookback_bars: int = Field(
        default=60,
        description="Live: number of bars included in prompt context.",
    )
    live_prompt_timeframe: str = Field(
        default="1m",
        description="Live: OHLCV timeframe for prompt bars (e.g., 1h, 1m).",
    )
    live_prompt_time_offset_seconds: int = Field(
        default=0,
        description="Live: prompt-only time masking offset (seconds).",
    )

    execution_fee_bps: float = Field(
        default=10.0,
        description="Trading fee in basis points.",
    )
    execution_initial_equity_quote: float = Field(
        default=10000.0,
        description="Initial equity in quote currency.",
    )
    execution_gross_leverage_cap: float = Field(
        default=1.0,
        description="Max gross leverage (best-effort cap).",
    )
    execution_net_exposure_cap: float = Field(
        default=1.0,
        description="Max net exposure (best-effort cap).",
    )

    # Vendors
    dexscreener_base_url: str = "https://api.dexscreener.com"
    dexscreener_timeout_seconds: float = 10.0
    sentiment_rss_feeds: str | None = None

    # RSS ingest hardening
    sentiment_rss_timeout_seconds: float = 10.0
    sentiment_rss_max_bytes: int = 1_000_000
    sentiment_rss_allowed_schemes: str = "https,http"
    sentiment_rss_allow_private_hosts: bool = False
    sentiment_rss_allowed_hosts: str | None = None

    oidc_issuer: str = Field(default="", description="OIDC issuer URL")
    oidc_jwks_url: str = Field(default="", description="OIDC JWKS endpoint URL")
    oidc_audience: str = Field(default="", description="OIDC audience")
    daily_run_limit: int = Field(default=3, description="Daily run limit per user")

    bypass_auth: bool = Field(default=False, description="Bypass auth for non-production")

    admin_email_allowlist: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of admin user emails. When set, only these users can access admin-only endpoints."
        ),
    )

    admin_groups: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of OIDC group names that grant admin access. "
            "Users whose oidc_groups contain any of these groups are considered admins."
        ),
    )

    arena_dataset_ids: str | None = Field(
        default=None,
        description=(
            "Comma-separated UUIDs of pre-populated spot datasets used by Arena. "
            "When set, Arena runs ignore synthetic scenario datasets and instead use these "
            "datasets grouped by params.market_id, running across the 10 dataset windows."
        ),
    )


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


def parse_model_allowlist_override(
    raw: str | None, *, strict: bool = False
) -> tuple[set[str], set[str]]:
    additions: set[str] = set()
    removals: set[str] = set()

    if raw is None:
        return additions, removals

    for token in raw.split(","):
        value = token.strip()
        if not value:
            continue

        op = value[0]
        model_key = value[1:].strip()
        if op not in {"+", "-"} or not model_key:
            if strict:
                raise ValueError(f"Invalid allowlist override token: {value}")
            continue
        if model_key == "stub":
            continue
        if not _MODEL_KEY_RE.match(model_key):
            if strict:
                raise ValueError(f"Invalid model key in allowlist override: {model_key}")
            continue

        if op == "+":
            additions.add(model_key)
            removals.discard(model_key)
        else:
            removals.add(model_key)
            additions.discard(model_key)

    return additions, removals
