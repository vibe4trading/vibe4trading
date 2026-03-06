from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from v4t.contracts.numbers import DECIMAL_STR_RE


class PriceType(StrEnum):
    last = "last"
    mid = "mid"
    mark = "mark"


class MarketPricePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    price: str = Field(pattern=DECIMAL_STR_RE)
    price_type: PriceType = PriceType.mid


class MarketOHLCVPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    timeframe: str
    bar_start: datetime
    bar_end: datetime

    o: str = Field(pattern=DECIMAL_STR_RE)
    h: str = Field(pattern=DECIMAL_STR_RE)
    l: str = Field(pattern=DECIMAL_STR_RE)
    c: str = Field(pattern=DECIMAL_STR_RE)
    volume_base: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    volume_quote: str | None = Field(default=None, pattern=DECIMAL_STR_RE)


class SentimentItemKind(StrEnum):
    x_post = "x_post"
    news = "news"


class SentimentItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    external_id: str
    item_time: datetime
    item_kind: SentimentItemKind
    text: str
    url: str | None = None


class SentimentItemSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    external_id: str
    item_time: datetime
    item_kind: SentimentItemKind
    summary_text: str
    tags: list[str] = Field(default_factory=list)
    sentiment_score: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    llm_call_id: UUID | None = None


class LlmDecisionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2] = 2
    target: Decimal
    mode: Literal["spot", "futures"]
    leverage: int = Field(default=1, ge=1, le=100)
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None
    confidence: Decimal
    key_signals: list[str] = Field(default_factory=list, min_length=1, max_length=5)
    rationale: str


class LlmDecisionPayload(BaseModel):
    """Run-scoped decision event payload stored in the event log."""

    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    market_id: str
    targets: dict[str, str] = Field(default_factory=dict)
    target: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    mode: Literal["spot", "futures"] | None = None
    leverage: int | None = None
    stop_loss_pct: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    take_profit_pct: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    llm_call_id: UUID | None = None

    accepted: bool = True
    reject_reason: str | None = None

    confidence: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    key_signals: list[str] = Field(default_factory=list)
    rationale: str | None = None


class LlmStreamStartPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    purpose: Literal["decision"] = "decision"


class LlmStreamDeltaPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    seq: int
    delta: str


class LlmStreamEndPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    error: str | None = None


class SimFillSide(StrEnum):
    buy = "buy"
    sell = "sell"


class SimFillPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    market_id: str
    side: SimFillSide
    qty_base: str = Field(pattern=DECIMAL_STR_RE)
    price: str = Field(pattern=DECIMAL_STR_RE)
    notional_quote: str = Field(pattern=DECIMAL_STR_RE)
    fee_quote: str = Field(pattern=DECIMAL_STR_RE)
    reason: str | None = None
    position_mode: Literal["spot", "futures"] | None = None
    leverage: int | None = None


class PortfolioSnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_time: datetime
    equity_quote: str = Field(pattern=DECIMAL_STR_RE)
    cash_quote: str = Field(pattern=DECIMAL_STR_RE)
    positions_base: dict[str, str] = Field(default_factory=dict)
    position_mode: Literal["spot", "futures", "none"] | None = None
    position_direction: Literal["long", "short", "flat"] | None = None
    position_qty_base: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    position_leverage: int | None = None
    entry_price: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    current_price: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    liquidation_price: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    unrealized_pnl: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    unrealized_pnl_pct: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    funding_cost_accumulated: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    stop_loss_price: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    take_profit_price: str | None = Field(default=None, pattern=DECIMAL_STR_RE)


class FundingRatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    funding_time: datetime
    funding_rate: str = Field(pattern=DECIMAL_STR_RE)


class RunStartedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    mode: Literal["replay", "live"]


class RunFinishedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    return_pct: str = Field(pattern=DECIMAL_STR_RE)


class RunFailedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    error: str
