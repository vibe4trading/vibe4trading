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
    get_risk_profile,
)
from v4t.contracts.events import make_event
from v4t.contracts.numbers import decimal_to_str, parse_decimal
from v4t.contracts.payloads import (
    LlmDecisionOutputV1,
    LlmDecisionOutputV2,
    LlmScheduleRequestPayload,
    MarketOHLCVPayload,
    PortfolioSnapshotPayload,
    RunFailedPayload,
    RunFinishedPayload,
    RunStartedPayload,
    SentimentItemSummaryPayload,
    SimFillPayload,
    SimFillSide,
)
from v4t.contracts.run_config import RunConfigSnapshot, RunMode
from v4t.db.event_store import append_event
from v4t.db.models import PortfolioSnapshotRow, RunConfigSnapshotRow, RunRow
from v4t.orchestrator.prompt_builder import build_default_prompt_context
from v4t.utils.datetime import ceil_seconds, ceil_time, now

_logger = logging.getLogger(__name__)

LEGACY_SYSTEM_PROMPT = (
    "You are a trading decision engine. "
    "Return ONLY a valid JSON object matching schema_version=1. "
    "Spot is long-only; target exposure must be between 0 and 1."
)


@dataclass(frozen=True)
class ValidatedDecision:
    accepted: bool
    reject_reason: str | None
    effective_target: Decimal
    decision_schema_version: int
    mode: PositionMode
    leverage: int
    stop_loss_pct: Decimal | None
    take_profit_pct: Decimal | None
    next_check_seconds: int | None
    confidence: Decimal | None
    key_signals: list[str]
    rationale: str | None


def get_system_prompt(cfg: RunConfigSnapshot) -> str:
    if int(cfg.decision_schema_version) == 2:
        return benchmark_system_prompt(cfg.prompt.system_prompt_override)
    override = (cfg.prompt.system_prompt_override or "").strip()
    if override:
        return override
    return LEGACY_SYSTEM_PROMPT


def get_strategy_prompt(cfg: RunConfigSnapshot) -> str:
    if int(cfg.decision_schema_version) == 2:
        return build_strategy_prompt(
            base_prompt=cfg.prompt.prompt_text,
            risk_level=cfg.risk_level,
            holding_period=cfg.holding_period,
        )
    return cfg.prompt.prompt_text


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


def compute_features(closes: list[str]) -> dict | None:
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


def mask_decision_memory(memory: list[dict], mask_offset: timedelta) -> list[dict]:
    if mask_offset.total_seconds() == 0:
        return memory[-3:]

    masked_memory: list[dict] = []
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
    features: dict | None,
    sentiment_summaries: list[SentimentItemSummaryPayload],
    portfolio_view: dict[str, str],
    memory: list[dict],
    decision_schema_version: int = 1,
) -> dict[str, Any]:
    prompt_tick_time = tick_time + mask_offset
    recent_summaries = [s for s in sentiment_summaries if s.item_time <= tick_time]
    recent_summaries = recent_summaries[-20:]

    ctx = build_default_prompt_context(
        market_id=market_id,
        tick_time=prompt_tick_time,
        closes=closes,
        features=features,
        sentiment_summaries=[
            {
                "item_time": (s.item_time + mask_offset).isoformat()
                if mask_offset.total_seconds() != 0
                else s.item_time.isoformat(),
                "summary_text": s.summary_text,
                "tags": s.tags,
                "sentiment_score": s.sentiment_score,
            }
            for s in recent_summaries
        ],
        portfolio=portfolio_view,
        memory=mask_decision_memory(memory, mask_offset),
    )
    ctx["decision_schema_version"] = int(decision_schema_version)

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
    decision: LlmDecisionOutputV1 | LlmDecisionOutputV2,
    market_id: str,
    last_target: Decimal,
    last_mode: PositionMode = PositionMode.spot,
    last_leverage: int = 1,
    gross_leverage_cap: Decimal,
    net_exposure_cap: Decimal,
    call_error: str | None,
    risk_level: int | None,
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

    if int(decision.schema_version) == 2:
        v2 = decision if isinstance(decision, LlmDecisionOutputV2) else None
        if v2 is None:
            accepted = False
            reject_reason = "invalid decision schema"
        else:
            profile = get_risk_profile(risk_level)
            proposed_mode = PositionMode(v2.mode)
            proposed_target = Decimal(v2.target)
            proposed_leverage = int(v2.leverage)
            if profile is not None:
                if proposed_mode not in profile.mode_allowed:
                    accepted = False
                    reject_reason = "mode not allowed for risk_level"
                elif proposed_mode == PositionMode.spot and proposed_leverage != 1:
                    accepted = False
                    reject_reason = "spot leverage must be 1"
                elif proposed_mode == PositionMode.spot and proposed_target < 0:
                    accepted = False
                    reject_reason = "spot exposure must be >= 0"
                elif proposed_mode == PositionMode.spot and proposed_target > Decimal("1"):
                    accepted = False
                    reject_reason = "spot exposure must be <= 1"
                elif abs(proposed_target) > profile.max_abs_exposure:
                    accepted = False
                    reject_reason = "exposure exceeds risk_level cap"
                elif proposed_leverage > profile.max_leverage:
                    accepted = False
                    reject_reason = "leverage exceeds risk_level cap"
                elif proposed_target < 0 and not profile.short_allowed:
                    accepted = False
                    reject_reason = "shorting not allowed for risk_level"
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
                    stop_loss_pct = v2.stop_loss_pct
                    take_profit_pct = v2.take_profit_pct
    else:
        targets = decision.targets if isinstance(decision, LlmDecisionOutputV1) else None
        if targets:
            if set(targets.keys()) - {market_id}:
                accepted = False
                reject_reason = "targets contains unknown market_id"
            else:
                proposed = targets.get(market_id)
                if proposed is None:
                    effective_target = last_target
                elif proposed < 0:
                    accepted = False
                    reject_reason = "spot exposure must be >= 0"
                elif proposed > gross_leverage_cap:
                    accepted = False
                    reject_reason = "exposure exceeds gross_leverage_cap"
                elif proposed > net_exposure_cap:
                    accepted = False
                    reject_reason = "exposure exceeds net_exposure_cap"
                else:
                    effective_target = proposed

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
        decision_schema_version=int(decision.schema_version),
        mode=effective_mode,
        leverage=effective_leverage,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        next_check_seconds=decision.next_check_seconds,
        confidence=decision.confidence,
        key_signals=list(decision.key_signals),
        rationale=decision.rationale,
    )


def choose_tick_time(next_base_tick: datetime, next_early_tick: datetime | None) -> datetime:
    tick_time = next_base_tick
    if next_early_tick is not None and next_early_tick < tick_time:
        tick_time = next_early_tick
    return tick_time


def advance_schedule(
    *,
    tick_time: datetime,
    next_base_tick: datetime,
    next_early_tick: datetime | None,
    base_interval: timedelta,
) -> tuple[datetime, datetime | None]:
    if next_early_tick is not None and tick_time == next_early_tick:
        next_early_tick = None
    if tick_time == next_base_tick:
        next_base_tick = next_base_tick + base_interval
    return next_base_tick, next_early_tick


def compute_early_tick(
    *,
    requested_seconds: int,
    min_interval_seconds: int,
    base_interval_seconds: int,
    step_seconds: int,
    tick_time: datetime,
    next_base_tick: datetime,
    align_to_step: bool,
) -> tuple[int | None, datetime | None]:
    honored_raw = max(min_interval_seconds, min(requested_seconds, base_interval_seconds))
    honored = ceil_seconds(honored_raw, step=step_seconds)
    candidate = tick_time + timedelta(seconds=honored)
    if align_to_step:
        candidate = ceil_time(candidate, step_seconds=step_seconds)
    if candidate < next_base_tick:
        return honored, candidate
    return None, None


def append_schedule_request_event(
    session: Session,
    *,
    source: str,
    tick_time: datetime,
    run_id: UUID,
    requested_seconds: int,
    honored_seconds: int | None,
) -> None:
    append_event(
        session,
        ev=make_event(
            event_type="llm.schedule_request",
            source=source,
            observed_at=tick_time,
            dedupe_key=tick_time.isoformat(),
            run_id=run_id,
            payload=LlmScheduleRequestPayload(
                tick_time=tick_time,
                requested_seconds=requested_seconds,
                honored_seconds=honored_seconds,
            ).model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )


def append_decision_memory(
    memory: list[dict], decision_payload: dict, max_items: int | None = 50
) -> list[dict]:
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
    for field in {
        "position_qty_base",
        "entry_price",
        "current_price",
        "liquidation_price",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "funding_cost_accumulated",
        "stop_loss_price",
        "take_profit_price",
    }:
        value = normalized_extra.get(field)
        if isinstance(value, str):
            normalized_extra[field] = decimal_to_str(parse_decimal(value))

    snap_payload = PortfolioSnapshotPayload(
        snapshot_time=tick_time,
        equity_quote=decimal_to_str(equity),
        cash_quote=decimal_to_str(cash),
        positions_base={market_id: decimal_to_str(position_base)},
        **normalized_extra,
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
