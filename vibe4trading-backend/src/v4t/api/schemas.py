from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["spot", "sentiment"]
    source: Literal["demo", "dexscreener", "empty", "rss", "freqtrade"] = "demo"
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


class ModelPublicOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    label: str | None = None


class ModelAdminOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    label: str | None = None
    api_base_url: str | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ModelAdminCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    label: str | None = None
    api_base_url: str | None = None
    enabled: bool = True


class ModelAdminUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    api_base_url: str | None = None
    enabled: bool | None = None


class ModelTokenPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_key: str
    token: str | None = None


class RunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    model_key: str = "stub"
    market_dataset_id: UUID
    sentiment_dataset_id: UUID

    model_token_pairs: list[ModelTokenPair] | None = None

    prompt_text: str = "Analyze the market data and decide target exposure."


class RunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    parent_run_id: UUID | None = None
    market_id: str
    model_key: str
    status: str
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class RunLeaderboardEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    parent_run_id: UUID | None
    market_id: str
    model_key: str
    total_return_pct: float
    final_equity: float
    created_at: datetime


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

    prompt_text: str = "You are a trading assistant. Analyze the market and make decisions."

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


class ScenarioWindowOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    label: str
    start: datetime
    end: datetime


class ScenarioSetOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    description: str
    windows: list[ScenarioWindowOut]

    # Fixed knobs for comparability/cost.
    base_interval_seconds: int
    min_interval_seconds: int
    price_tick_seconds: int
    lookback_bars: int
    timeframe: str
    time_offset_seconds: int
    fee_bps: float
    initial_equity_quote: float


class ArenaSubmissionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_set_key: str = "default-v1"
    market_id: str = "spot:demo:DEMO"
    model_key: str = "stub"

    prompt_text: str = "Analyze the market data and decide target exposure."

    visibility: Literal["public", "private"] = "public"


class ArenaSubmissionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: UUID
    scenario_set_key: str
    market_id: str
    model_key: str
    visibility: str
    status: str

    windows_total: int
    windows_completed: int

    total_return_pct: float | None
    avg_return_pct: float | None

    error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class ArenaScenarioRunOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: UUID
    scenario_index: int
    run_id: UUID
    window_start: datetime
    window_end: datetime

    status: str
    return_pct: float | None
    error: str | None
    started_at: datetime | None
    ended_at: datetime | None


class ArenaSubmissionDetailOut(ArenaSubmissionOut):
    runs: list[ArenaScenarioRunOut]


class LeaderboardEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: UUID
    scenario_set_key: str
    market_id: str
    model_key: str
    total_return_pct: float
    avg_return_pct: float
    created_at: datetime
