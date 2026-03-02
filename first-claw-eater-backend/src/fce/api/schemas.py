from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["spot", "sentiment"]
    source: Literal["demo", "dexscreener", "empty", "rss"] = "demo"
    start: datetime
    end: datetime
    params: dict[str, Any] = Field(default_factory=dict)


class DatasetOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: UUID
    category: str
    source: str
    start: datetime
    end: datetime
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    model_key: str = "stub"
    spot_dataset_id: UUID
    sentiment_dataset_id: UUID

    # Optional user-authored prompt template; if omitted, a built-in default is used.
    prompt_template_id: UUID | None = None
    prompt_vars: dict[str, Any] = Field(default_factory=dict)

    base_interval_seconds: int = 3600
    min_interval_seconds: int = 60
    price_tick_seconds: int = 60

    lookback_bars: int = 24
    timeframe: str = "1h"

    # Prompt-only time masking (seconds). Internal replay clock remains unshifted.
    time_offset_seconds: int = 0

    fee_bps: float = 10.0
    initial_equity_quote: float = 1000.0


class RunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    market_id: str
    model_key: str
    status: str
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class TimelinePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    equity_quote: float
    cash_quote: float


class PricePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    price: float


class PromptTemplateCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    engine: Literal["mustache"] = "mustache"
    system_template: str
    user_template: str
    vars_schema: dict[str, Any] | None = None


class PromptTemplateOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: UUID
    name: str
    engine: str
    system_template: str
    user_template: str
    vars_schema: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class LiveRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Core run knobs
    market_id: str = "spot:demo:DEMO"
    model_key: str = "stub"

    prompt_template_id: UUID | None = None
    prompt_vars: dict[str, Any] = Field(default_factory=dict)

    base_interval_seconds: int = 60
    min_interval_seconds: int = 30
    price_tick_seconds: int = 60

    lookback_bars: int = 60
    timeframe: str = "1m"

    # Prompt-only time masking (seconds). Internal live clock remains unshifted.
    time_offset_seconds: int = 0

    fee_bps: float = 10.0
    initial_equity_quote: float = 1000.0

    # Live ingestion
    live_source: Literal["demo", "dexscreener"] = "demo"
    chain_id: str | None = None
    pair_id: str | None = None
    base_price: float = 1.0

    # If a live run is already running, reuse it unless force_restart=true.
    force_restart: bool = False


class LiveRunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: RunOut | None
