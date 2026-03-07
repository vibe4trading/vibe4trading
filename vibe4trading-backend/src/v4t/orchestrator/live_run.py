from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.benchmark.spec import PositionMode
from v4t.contracts.events import make_event
from v4t.contracts.numbers import decimal_to_str
from v4t.contracts.payloads import (
    LlmDecisionPayload,
    LlmStreamDeltaPayload,
    LlmStreamEndPayload,
    LlmStreamStartPayload,
    MarketOHLCVPayload,
    MarketPricePayload,
    SentimentItemSummaryPayload,
)
from v4t.contracts.run_config import LiveConfig, RunMode
from v4t.db.event_store import append_event
from v4t.db.models import EventRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.orchestrator.prompt_builder import render_user_prompt
from v4t.orchestrator.run_base import (
    advance_base_tick,
    append_decision_memory,
    append_sim_fill_event,
    build_prompt_context,
    compute_features,
    get_strategy_prompt,
    get_system_prompt,
    load_run_and_config,
    mark_run_cancelled,
    mark_run_finished,
    mark_run_started,
    select_usable_bars,
    validate_decision,
    write_portfolio_snapshot,
)
from v4t.sim.benchmark_sim import BenchmarkPaperSim
from v4t.utils.datetime import as_utc, ceil_time, floor_time, now

_logger = logging.getLogger(__name__)


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

    def update(self, *, ts: datetime, price: Decimal) -> MarketOHLCVPayload | None:
        """Update the current bar and return a closed bar if we rolled."""

        ts = as_utc(ts)
        step = _timeframe_to_seconds(self.timeframe)
        new_start = floor_time(ts, step_seconds=step)
        new_end = new_start + timedelta(seconds=step)

        closed: MarketOHLCVPayload | None = None
        if self.bar_start is None:
            # First tick creates the initial bar.
            self.bar_start = new_start
            self.bar_end = new_end
        elif new_start != self.bar_start:
            # Roll: close previous bar (if it has data).
            if self.c is not None:
                closed = MarketOHLCVPayload(
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
    cfg: LiveConfig,
    market_id: str,
    rng: random.Random,
    demo_price: Decimal | None,
) -> tuple[Decimal, dict[str, str | int], Decimal]:
    if cfg.source != "demo":
        raise ValueError(f"Unknown live.source={cfg.source}")

    step_bp = rng.randint(-int(cfg.step_bps), int(cfg.step_bps))
    drift_bp = int(cfg.drift_bps)
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


def execute_live_run(session: Session, *, run_id: UUID, max_ticks: int | None = None) -> None:
    """Execute a live run until stop is requested.

    This is intentionally simple for MVP: the same worker can run this job as a
    long-lived loop, while other job types can be handled by separate workers.
    """

    run, cfg = load_run_and_config(session, run_id=run_id, expected_mode=RunMode.live)
    mark_run_started(
        session,
        run=run,
        run_id=run_id,
        mode="live",
        source="orchestrator.live",
    )

    rng = random.Random(run_id.int & 0xFFFFFFFF)
    gateway = LlmGateway()

    fee_bps = Decimal(str(cfg.execution.fee_bps))
    sim = BenchmarkPaperSim(
        market_id=cfg.market_id,
        initial_equity_quote=Decimal(str(cfg.execution.initial_equity_quote)),
        fee_bps=fee_bps,
    )
    last_target = Decimal("0")
    last_mode = PositionMode.spot
    last_leverage = 1
    memory: list[dict[str, object]] = []

    # Live state caches.
    latest_price: tuple[datetime, Decimal] | None = None
    ohlcv_bars: list[MarketOHLCVPayload] = []
    sentiment_summaries: list[SentimentItemSummaryPayload] = []

    bar_builder = _OhlcvBarBuilder(market_id=cfg.market_id, timeframe=cfg.prompt.timeframe)

    base_interval = timedelta(seconds=int(cfg.scheduler.base_interval_seconds))
    price_step = int(cfg.scheduler.price_tick_seconds)
    price_max_age = timedelta(seconds=price_step)

    start_tick = ceil_time(now(), step_seconds=price_step)
    next_base_tick = start_tick

    last_price_tick: datetime | None = None
    demo_price: Decimal | None = None
    tick_count = 0

    try:
        while True:
            # Refresh stop flag.
            session.refresh(run)
            if run.stop_requested:
                mark_run_cancelled(session, run=run)
                return

            current_time = now()
            sentiment_rows = list(
                session.execute(
                    select(EventRow)
                    .where(EventRow.event_type == "sentiment.item_summary")
                    .where(EventRow.run_id == run_id)
                    .order_by(EventRow.observed_at.desc())
                    .limit(20)
                )
                .scalars()
                .all()
            )
            sentiment_summaries = [
                SentimentItemSummaryPayload.model_validate(r.payload)
                for r in reversed(sentiment_rows)
            ]

            # Emit price ticks on a stable cadence (bucketed).
            price_tick_time = floor_time(current_time, step_seconds=price_step)
            if last_price_tick is None or price_tick_time > last_price_tick:
                price, raw, demo_price = _fetch_live_price(
                    cfg=cfg.live,
                    market_id=cfg.market_id,
                    rng=rng,
                    demo_price=demo_price,
                )
                last_price_tick = price_tick_time
                latest_price = (price_tick_time, price)
                trigger_fill = sim.process_price_update(tick_time=price_tick_time, price=price)
                if trigger_fill is not None:
                    append_sim_fill_event(
                        session,
                        source="orchestrator.live",
                        tick_time=price_tick_time,
                        run_id=run_id,
                        market_id=cfg.market_id,
                        fill=trigger_fill,
                    )
                sim.maybe_apply_default_funding(
                    tick_time=price_tick_time,
                    price=price,
                    funding_rate=Decimal(str(cfg.execution.funding_rate_per_8h)),
                )

                append_event(
                    session,
                    ev=make_event(
                        event_type="market.price",
                        source="ingest.live",
                        observed_at=price_tick_time,
                        event_time=price_tick_time,
                        dedupe_key=f"{cfg.market_id}:{price_tick_time.isoformat()}",
                        run_id=run_id,
                        payload=MarketPricePayload(
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
                        ev=make_event(
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

            current_time = now()
            if current_time < tick_time:
                # Sleep until the next price tick or scheduled tick, whichever is sooner.
                next_price_emit = (last_price_tick or price_tick_time) + timedelta(
                    seconds=price_step
                )
                wake_at = min(next_price_emit, tick_time)
                sleep_s = max(0.0, min(0.75, (wake_at - current_time).total_seconds()))
                time.sleep(sleep_s)
                continue

            next_base_tick = advance_base_tick(
                next_base_tick=next_base_tick,
                base_interval=base_interval,
            )

            # Guard: require fresh price.
            if latest_price is None:
                continue
            price_ts, price = latest_price
            if tick_time - price_ts > price_max_age:
                continue

            usable_bars = select_usable_bars(
                ohlcv_bars,
                tick_time=tick_time,
                lookback_bars=int(cfg.prompt.lookback_bars),
                timeframe=cfg.prompt.timeframe,
            )
            closes = [b.c for b in usable_bars]
            features = compute_features(closes)

            portfolio_view = sim.portfolio_view(price=price)

            mask_offset = timedelta(seconds=int(cfg.prompt.masking.time_offset_seconds))
            prompt_ctx = build_prompt_context(
                market_id=cfg.market_id,
                tick_time=tick_time,
                mask_offset=mask_offset,
                timeframe=cfg.prompt.timeframe,
                latest_price=(price_ts, portfolio_view["price"]),
                ohlcv_bars=usable_bars,
                closes=closes,
                features=features,
                sentiment_summaries=sentiment_summaries,
                portfolio_view=portfolio_view,
                memory=memory,
            )

            user_prompt = render_user_prompt(
                style_text=get_strategy_prompt(cfg),
                context=prompt_ctx,
                include=list(cfg.prompt.include or []),
            )

            append_event(
                session,
                ev=make_event(
                    event_type="llm.stream_start",
                    source="orchestrator.live",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=LlmStreamStartPayload(tick_time=tick_time).model_dump(mode="json"),
                ),
                dedupe_scope="run",
            )
            session.commit()

            seq = 0
            last_commit = time.perf_counter()

            def _on_delta(delta: str, *, _tick_time: datetime = tick_time) -> None:
                nonlocal seq, last_commit
                seq += 1
                append_event(
                    session,
                    ev=make_event(
                        event_type="llm.stream_delta",
                        source="orchestrator.live",
                        observed_at=_tick_time,
                        dedupe_key=f"{_tick_time.isoformat()}:{seq}",
                        run_id=run_id,
                        payload=LlmStreamDeltaPayload(
                            tick_time=_tick_time, seq=seq, delta=delta
                        ).model_dump(mode="json"),
                    ),
                    dedupe_scope="run",
                )

                now_perf = time.perf_counter()
                if seq % 20 == 0 or (now_perf - last_commit) >= 0.25:
                    try:
                        session.commit()
                    except Exception:
                        _logger.exception("streaming_commit_failed run_id=%s", str(run_id))
                        session.rollback()
                        raise RuntimeError("streaming commit failed") from None
                    last_commit = now_perf

            call = gateway.call_decision_streaming(
                session,
                run_id=run_id,
                observed_at=tick_time,
                model_key=cfg.model.key,
                system_prompt=get_system_prompt(cfg),
                user_prompt=user_prompt,
                stub_features=StubDecisionFeatures(
                    market_id=cfg.market_id,
                    closes=closes,
                    risk_level=cfg.risk_level,
                ),
                on_delta=_on_delta,
                temperature=cfg.model.temperature,
                max_output_tokens=cfg.model.max_output_tokens,
            )

            append_event(
                session,
                ev=make_event(
                    event_type="llm.stream_end",
                    source="orchestrator.live",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=LlmStreamEndPayload(tick_time=tick_time, error=call.error).model_dump(
                        mode="json"
                    ),
                ),
                dedupe_scope="run",
            )
            session.commit()

            validated = validate_decision(
                decision=call.decision,
                market_id=cfg.market_id,
                last_target=last_target,
                last_mode=last_mode,
                last_leverage=last_leverage,
                gross_leverage_cap=Decimal(str(cfg.execution.gross_leverage_cap)),
                net_exposure_cap=Decimal(str(cfg.execution.net_exposure_cap)),
                call_error=call.error,
                risk_level=cfg.risk_level,
            )

            decision_payload = LlmDecisionPayload(
                tick_time=tick_time,
                market_id=cfg.market_id,
                targets={cfg.market_id: decimal_to_str(validated.effective_target)},
                target=decimal_to_str(validated.effective_target),
                mode=validated.mode.value,
                leverage=validated.leverage,
                stop_loss_pct=decimal_to_str(validated.stop_loss_pct)
                if validated.stop_loss_pct is not None
                else None,
                take_profit_pct=decimal_to_str(validated.take_profit_pct)
                if validated.take_profit_pct is not None
                else None,
                llm_call_id=call.call_id,
                accepted=validated.accepted,
                reject_reason=validated.reject_reason,
                confidence=decimal_to_str(validated.confidence)
                if validated.confidence is not None
                else None,
                key_signals=validated.key_signals,
                rationale=validated.rationale,
            )
            append_event(
                session,
                ev=make_event(
                    event_type="llm.decision",
                    source="orchestrator.live",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=decision_payload.model_dump(mode="json"),
                ),
                dedupe_scope="run",
            )

            memory = append_decision_memory(memory, decision_payload.model_dump(mode="json"))

            fills = sim.rebalance_to_target(
                tick_time=tick_time,
                price=price,
                target_exposure=validated.effective_target,
                mode=validated.mode,
                leverage=validated.leverage,
                stop_loss_pct=validated.stop_loss_pct,
                take_profit_pct=validated.take_profit_pct,
                reason="rebalance",
            )
            for fill_index, fill in enumerate(fills):
                append_sim_fill_event(
                    session,
                    source="orchestrator.live",
                    tick_time=tick_time,
                    run_id=run_id,
                    market_id=cfg.market_id,
                    fill=fill,
                    fill_index=fill_index,
                )

            equity = sim.equity_quote(price=price)
            cash = sim.cash_quote()
            pos = sim.position_qty_base()
            portfolio_view = sim.portfolio_view(price=price)
            extra_payload: dict[str, str | int | None] = {
                "position_mode": portfolio_view.get("position_mode"),
                "position_direction": portfolio_view.get("position_direction"),
                "position_qty_base": portfolio_view.get("position_qty_base"),
                "position_leverage": int(portfolio_view.get("position_leverage", "1")),
                "entry_price": None
                if portfolio_view.get("entry_price") == "n/a"
                else portfolio_view.get("entry_price"),
                "current_price": portfolio_view.get("current_price"),
                "liquidation_price": None
                if portfolio_view.get("liquidation_price") == "n/a"
                else portfolio_view.get("liquidation_price"),
                "unrealized_pnl": portfolio_view.get("unrealized_pnl"),
                "unrealized_pnl_pct": portfolio_view.get("unrealized_pnl_pct"),
                "funding_cost_accumulated": portfolio_view.get("funding_cost_accumulated"),
                "stop_loss_price": None
                if portfolio_view.get("stop_loss_price") == "n/a"
                else portfolio_view.get("stop_loss_price"),
                "take_profit_price": None
                if portfolio_view.get("take_profit_price") == "n/a"
                else portfolio_view.get("take_profit_price"),
            }
            write_portfolio_snapshot(
                session,
                source="orchestrator.live",
                tick_time=tick_time,
                run_id=run_id,
                market_id=cfg.market_id,
                equity=equity,
                cash=cash,
                position_base=pos,
                extra_payload=extra_payload,
            )

            last_target = validated.effective_target
            last_mode = validated.mode
            last_leverage = validated.leverage
            session.commit()

            tick_count += 1
            if max_ticks is not None and tick_count >= max_ticks:
                start_equity = Decimal(str(cfg.execution.initial_equity_quote))
                end_equity = sim.equity_quote(price=price)
                return_pct = (
                    ((end_equity / start_equity) - 1) * Decimal("100")
                    if start_equity != 0
                    else Decimal("0")
                )
                mark_run_finished(
                    session,
                    run=run,
                    run_id=run_id,
                    source="orchestrator.live",
                    return_pct=return_pct,
                    summary_call_id=None,
                    summary_text=None,
                )
                return
    finally:
        sim.close()
