from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.benchmark.spec import (
    PositionMode,
    benchmark_system_prompt,
    build_strategy_prompt,
)
from v4t.contracts.events import make_event
from v4t.contracts.numbers import decimal_to_str, parse_decimal
from v4t.contracts.payloads import (
    LlmDecisionOutput,
    MarketOHLCVPayload,
    PortfolioSnapshotPayload,
    RunFailedPayload,
    RunFinishedPayload,
    RunStartedPayload,
    SentimentItemPayload,
    SentimentItemSummaryPayload,
    SimFillPayload,
    SimFillSide,
)
from v4t.contracts.run_config import RunConfigSnapshot, RunMode
from v4t.db.event_store import append_event
from v4t.db.models import PortfolioSnapshotRow, RunConfigSnapshotRow, RunRow
from v4t.orchestrator.prompt_builder import build_default_prompt_context
from v4t.utils.datetime import now

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidatedDecision:
    accepted: bool
    reject_reason: str | None
    effective_target: Decimal
    mode: PositionMode
    leverage: int
    stop_loss_pct: Decimal | None
    take_profit_pct: Decimal | None
    confidence: Decimal | None
    key_signals: list[str]
    rationale: str | None


@dataclass(frozen=True)
class SentimentPromptItem:
    payload: SentimentItemPayload
    raw_payload: dict[str, Any] | None = None


def get_system_prompt(cfg: RunConfigSnapshot) -> str:
    return benchmark_system_prompt(cfg.prompt.system_prompt_override, cfg.market_id)


def get_strategy_prompt(cfg: RunConfigSnapshot) -> str:
    return build_strategy_prompt(
        base_prompt=cfg.prompt.prompt_text,
        risk_level=cfg.risk_level,
        holding_period=cfg.holding_period,
    )


def _coerce_sentiment_metadata(raw_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw_payload, dict):
        return {}

    out: dict[str, Any] = {}
    for key, value in raw_payload.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            out[key] = value
    return out


def _build_sentiment_tags(item: SentimentPromptItem) -> list[str]:
    tags = [item.payload.source, str(item.payload.item_kind)]
    handle = item.raw_payload.get("handle") if isinstance(item.raw_payload, dict) else None
    if isinstance(handle, str) and handle.strip():
        tags.append(handle.strip())
    return tags


def _build_sentiment_prompt_items(
    *,
    tick_time: datetime,
    mask_offset: timedelta,
    sentiment_items: list[SentimentPromptItem],
    sentiment_summaries: list[SentimentItemSummaryPayload],
) -> list[dict[str, Any]]:
    recent_items: dict[str, SentimentPromptItem] = {}
    for item in sentiment_items:
        if item.payload.item_time <= tick_time:
            recent_items[item.payload.external_id] = item

    recent_summaries: dict[str, SentimentItemSummaryPayload] = {}
    for summary in sentiment_summaries:
        if summary.item_time <= tick_time:
            recent_summaries[summary.external_id] = summary

    merged: list[dict[str, Any]] = []
    for external_id, item in recent_items.items():
        summary = recent_summaries.get(external_id)
        summary_text = (summary.summary_text or "").strip() if summary is not None else ""
        uses_full_text = not bool(summary_text)
        effective_text = item.payload.text.strip() if uses_full_text else summary_text
        effective_item_time = summary.item_time if summary is not None else item.payload.item_time
        effective_source = summary.source if summary is not None else item.payload.source
        effective_kind = summary.item_kind if summary is not None else item.payload.item_kind
        effective_tags = (
            list(summary.tags)
            if summary is not None and summary.tags
            else _build_sentiment_tags(item)
        )

        merged.append(
            {
                "item_time": effective_item_time,
                "summary_text": effective_text,
                "tags": effective_tags,
                "sentiment_score": summary.sentiment_score if summary is not None else None,
                "source": effective_source,
                "external_id": external_id,
                "item_kind": str(effective_kind),
                "url": item.payload.url,
                "metadata": _coerce_sentiment_metadata(item.raw_payload),
                "uses_full_text": uses_full_text,
            }
        )

    for external_id, summary in recent_summaries.items():
        if external_id in recent_items:
            continue
        merged.append(
            {
                "item_time": summary.item_time,
                "summary_text": summary.summary_text,
                "tags": list(summary.tags),
                "sentiment_score": summary.sentiment_score,
                "source": summary.source,
                "external_id": external_id,
                "item_kind": str(summary.item_kind),
                "url": None,
                "metadata": {},
                "uses_full_text": False,
            }
        )

    merged.sort(key=lambda entry: entry["item_time"])
    merged = merged[-20:]

    out: list[dict[str, Any]] = []
    for entry in merged:
        item_time = entry["item_time"]
        masked_item_time = (
            item_time + mask_offset if mask_offset.total_seconds() != 0 else item_time
        ).isoformat()
        out.append({**entry, "item_time": masked_item_time})

    return out


def load_run_and_config(
    session: Session,
    *,
    run_id: UUID,
    expected_mode: RunMode | str | None = None,
) -> tuple[RunRow, RunConfigSnapshot]:
    run = session.get(RunRow, run_id)
    if run is None:
        raise ValueError(f"run_id not found: {run_id}")

    cfg_row = session.get(RunConfigSnapshotRow, run.config_id)
    if cfg_row is None:
        raise ValueError(f"config_id not found: {run.config_id}")

    cfg = RunConfigSnapshot.model_validate(cfg_row.config)

    if expected_mode is not None:
        expected_value = str(expected_mode)
        if cfg.mode != expected_value:
            raise ValueError(f"run_id={run_id} is not a {expected_value} run (mode={cfg.mode})")

    return run, cfg


def mark_run_started(
    session: Session,
    *,
    run: RunRow,
    run_id: UUID,
    mode: Literal["replay", "live"],
    source: str,
) -> None:
    run.status = "running"
    run.started_at = now()
    run.updated_at = now()
    session.commit()

    append_event(
        session,
        ev=make_event(
            event_type="run.started",
            source=source,
            observed_at=now(),
            dedupe_key="started",
            run_id=run_id,
            payload=RunStartedPayload(run_id=run_id, mode=mode).model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )
    session.commit()


def mark_run_cancelled(session: Session, *, run: RunRow) -> None:
    run.status = "cancelled"
    run.ended_at = now()
    run.updated_at = now()
    session.commit()


def mark_run_finished(
    session: Session,
    *,
    run: RunRow,
    run_id: UUID,
    source: str,
    return_pct: Decimal,
    summary_call_id: UUID | None,
    summary_text: str | None,
) -> None:
    run.status = "finished"
    run.ended_at = now()
    run.summary_call_id = summary_call_id
    run.summary_text = summary_text
    run.updated_at = now()

    append_event(
        session,
        ev=make_event(
            event_type="run.finished",
            source=source,
            observed_at=now(),
            dedupe_key="finished",
            run_id=run_id,
            payload=RunFinishedPayload(
                run_id=run_id,
                return_pct=decimal_to_str(return_pct),
            ).model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )

    session.commit()


def mark_run_failed(
    session: Session,
    *,
    run: RunRow,
    run_id: UUID,
    source: str,
    error: str,
) -> None:
    run.status = "failed"
    run.ended_at = now()
    run.updated_at = now()

    append_event(
        session,
        ev=make_event(
            event_type="run.failed",
            source=source,
            observed_at=now(),
            dedupe_key="failed",
            run_id=run_id,
            payload=RunFailedPayload(run_id=run_id, error=error).model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )

    session.commit()


def compute_features(closes: list[str]) -> dict[str, Any] | None:
    if len(closes) < 2:
        return None
    try:
        c0 = Decimal(closes[0])
        c1 = Decimal(closes[-1])
        momentum = c1 - c0
        ret_pct = ((c1 / c0) - 1) * Decimal("100") if c0 != 0 else None
        return {
            "momentum": decimal_to_str(momentum),
            "return_pct": decimal_to_str(ret_pct) if ret_pct is not None else None,
        }
    except Exception:
        _logger.exception("compute_features failed for %d closes", len(closes))
        return None


def mask_decision_memory(
    memory: list[dict[str, Any]], mask_offset: timedelta
) -> list[dict[str, Any]]:
    if mask_offset.total_seconds() == 0:
        return memory[-3:]

    masked_memory: list[dict[str, Any]] = []
    for m in memory[-3:]:
        mm = dict(m)
        tt = mm.get("tick_time")
        if isinstance(tt, str):
            try:
                dt = datetime.fromisoformat(tt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                mm["tick_time"] = (dt + mask_offset).isoformat()
            except Exception:
                _logger.debug("mask_decision_memory: failed to parse tick_time %r", tt)
        masked_memory.append(mm)
    return masked_memory


def build_prompt_context(
    *,
    market_id: str,
    tick_time: datetime,
    mask_offset: timedelta,
    timeframe: str | None,
    latest_price: tuple[datetime, str] | None,
    ohlcv_bars: list[MarketOHLCVPayload] | None,
    closes: list[str],
    features: dict[str, Any] | None,
    sentiment_items: list[SentimentPromptItem],
    sentiment_summaries: list[SentimentItemSummaryPayload],
    portfolio_view: dict[str, str],
    memory: list[dict[str, Any]],
) -> dict[str, Any]:
    prompt_tick_time = tick_time + mask_offset

    ctx = build_default_prompt_context(
        market_id=market_id,
        tick_time=prompt_tick_time,
        closes=closes,
        features=features,
        sentiment_summaries=_build_sentiment_prompt_items(
            tick_time=tick_time,
            mask_offset=mask_offset,
            sentiment_items=sentiment_items,
            sentiment_summaries=sentiment_summaries,
        ),
        portfolio=portfolio_view,
        memory=mask_decision_memory(memory, mask_offset),
    )

    if timeframe:
        ctx["timeframe"] = timeframe

    if latest_price is not None:
        price_ts, price_str = latest_price
        ts = price_ts + mask_offset if mask_offset.total_seconds() != 0 else price_ts
        ctx["latest_price"] = {
            "observed_at": ts.isoformat(),
            "price": price_str,
        }

    if ohlcv_bars is not None:
        ctx["ohlcv_bars"] = [
            {
                "bar_start": (
                    (b.bar_start + mask_offset) if mask_offset.total_seconds() != 0 else b.bar_start
                ).isoformat(),
                "bar_end": (
                    (b.bar_end + mask_offset) if mask_offset.total_seconds() != 0 else b.bar_end
                ).isoformat(),
                "timeframe": b.timeframe,
                "o": b.o,
                "h": b.h,
                "l": b.l,
                "c": b.c,
                "volume_base": b.volume_base,
                "volume_quote": b.volume_quote,
            }
            for b in ohlcv_bars
        ]

    return ctx


def validate_decision(
    *,
    decision: LlmDecisionOutput,
    market_id: str,
    last_target: Decimal,
    last_mode: PositionMode = PositionMode.spot,
    last_leverage: int = 1,
    gross_leverage_cap: Decimal,
    net_exposure_cap: Decimal,
    call_error: str | None,
) -> ValidatedDecision:
    accepted = True
    reject_reason: str | None = None
    effective_target = last_target
    effective_mode = last_mode
    effective_leverage = last_leverage
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None

    if call_error is not None:
        accepted = False
        reject_reason = f"llm_error: {call_error}"[:300]

    if accepted:
        proposed_mode = PositionMode(decision.mode)
        proposed_target = Decimal(decision.target)
        proposed_leverage = int(decision.leverage)
        if proposed_mode == PositionMode.spot and proposed_leverage != 1:
            accepted = False
            reject_reason = "spot leverage must be 1"
        elif proposed_mode == PositionMode.spot and proposed_target < 0:
            accepted = False
            reject_reason = "spot exposure must be >= 0"
        elif proposed_mode == PositionMode.spot and proposed_target > Decimal("1"):
            accepted = False
            reject_reason = "spot exposure must be <= 1"
        elif abs(proposed_target) > Decimal(proposed_leverage):
            accepted = False
            reject_reason = "exposure exceeds leverage"
        if accepted:
            if abs(proposed_target) > gross_leverage_cap:
                accepted = False
                reject_reason = "exposure exceeds gross_leverage_cap"
            elif abs(proposed_target) > net_exposure_cap:
                accepted = False
                reject_reason = "exposure exceeds net_exposure_cap"
            else:
                effective_target = proposed_target
                effective_mode = proposed_mode
                effective_leverage = proposed_leverage
                stop_loss_pct = decision.stop_loss_pct
                take_profit_pct = decision.take_profit_pct

    if not accepted:
        effective_target = last_target
        effective_mode = last_mode
        effective_leverage = last_leverage
        stop_loss_pct = None
        take_profit_pct = None

    return ValidatedDecision(
        accepted=accepted,
        reject_reason=reject_reason,
        effective_target=effective_target,
        mode=effective_mode,
        leverage=effective_leverage,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        confidence=decision.confidence,
        key_signals=list(decision.key_signals),
        rationale=decision.rationale,
    )


def advance_base_tick(
    *,
    next_base_tick: datetime,
    base_interval: timedelta,
) -> datetime:
    return next_base_tick + base_interval


def append_decision_memory(
    memory: list[dict[str, Any]],
    decision_payload: dict[str, Any],
    max_items: int | None = 50,
) -> list[dict[str, Any]]:
    memory.append(decision_payload)
    if max_items is None:
        return memory
    return memory[-max_items:]


def append_sim_fill_event(
    session: Session,
    *,
    source: str,
    tick_time: datetime,
    run_id: UUID,
    market_id: str,
    fill: Any,
    fill_index: int = 0,
) -> None:
    side = SimFillSide.buy if fill.qty_base > 0 else SimFillSide.sell
    fill_payload = SimFillPayload(
        tick_time=tick_time,
        market_id=market_id,
        side=side,
        qty_base=decimal_to_str(fill.qty_base),
        price=decimal_to_str(fill.price),
        notional_quote=decimal_to_str(fill.notional_quote),
        fee_quote=decimal_to_str(fill.fee_quote),
        reason=getattr(fill, "reason", None),
        position_mode=getattr(fill, "position_mode", None),
        leverage=getattr(fill, "leverage", None),
    ).model_dump(mode="json")

    append_event(
        session,
        ev=make_event(
            event_type="sim.fill",
            source=source,
            observed_at=tick_time,
            dedupe_key=f"{tick_time.isoformat()}:{market_id}:{fill_index}",
            run_id=run_id,
            payload=fill_payload,
        ),
        dedupe_scope="run",
    )


def write_portfolio_snapshot(
    session: Session,
    *,
    source: str,
    tick_time: datetime,
    run_id: UUID,
    market_id: str,
    equity: Decimal,
    cash: Decimal,
    position_base: Decimal,
    extra_payload: dict[str, str | int | None] | None = None,
) -> None:
    normalized_extra = dict(extra_payload or {})

    def _decimal_field(name: str) -> str | None:
        value = normalized_extra.get(name)
        if isinstance(value, str):
            return decimal_to_str(parse_decimal(value))
        return None

    def _position_mode_field() -> Literal["spot", "futures", "none"] | None:
        value = normalized_extra.get("position_mode")
        if value == "spot":
            return "spot"
        if value == "futures":
            return "futures"
        if value == "none":
            return "none"
        return None

    def _position_direction_field() -> Literal["long", "short", "flat"] | None:
        value = normalized_extra.get("position_direction")
        if value == "long":
            return "long"
        if value == "short":
            return "short"
        if value == "flat":
            return "flat"
        return None

    position_mode = _position_mode_field()
    position_direction = _position_direction_field()

    position_leverage_raw = normalized_extra.get("position_leverage")
    position_leverage: int | None = (
        position_leverage_raw if isinstance(position_leverage_raw, int) else None
    )

    snap_payload = PortfolioSnapshotPayload(
        snapshot_time=tick_time,
        equity_quote=decimal_to_str(equity),
        cash_quote=decimal_to_str(cash),
        positions_base={market_id: decimal_to_str(position_base)},
        position_mode=position_mode,
        position_direction=position_direction,
        position_qty_base=_decimal_field("position_qty_base"),
        position_leverage=position_leverage,
        entry_price=_decimal_field("entry_price"),
        current_price=_decimal_field("current_price"),
        liquidation_price=_decimal_field("liquidation_price"),
        unrealized_pnl=_decimal_field("unrealized_pnl"),
        unrealized_pnl_pct=_decimal_field("unrealized_pnl_pct"),
        funding_cost_accumulated=_decimal_field("funding_cost_accumulated"),
        stop_loss_price=_decimal_field("stop_loss_price"),
        take_profit_price=_decimal_field("take_profit_price"),
    ).model_dump(mode="json")
    append_event(
        session,
        ev=make_event(
            event_type="portfolio.snapshot",
            source=source,
            observed_at=tick_time,
            dedupe_key=tick_time.isoformat(),
            run_id=run_id,
            payload=snap_payload,
        ),
        dedupe_scope="run",
    )

    existing = session.execute(
        select(PortfolioSnapshotRow).where(
            PortfolioSnapshotRow.run_id == run_id,
            PortfolioSnapshotRow.observed_at == tick_time,
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            PortfolioSnapshotRow(
                run_id=run_id,
                observed_at=tick_time,
                equity_quote=equity,
                cash_quote=cash,
                positions={market_id: decimal_to_str(position_base)},
            )
        )
    else:
        existing.equity_quote = equity
        existing.cash_quote = cash
        existing.positions = {market_id: decimal_to_str(position_base)}


def select_usable_bars(
    ohlcv_bars: list[MarketOHLCVPayload],
    *,
    tick_time: datetime,
    lookback_bars: int,
    timeframe: str | None,
) -> list[MarketOHLCVPayload]:
    usable_bars = [
        b
        for b in ohlcv_bars
        if b.bar_end <= tick_time and (timeframe is None or b.timeframe == timeframe)
    ]
    return usable_bars[-lookback_bars:]
