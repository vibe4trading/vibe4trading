from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunMode(StrEnum):
    replay = "replay"
    live = "live"


class RunKind(StrEnum):
    single_window = "single_window"
    tournament = "tournament"


class RunVisibility(StrEnum):
    private = "private"
    public = "public"


class ModelConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str | None = None
    temperature: float = 0.0
    max_output_tokens: int = 800


class DatasetRefsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_dataset_id: UUID | None = None
    sentiment_dataset_id: UUID | None = None


class ReplayConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    advance_mode: Literal["as_fast_as_possible"] = "as_fast_as_possible"
    max_concurrent_llm_requests: int = 1
    pace_seconds_per_base_tick: float = 0.0


class SchedulerConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_interval_seconds: int = 3600
    min_interval_seconds: int = 60
    price_tick_seconds: int = 60
    early_check_alignment: Literal["ceil_to_price_tick"] = "ceil_to_price_tick"


class DecisionConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    missing_market_policy: Literal["hold_previous"] = "hold_previous"


class PromptTemplateSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: Literal["mustache"] = "mustache"
    system: str
    user: str
    vars: dict[str, Any] = Field(default_factory=dict)


class PromptMaskingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_offset_seconds: int = 0


class PromptConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_text: str
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
    masking: PromptMaskingV1 = PromptMaskingV1()


class ExecutionConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fee_bps: float = 10.0
    gross_leverage_cap: float = 1.0
    net_exposure_cap: float = 1.0
    initial_equity_quote: float = 1000.0


class SummaryConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_key: str = "builtin:run_summary:v1"
    model_key: str | None = None


class LiveConfigV1(BaseModel):
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


class RunConfigSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    mode: RunMode
    run_kind: RunKind = RunKind.single_window
    visibility: RunVisibility = RunVisibility.private

    market_id: str
    model: ModelConfigV1
    datasets: DatasetRefsV1

    # Live mode parameters (prompt-only; does not affect replay determinism).
    live: LiveConfigV1 = Field(default_factory=LiveConfigV1)

    replay: ReplayConfigV1 = ReplayConfigV1()
    scheduler: SchedulerConfigV1 = SchedulerConfigV1()
    decision: DecisionConfigV1 = DecisionConfigV1()
    prompt: PromptConfigV1
    execution: ExecutionConfigV1 = ExecutionConfigV1()
    summary: SummaryConfigV1 = SummaryConfigV1()
