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


class MarketPricePayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    price: str = Field(pattern=DECIMAL_STR_RE)
    price_type: PriceType = PriceType.mid


class MarketOHLCVPayloadV1(BaseModel):
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


class SentimentItemPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    external_id: str
    item_time: datetime
    item_kind: SentimentItemKind
    text: str
    url: str | None = None


class SentimentItemSummaryPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    external_id: str
    item_time: datetime
    item_kind: SentimentItemKind
    summary_text: str
    tags: list[str] = Field(default_factory=list)
    sentiment_score: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    llm_call_id: UUID | None = None


class LlmDecisionOutputV1(BaseModel):
    """The strict JSON object the model must output (parsed from chat content)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    targets: dict[str, Decimal] = Field(default_factory=dict)
    next_check_seconds: int | None = None
    confidence: Decimal | None = None
    key_signals: list[str] = Field(default_factory=list)
    rationale: str | None = None


class LlmDecisionPayloadV1(BaseModel):
    """Run-scoped decision event payload stored in the event log."""

    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    market_id: str
    targets: dict[str, str] = Field(default_factory=dict)
    llm_call_id: UUID | None = None

    accepted: bool = True
    reject_reason: str | None = None

    next_check_seconds: int | None = None
    confidence: str | None = Field(default=None, pattern=DECIMAL_STR_RE)
    key_signals: list[str] = Field(default_factory=list)
    rationale: str | None = None


class LlmScheduleRequestPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    requested_seconds: int
    honored_seconds: int | None = None


class LlmStreamStartPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    purpose: Literal["decision"] = "decision"


class LlmStreamDeltaPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    seq: int
    delta: str


class LlmStreamEndPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    error: str | None = None


class SimFillSide(StrEnum):
    buy = "buy"
    sell = "sell"


class SimFillPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_time: datetime
    market_id: str
    side: SimFillSide
    qty_base: str = Field(pattern=DECIMAL_STR_RE)
    price: str = Field(pattern=DECIMAL_STR_RE)
    notional_quote: str = Field(pattern=DECIMAL_STR_RE)
    fee_quote: str = Field(pattern=DECIMAL_STR_RE)


class PortfolioSnapshotPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_time: datetime
    equity_quote: str = Field(pattern=DECIMAL_STR_RE)
    cash_quote: str = Field(pattern=DECIMAL_STR_RE)
    positions_base: dict[str, str] = Field(default_factory=dict)


class RunStartedPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    mode: Literal["replay", "live"]


class RunFinishedPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    return_pct: str = Field(pattern=DECIMAL_STR_RE)


class RunFailedPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    error: str
