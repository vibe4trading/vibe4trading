from __future__ import annotations

import json
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
    RunFinishedPayloadV1,
    RunStartedPayloadV1,
    SentimentItemSummaryPayloadV1,
    SimFillPayloadV1,
    SimFillSide,
)
from fce.contracts.run_config import RunConfigSnapshotV1
from fce.db.event_store import append_event
from fce.db.models import DatasetRow, PortfolioSnapshotRow, RunConfigSnapshotRow, RunRow
from fce.llm.gateway import LlmGateway, StubDecisionFeatures
from fce.orchestrator.prompt_builder import (
    build_default_prompt_context,
    render_mustache,
)
from fce.replay.stream import iter_dataset_events
from fce.sim.engine import PortfolioState, rebalance_to_target_exposure


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    # SQLite doesn't preserve tzinfo; treat naive timestamps as UTC.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _ceil_seconds(delta_seconds: int, *, step: int) -> int:
    if step <= 0:
        return delta_seconds
    if delta_seconds % step == 0:
        return delta_seconds
    return ((delta_seconds // step) + 1) * step


def execute_replay_run(session: Session, *, run_id: UUID) -> None:
    run = session.get(RunRow, run_id)
    if run is None:
        raise ValueError(f"run_id not found: {run_id}")

    cfg_row = session.get(RunConfigSnapshotRow, run.config_id)
    if cfg_row is None:
        raise ValueError(f"config_id not found: {run.config_id}")

    cfg = RunConfigSnapshotV1.model_validate(cfg_row.config)

    spot_dataset_id = cfg.datasets.spot_dataset_id
    sentiment_dataset_id = cfg.datasets.sentiment_dataset_id
    if spot_dataset_id is None:
        raise ValueError("Replay run requires datasets.spot_dataset_id")
    if sentiment_dataset_id is None:
        raise ValueError("Replay run requires datasets.sentiment_dataset_id (may be empty)")

    spot_ds = session.get(DatasetRow, spot_dataset_id)
    sent_ds = session.get(DatasetRow, sentiment_dataset_id)
    if spot_ds is None or sent_ds is None:
        raise ValueError("Referenced dataset_id not found")
    if spot_ds.status != "ready" or sent_ds.status != "ready":
        raise ValueError("Referenced datasets must be status=ready")
    if spot_ds.start != sent_ds.start or spot_ds.end != sent_ds.end:
        raise ValueError("Dataset windows must match exactly (start/end)")

    window_start = _as_utc(spot_ds.start)
    window_end = _as_utc(spot_ds.end)

    run.status = "running"
    run.started_at = _now()
    run.updated_at = _now()
    session.commit()

    append_event(
        session,
        ev=make_event_v1(
            event_type="run.started",
            source="orchestrator.replay",
            observed_at=_now(),
            dedupe_key="started",
            run_id=run_id,
            payload=RunStartedPayloadV1(run_id=run_id, mode="replay").model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )
    session.commit()

    events = iter_dataset_events(
        session,
        dataset_ids=[spot_dataset_id, sentiment_dataset_id],
        start=window_start,
        end=window_end,
    )

    # Replay state caches.
    latest_price: tuple[datetime, Decimal] | None = None
    ohlcv_bars: list[MarketOHLCVPayloadV1] = []
    sentiment_summaries: list[SentimentItemSummaryPayloadV1] = []

    # Portfolio state.
    fee_bps = Decimal(str(cfg.execution.fee_bps))
    state = PortfolioState(
        cash_quote=Decimal(str(cfg.execution.initial_equity_quote)),
        positions_base={},
    )

    # Decision memory (last 3 payloads for prompt context).
    memory: list[dict] = []
    last_target = Decimal("0")

    base_interval = timedelta(seconds=cfg.scheduler.base_interval_seconds)
    base_tick = window_start
    next_base_tick = base_tick
    next_early_tick: datetime | None = None

    price_max_age = timedelta(seconds=cfg.scheduler.price_tick_seconds)

    i = 0
    while True:
        tick_time = next_base_tick
        if next_early_tick is not None and next_early_tick < tick_time:
            tick_time = next_early_tick

        if tick_time > window_end:
            break

        # Advance event stream up to tick_time.
        while i < len(events) and _as_utc(events[i].observed_at) <= tick_time:
            ev = events[i]
            i += 1
            if ev.event_type == "market.price":
                p = MarketPricePayloadV1.model_validate(ev.payload)
                if p.market_id == cfg.market_id:
                    latest_price = (_as_utc(ev.observed_at), Decimal(p.price))
            elif ev.event_type == "market.ohlcv":
                b = MarketOHLCVPayloadV1.model_validate(ev.payload)
                if b.market_id == cfg.market_id:
                    ohlcv_bars.append(b)
            elif ev.event_type == "sentiment.item_summary":
                s = SentimentItemSummaryPayloadV1.model_validate(ev.payload)
                sentiment_summaries.append(s)

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

        # Prompt inputs.
        usable_bars = [b for b in ohlcv_bars if b.bar_end <= tick_time]
        usable_bars = usable_bars[-cfg.prompt.lookback_bars :]
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

        # Prompt-only time masking: shift any timestamps shown to the model while keeping
        # internal replay clock and outputs unchanged.
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

        # Template variables are prompt-only inputs; they don't affect replay determinism.
        # Built-in context keys win on conflicts.
        template_vars = cfg.prompt.template.vars or {}
        render_ctx = {**template_vars, **ctx, "vars": template_vars}

        system_prompt = render_mustache(template=cfg.prompt.template.system, context=render_ctx)
        user_prompt = render_mustache(template=cfg.prompt.template.user, context=render_ctx)

        gateway = LlmGateway()
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

        # Validate decision against MVP constraint: exactly one market_id.
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
                    # Missing => hold previous.
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

        # Schedule request (log even if ignored).
        requested = call.decision.next_check_seconds
        honored: int | None = None
        if requested is not None:
            honored_raw = max(
                cfg.scheduler.min_interval_seconds,
                min(requested, cfg.scheduler.base_interval_seconds),
            )
            honored = _ceil_seconds(honored_raw, step=cfg.scheduler.price_tick_seconds)
            candidate = tick_time + timedelta(seconds=honored)
            if candidate < next_base_tick:
                next_early_tick = candidate
            else:
                honored = None

            append_event(
                session,
                ev=make_event_v1(
                    event_type="llm.schedule_request",
                    source="orchestrator.replay",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=LlmScheduleRequestPayloadV1(
                        tick_time=tick_time,
                        requested_seconds=requested,
                        honored_seconds=honored,
                    ).model_dump(mode="json"),
                ),
                dedupe_scope="run",
            )

        # Persist decision event.
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
                source="orchestrator.replay",
                observed_at=tick_time,
                dedupe_key=tick_time.isoformat(),
                run_id=run_id,
                payload=decision_payload.model_dump(mode="json"),
            ),
            dedupe_scope="run",
        )

        memory.append(decision_payload.model_dump(mode="json"))

        # Execute simulation.
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
                    source="orchestrator.replay",
                    observed_at=tick_time,
                    dedupe_key=f"{tick_time.isoformat()}:{cfg.market_id}",
                    run_id=run_id,
                    payload=fill_payload,
                ),
                dedupe_scope="run",
            )

        # Portfolio snapshot event + projection.
        equity = state.equity_quote(market_id=cfg.market_id, price=price)
        snap_payload = PortfolioSnapshotPayloadV1(
            snapshot_time=tick_time,
            equity_quote=decimal_to_str(equity),
            cash_quote=decimal_to_str(state.cash_quote),
            positions_base={
                cfg.market_id: decimal_to_str(state.position_qty(cfg.market_id)),
            },
        ).model_dump(mode="json")
        append_event(
            session,
            ev=make_event_v1(
                event_type="portfolio.snapshot",
                source="orchestrator.replay",
                observed_at=tick_time,
                dedupe_key=tick_time.isoformat(),
                run_id=run_id,
                payload=snap_payload,
            ),
            dedupe_scope="run",
        )

        # Projection table (fast reads).
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

        # Commit each tick so the dashboard can poll progress.
        session.commit()

        # Stop flag support.
        session.refresh(run)
        if run.stop_requested:
            run.status = "cancelled"
            run.ended_at = _now()
            run.updated_at = _now()
            session.commit()
            return

    # Summary stage.
    start_equity = Decimal(str(cfg.execution.initial_equity_quote))
    end_equity = state.equity_quote(
        market_id=cfg.market_id, price=latest_price[1] if latest_price else Decimal("0")
    )
    ret_pct = (
        ((end_equity / start_equity) - 1) * Decimal("100") if start_equity != 0 else Decimal("0")
    )

    summary_system = "You are a trading run reviewer."
    summary_user = json.dumps(
        {
            "run_id": str(run_id),
            "market_id": cfg.market_id,
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "start_equity": decimal_to_str(start_equity),
            "end_equity": decimal_to_str(end_equity),
            "return_pct": decimal_to_str(ret_pct),
        },
        indent=2,
    )
    gateway = LlmGateway()
    summary_call_id, summary_text = gateway.call_summary(
        session,
        run_id=run_id,
        observed_at=_now(),
        model_key=cfg.summary.model_key or cfg.model.key,
        system_prompt=summary_system,
        user_prompt=summary_user,
    )

    run.status = "finished"
    run.ended_at = _now()
    run.summary_call_id = summary_call_id
    run.summary_text = summary_text
    run.updated_at = _now()

    append_event(
        session,
        ev=make_event_v1(
            event_type="run.finished",
            source="orchestrator.replay",
            observed_at=_now(),
            dedupe_key="finished",
            run_id=run_id,
            payload=RunFinishedPayloadV1(
                run_id=run_id,
                return_pct=decimal_to_str(ret_pct),
            ).model_dump(mode="json"),
        ),
        dedupe_scope="run",
    )

    session.commit()
