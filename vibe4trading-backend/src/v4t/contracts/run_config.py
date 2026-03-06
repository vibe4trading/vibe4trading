from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from v4t.benchmark.spec import HoldingPeriod


class RunMode(StrEnum):
    replay = "replay"
    live = "live"


class RunKind(StrEnum):
    single_window = "single_window"
    tournament = "tournament"


class RunVisibility(StrEnum):
    private = "private"
    public = "public"


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str | None = None
    temperature: float = 0.0
    max_output_tokens: int = 800


class DatasetRefs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_dataset_id: UUID | None = None
    sentiment_dataset_id: UUID | None = None


class ReplayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    advance_mode: Literal["as_fast_as_possible"] = "as_fast_as_possible"
    max_concurrent_llm_requests: int = 1
    pace_seconds_per_base_tick: float = 0.0


class SchedulerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_interval_seconds: int = 3600
    price_tick_seconds: int = 60


class DecisionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_market_policy: Literal["hold_previous"] = "hold_previous"


class PromptTemplateSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: Literal["mustache"] = "mustache"
    system: str
    user: str
    vars: dict[str, Any] = Field(default_factory=dict)


class PromptMasking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_offset_seconds: int = 0


class PromptConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_text: str
    system_prompt_override: str | None = None
    lookback_bars: int = 72
    timeframe: str = "1h"
    include: list[str] = Field(
        default_factory=lambda: [
            "closes",
            "ohlcv",
            "latest_price",
            "portfolio",
            "memory",
            "sentiment",
        ]
    )
    masking: PromptMasking = PromptMasking()


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fee_bps: float = 10.0
    gross_leverage_cap: float = 1.0
    net_exposure_cap: float = 1.0
    initial_equity_quote: float = 10000.0
    funding_rate_per_8h: float = 0.0


class SummaryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_key: str = "builtin:run_summary:v1"
    model_key: str | None = None


class LiveConfig(BaseModel):
    """Live ingestion settings.

    MVP keeps this intentionally small: either a deterministic demo stream or a
    DexScreener polled spot price stream.
    """

    model_config = ConfigDict(extra="forbid")

    source: Literal["demo", "dexscreener"] = "demo"

    # DexScreener params (required when source="dexscreener").
    chain_id: str | None = None
    pair_id: str | None = None

    # Demo params (used when source="demo").
    base_price: float = 1.0
    drift_bps: int = 1
    step_bps: int = 12


class RunConfigSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    mode: RunMode
    run_kind: RunKind = RunKind.single_window
    visibility: RunVisibility = RunVisibility.private

    market_id: str
    risk_level: int | None = Field(default=None, ge=1, le=5)
    holding_period: HoldingPeriod | None = None
    model: ModelConfig
    datasets: DatasetRefs

    # Live mode parameters (prompt-only; does not affect replay determinism).
    live: LiveConfig = Field(default_factory=LiveConfig)

    replay: ReplayConfig = ReplayConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    decision: DecisionConfig = DecisionConfig()
    prompt: PromptConfig
    execution: ExecutionConfig = ExecutionConfig()
    summary: SummaryConfig = SummaryConfig()
