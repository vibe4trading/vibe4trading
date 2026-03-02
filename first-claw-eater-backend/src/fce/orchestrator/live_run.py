from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from fce.contracts.events import make_event_v1
from fce.contracts.numbers import decimal_to_str
from fce.contracts.payloads import (
    LlmDecisionPayloadV1,
    LlmScheduleRequestPayloadV1,
    MarketOHLCVPayloadV1,
    MarketPricePayloadV1,
    PortfolioSnapshotPayloadV1,
    RunStartedPayloadV1,
    SentimentItemSummaryPayloadV1,
    SimFillPayloadV1,
    SimFillSide,
)
from fce.contracts.run_config import LiveConfigV1, RunConfigSnapshotV1, RunMode
from fce.db.event_store import append_event
from fce.db.models import PortfolioSnapshotRow, RunConfigSnapshotRow, RunRow
from fce.ingest.dexscreener import resolve_spot_market
from fce.llm.gateway import LlmGateway, StubDecisionFeatures
from fce.orchestrator.prompt_builder import build_default_prompt_context, render_mustache
from fce.sim.engine import PortfolioState, rebalance_to_target_exposure


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _floor_time(dt: datetime, *, step_seconds: int) -> datetime:
    dt = _as_utc(dt)
    step_seconds = max(1, int(step_seconds))
    epoch = int(dt.timestamp())
    floored = (epoch // step_seconds) * step_seconds
    return datetime.fromtimestamp(floored, tz=UTC)


def _ceil_time(dt: datetime, *, step_seconds: int) -> datetime:
    dt = _as_utc(dt)
    step_seconds = max(1, int(step_seconds))
    floored = _floor_time(dt, step_seconds=step_seconds)
    if floored == dt:
        return floored
    return floored + timedelta(seconds=step_seconds)


def _ceil_seconds(delta_seconds: int, *, step: int) -> int:
    if step <= 0:
        return delta_seconds
    if delta_seconds % step == 0:
        return delta_seconds
    return ((delta_seconds // step) + 1) * step


def _timeframe_to_seconds(timeframe: str) -> int:
    tf = (timeframe or "").strip().lower()
    if tf.endswith("h") and tf[:-1].isdigit():
        return int(tf[:-1]) * 3600
    if tf.endswith("m") and tf[:-1].isdigit():
        return int(tf[:-1]) * 60
    if tf.endswith("s") and tf[:-1].isdigit():
        return int(tf[:-1])
    # Default to 1h to keep the prompt context stable.
    return 3600


@dataclass
class _OhlcvBarBuilder:
    market_id: str
    timeframe: str

    bar_start: datetime | None = None
    bar_end: datetime | None = None
    o: Decimal | None = None
    h: Decimal | None = None
    l: Decimal | None = None
    c: Decimal | None = None

    def update(self, *, ts: datetime, price: Decimal) -> MarketOHLCVPayloadV1 | None:
        """Update the current bar and return a closed bar if we rolled."""

        ts = _as_utc(ts)
        step = _timeframe_to_seconds(self.timeframe)
        new_start = _floor_time(ts, step_seconds=step)
        new_end = new_start + timedelta(seconds=step)

        closed: MarketOHLCVPayloadV1 | None = None
        if self.bar_start is None:
            # First tick creates the initial bar.
            self.bar_start = new_start
            self.bar_end = new_end
        elif new_start != self.bar_start:
            # Roll: close previous bar (if it has data).
            if self.bar_start is not None and self.bar_end is not None and self.c is not None:
                closed = MarketOHLCVPayloadV1(
                    market_id=self.market_id,
                    timeframe=self.timeframe,
                    bar_start=self.bar_start,
                    bar_end=self.bar_end,
                    o=decimal_to_str(self.o or self.c),
                    h=decimal_to_str(self.h or self.c),
                    l=decimal_to_str(self.l or self.c),
                    c=decimal_to_str(self.c),
                    volume_base=None,
                    volume_quote=None,
                )

            # Start a new bar.
            self.bar_start = new_start
            self.bar_end = new_end
            self.o = None
            self.h = None
            self.l = None
            self.c = None

        # Update current bar OHLC.
        if self.o is None:
            self.o = price
        self.c = price
        self.h = price if self.h is None else max(self.h, price)
        self.l = price if self.l is None else min(self.l, price)
        return closed


def _fetch_live_price(
    *,
    cfg: LiveConfigV1,
    market_id: str,
    rng: random.Random,
    demo_price: Decimal | None,
) -> tuple[Decimal, dict, Decimal | None]:
    if cfg.source == "demo":
        step_bp = rng.randint(-int(cfg.step_bps), int(cfg.step_bps))
        drift_bp = int(cfg.drift_bps)
        # price_{t+1} = price_t * (1 + (drift+step)/10000)
        price = demo_price if demo_price is not None else Decimal(str(cfg.base_price))
        price = (price * Decimal(10000 + drift_bp + step_bp)) / Decimal(10000)
        if price <= 0:
            price = Decimal(str(cfg.base_price))
        price_q = price.quantize(Decimal("0.000001"))
        return (
            price_q,
            {
                "source": "demo",
                "step_bp": step_bp,
                "drift_bp": drift_bp,
                "market_id": market_id,
            },
            price_q,
        )

    if cfg.source == "dexscreener":
        if not cfg.chain_id or not cfg.pair_id:
            raise ValueError("live.source=dexscreener requires live.chain_id and live.pair_id")
        resolved = resolve_spot_market(chain_id=cfg.chain_id, pair_id=cfg.pair_id)
        return (
            resolved.base_price,
            {
                "source": "dexscreener",
                "resolved_market_id": resolved.market_id,
            },
            demo_price,
        )

    raise ValueError(f"Unknown live.source={cfg.source}")


def execute_live_run(session: Session, *, run_id: UUID, max_ticks: int | None = None) -> None:
    """Execute a live run until stop is requested.

    This is intentionally simple for MVP: the same worker can run this job as a
    long-lived loop, while other job types can be handled by separate workers.
    """

    run = session.get(RunRow, run_id)
    if run is None:
        raise ValueError(f"run_id not found: {run_id}")

    cfg_row = session.get(RunConfigSnapshotRow, run.config_id)
    if cfg_row is None:
        raise ValueError(f"config_id not found: {run.config_id}")

    cfg = RunConfigSnapshotV1.model_validate(cfg_row.config)
    if cfg.mode != RunMode.live:
        raise ValueError(f"run_id={run_id} is not a live run (mode={cfg.mode})")

    run.status = "running"
    run.started_at = _now()
    run.updated_at = _now()
    session.commit()

    append_event(
        session,
        ev=make_event_v1(
            event_type="run.started",
            source="orchestrator.live",
            observed_at=_now(),
            dedupe_key="started",
            run_id=run_id,
            payload=RunStartedPayloadV1(run_id=run_id, mode="live").model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )
    session.commit()

    rng = random.Random(run_id.int & 0xFFFFFFFF)
    gateway = LlmGateway()

    fee_bps = Decimal(str(cfg.execution.fee_bps))
    state = PortfolioState(
        cash_quote=Decimal(str(cfg.execution.initial_equity_quote)), positions_base={}
    )
    last_target = Decimal("0")
    memory: list[dict] = []

    # Live state caches.
    latest_price: tuple[datetime, Decimal] | None = None
    ohlcv_bars: list[MarketOHLCVPayloadV1] = []
    sentiment_summaries: list[SentimentItemSummaryPayloadV1] = []

    bar_builder = _OhlcvBarBuilder(market_id=cfg.market_id, timeframe=cfg.prompt.timeframe)

    base_interval = timedelta(seconds=int(cfg.scheduler.base_interval_seconds))
    price_step = int(cfg.scheduler.price_tick_seconds)
    price_max_age = timedelta(seconds=price_step)

    start_tick = _ceil_time(_now(), step_seconds=price_step)
    next_base_tick = start_tick
    next_early_tick: datetime | None = None

    last_price_tick: datetime | None = None
    demo_price: Decimal | None = None
    tick_count = 0

    while True:
        # Refresh stop flag.
        session.refresh(run)
        if run.stop_requested:
            run.status = "cancelled"
            run.ended_at = _now()
            run.updated_at = _now()
            session.commit()
            return

        now = _now()

        # Emit price ticks on a stable cadence (bucketed).
        price_tick_time = _floor_time(now, step_seconds=price_step)
        if last_price_tick is None or price_tick_time > last_price_tick:
            price, raw, demo_price = _fetch_live_price(
                cfg=cfg.live,
                market_id=cfg.market_id,
                rng=rng,
                demo_price=demo_price,
            )
            last_price_tick = price_tick_time
            latest_price = (price_tick_time, price)

            append_event(
                session,
                ev=make_event_v1(
                    event_type="market.price",
                    source="ingest.live",
                    observed_at=price_tick_time,
                    event_time=price_tick_time,
                    dedupe_key=f"{cfg.market_id}:{price_tick_time.isoformat()}",
                    run_id=run_id,
                    payload=MarketPricePayloadV1(
                        market_id=cfg.market_id,
                        price=decimal_to_str(price),
                    ).model_dump(mode="json"),
                    raw_payload=raw,
                ),
                dedupe_scope="run",
            )

            closed = bar_builder.update(ts=price_tick_time, price=price)
            if closed is not None:
                append_event(
                    session,
                    ev=make_event_v1(
                        event_type="market.ohlcv",
                        source="ingest.live",
                        observed_at=closed.bar_end,
                        event_time=closed.bar_end,
                        dedupe_key=f"{cfg.market_id}:{closed.timeframe}:{closed.bar_start.isoformat()}",
                        run_id=run_id,
                        payload=closed.model_dump(mode="json"),
                    ),
                    dedupe_scope="run",
                )
                ohlcv_bars.append(closed)
                ohlcv_bars = ohlcv_bars[-1000:]

            session.commit()

        # Decide whether we have a scheduled tick to run.
        tick_time = next_base_tick
        if next_early_tick is not None and next_early_tick < tick_time:
            tick_time = next_early_tick

        now = _now()
        if now < tick_time:
            # Sleep until the next price tick or scheduled tick, whichever is sooner.
            next_price_emit = (last_price_tick or price_tick_time) + timedelta(seconds=price_step)
            wake_at = min(next_price_emit, tick_time)
            sleep_s = max(0.0, min(0.75, (wake_at - now).total_seconds()))
            time.sleep(sleep_s)
            continue

        # If we just consumed an early tick, clear it; base ticks remain anchored.
        if next_early_tick is not None and tick_time == next_early_tick:
            next_early_tick = None
        if tick_time == next_base_tick:
            next_base_tick = next_base_tick + base_interval

        # Guard: require fresh price.
        if latest_price is None:
            continue
        price_ts, price = latest_price
        if tick_time - price_ts > price_max_age:
            continue

        usable_bars = [b for b in ohlcv_bars if b.bar_end <= tick_time]
        usable_bars = usable_bars[-int(cfg.prompt.lookback_bars) :]
        closes = [b.c for b in usable_bars]

        features: dict | None = None
        if len(closes) >= 2:
            try:
                c0 = Decimal(closes[0])
                c1 = Decimal(closes[-1])
                momentum = c1 - c0
                ret_pct = ((c1 / c0) - 1) * Decimal("100") if c0 != 0 else None
                features = {
                    "momentum": decimal_to_str(momentum),
                    "return_pct": decimal_to_str(ret_pct) if ret_pct is not None else None,
                }
            except Exception:
                features = None

        recent_summaries = [s for s in sentiment_summaries if s.item_time <= tick_time]
        recent_summaries = recent_summaries[-20:]

        portfolio_view = {
            "equity_quote": decimal_to_str(
                state.equity_quote(market_id=cfg.market_id, price=price)
            ),
            "cash_quote": decimal_to_str(state.cash_quote),
            "position_qty_base": decimal_to_str(state.position_qty(cfg.market_id)),
            "price": decimal_to_str(price),
        }

        # Prompt-only time masking.
        mask_offset = timedelta(seconds=int(cfg.prompt.masking.time_offset_seconds))
        prompt_tick_time = tick_time + mask_offset

        masked_memory: list[dict] = []
        if mask_offset.total_seconds() == 0:
            masked_memory = memory[-3:]
        else:
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
                        pass
                masked_memory.append(mm)

        ctx = build_default_prompt_context(
            market_id=cfg.market_id,
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
                }
                for s in recent_summaries
            ],
            portfolio=portfolio_view,
            memory=masked_memory,
        )

        template_vars = cfg.prompt.template.vars or {}
        render_ctx = {**template_vars, **ctx, "vars": template_vars}
        system_prompt = render_mustache(template=cfg.prompt.template.system, context=render_ctx)
        user_prompt = render_mustache(template=cfg.prompt.template.user, context=render_ctx)

        call = gateway.call_decision(
            session,
            run_id=run_id,
            observed_at=tick_time,
            model_key=cfg.model.key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            stub_features=StubDecisionFeatures(market_id=cfg.market_id, closes=closes),
            temperature=cfg.model.temperature,
            max_output_tokens=cfg.model.max_output_tokens,
        )

        accepted = True
        reject_reason: str | None = None
        effective_target = last_target

        if call.error is not None:
            accepted = False
            reject_reason = f"llm_error: {call.error}"[:300]

        if call.decision.targets:
            if set(call.decision.targets.keys()) - {cfg.market_id}:
                accepted = False
                reject_reason = "targets contains unknown market_id"
            else:
                proposed = call.decision.targets.get(cfg.market_id)
                if proposed is None:
                    effective_target = last_target
                elif proposed < 0:
                    accepted = False
                    reject_reason = "spot exposure must be >= 0"
                elif proposed > Decimal(str(cfg.execution.gross_leverage_cap)):
                    accepted = False
                    reject_reason = "exposure exceeds gross_leverage_cap"
                elif proposed > Decimal(str(cfg.execution.net_exposure_cap)):
                    accepted = False
                    reject_reason = "exposure exceeds net_exposure_cap"
                else:
                    effective_target = proposed

        if not accepted:
            effective_target = last_target

        requested = call.decision.next_check_seconds
        honored: int | None = None
        if requested is not None:
            honored_raw = max(
                int(cfg.scheduler.min_interval_seconds),
                min(int(requested), int(cfg.scheduler.base_interval_seconds)),
            )
            honored = _ceil_seconds(honored_raw, step=price_step)
            candidate = tick_time + timedelta(seconds=honored)
            candidate = _ceil_time(candidate, step_seconds=price_step)
            if candidate < next_base_tick:
                next_early_tick = candidate
            else:
                honored = None

            append_event(
                session,
                ev=make_event_v1(
                    event_type="llm.schedule_request",
                    source="orchestrator.live",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=LlmScheduleRequestPayloadV1(
                        tick_time=tick_time,
                        requested_seconds=int(requested),
                        honored_seconds=honored,
                    ).model_dump(mode="json"),
                ),
                dedupe_scope="run",
            )

        decision_payload = LlmDecisionPayloadV1(
            tick_time=tick_time,
            market_id=cfg.market_id,
            targets={cfg.market_id: decimal_to_str(effective_target)},
            llm_call_id=call.call_id,
            accepted=accepted,
            reject_reason=reject_reason,
            next_check_seconds=requested,
            confidence=decimal_to_str(call.decision.confidence)
            if call.decision.confidence is not None
            else None,
            key_signals=call.decision.key_signals,
            rationale=call.decision.rationale,
        )
        append_event(
            session,
            ev=make_event_v1(
                event_type="llm.decision",
                source="orchestrator.live",
                observed_at=tick_time,
                dedupe_key=tick_time.isoformat(),
                run_id=run_id,
                payload=decision_payload.model_dump(mode="json"),
            ),
            dedupe_scope="run",
        )

        memory.append(decision_payload.model_dump(mode="json"))
        memory = memory[-50:]

        fill = rebalance_to_target_exposure(
            state=state,
            market_id=cfg.market_id,
            price=price,
            target_exposure=effective_target,
            fee_bps=fee_bps,
        )
        if fill is not None:
            side = SimFillSide.buy if fill.qty_base > 0 else SimFillSide.sell
            fill_payload = SimFillPayloadV1(
                tick_time=tick_time,
                market_id=cfg.market_id,
                side=side,
                qty_base=decimal_to_str(fill.qty_base),
                price=decimal_to_str(fill.price),
                notional_quote=decimal_to_str(fill.notional_quote),
                fee_quote=decimal_to_str(fill.fee_quote),
            ).model_dump(mode="json")

            append_event(
                session,
                ev=make_event_v1(
                    event_type="sim.fill",
                    source="orchestrator.live",
                    observed_at=tick_time,
                    dedupe_key=f"{tick_time.isoformat()}:{cfg.market_id}",
                    run_id=run_id,
                    payload=fill_payload,
                ),
                dedupe_scope="run",
            )

        equity = state.equity_quote(market_id=cfg.market_id, price=price)
        snap_payload = PortfolioSnapshotPayloadV1(
            snapshot_time=tick_time,
            equity_quote=decimal_to_str(equity),
            cash_quote=decimal_to_str(state.cash_quote),
            positions_base={cfg.market_id: decimal_to_str(state.position_qty(cfg.market_id))},
        ).model_dump(mode="json")
        append_event(
            session,
            ev=make_event_v1(
                event_type="portfolio.snapshot",
                source="orchestrator.live",
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
                    cash_quote=state.cash_quote,
                    positions={cfg.market_id: decimal_to_str(state.position_qty(cfg.market_id))},
                )
            )
        else:
            existing.equity_quote = equity
            existing.cash_quote = state.cash_quote
            existing.positions = {cfg.market_id: decimal_to_str(state.position_qty(cfg.market_id))}

        last_target = effective_target
        session.commit()

        tick_count += 1
        if max_ticks is not None and tick_count >= max_ticks:
            return
