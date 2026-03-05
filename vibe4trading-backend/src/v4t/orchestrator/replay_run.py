from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.contracts.events import make_event_v1
from v4t.contracts.numbers import decimal_to_str
from v4t.contracts.payloads import (
    LlmDecisionPayloadV1,
    LlmStreamDeltaPayloadV1,
    LlmStreamEndPayloadV1,
    LlmStreamStartPayloadV1,
    MarketOHLCVPayloadV1,
    MarketPricePayloadV1,
    SentimentItemSummaryPayloadV1,
)
from v4t.db.event_store import append_event
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, DatasetRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.orchestrator.prompt_builder import render_user_prompt
from v4t.orchestrator.run_base import (
    SYSTEM_PROMPT,
    advance_schedule,
    append_decision_memory,
    append_schedule_request_event,
    append_sim_fill_event,
    build_prompt_context,
    choose_tick_time,
    compute_early_tick,
    compute_features,
    load_run_and_config,
    mark_run_cancelled,
    mark_run_finished,
    mark_run_started,
    select_usable_bars,
    validate_decision_targets,
    write_portfolio_snapshot,
)
from v4t.replay.stream import iter_dataset_events
from v4t.sim.nautilus_sim import NautilusPaperSim
from v4t.utils.datetime import as_utc, now

_logger = logging.getLogger(__name__)


def execute_replay_run(session: Session, *, run_id: UUID) -> None:
    run, cfg = load_run_and_config(session, run_id=run_id)

    market_dataset_id = cfg.datasets.market_dataset_id
    sentiment_dataset_id = cfg.datasets.sentiment_dataset_id
    if market_dataset_id is None:
        raise ValueError("Replay run requires datasets.market_dataset_id")

    market_ds = session.get(DatasetRow, market_dataset_id)
    if market_ds is None:
        raise ValueError("Referenced dataset_id not found")
    if market_ds.status != "ready":
        raise ValueError("Referenced datasets must be status=ready")

    window_start = as_utc(market_ds.start)
    window_end = as_utc(market_ds.end)
    data_start = window_start

    dataset_ids: list[UUID] = [market_dataset_id]
    if sentiment_dataset_id is not None:
        sent_ds = session.get(DatasetRow, sentiment_dataset_id)
        if sent_ds is None:
            raise ValueError("Referenced dataset_id not found")
        if sent_ds.status != "ready":
            raise ValueError("Referenced datasets must be status=ready")
        if as_utc(market_ds.start) != as_utc(sent_ds.start) or as_utc(market_ds.end) != as_utc(
            sent_ds.end
        ):
            raise ValueError("Dataset windows must match exactly (start/end)")
        dataset_ids.append(sentiment_dataset_id)

    if run.kind == "tournament":
        link = (
            session.query(ArenaSubmissionRunRow)
            .filter(ArenaSubmissionRunRow.run_id == run_id)
            .one_or_none()
        )
        if link is None:
            raise ValueError("tournament run missing arena link")
        window_start = as_utc(link.window_start)
        window_end = as_utc(link.window_end)
        if window_end <= window_start:
            raise ValueError("invalid tournament window")
        if window_start < as_utc(market_ds.start) or window_end > as_utc(market_ds.end):
            raise ValueError("tournament window outside dataset range")

    mark_run_started(
        session,
        run=run,
        run_id=run_id,
        mode="replay",
        source="orchestrator.replay",
    )

    if run.kind == "tournament":
        link = (
            session.execute(
                select(ArenaSubmissionRunRow).where(ArenaSubmissionRunRow.run_id == run_id).limit(1)
            )
            .scalars()
            .one_or_none()
        )
        if link is not None:
            link.status = "running"
            link.started_at = run.started_at
            link.updated_at = now()
            session.commit()

    events = iter_dataset_events(
        session,
        dataset_ids=dataset_ids,
        start=data_start,
        end=window_end,
    )

    # Replay state caches.
    latest_price: tuple[datetime, Decimal] | None = None
    ohlcv_bars: list[MarketOHLCVPayloadV1] = []
    sentiment_summaries: list[SentimentItemSummaryPayloadV1] = []

    # Portfolio state (Nautilus-backed).
    fee_bps = Decimal(str(cfg.execution.fee_bps))
    sim = NautilusPaperSim(
        market_id=cfg.market_id,
        initial_equity_quote=Decimal(str(cfg.execution.initial_equity_quote)),
        fee_bps=fee_bps,
    )

    # Decision memory (last 3 payloads for prompt context).
    memory: list[dict] = []
    last_target = Decimal("0")

    base_interval = timedelta(seconds=cfg.scheduler.base_interval_seconds)
    next_base_tick = window_start
    next_early_tick: datetime | None = None

    price_max_age = timedelta(seconds=cfg.scheduler.price_tick_seconds)

    gateway = LlmGateway()

    try:
        i = 0
        while True:
            tick_time = choose_tick_time(next_base_tick, next_early_tick)

            if tick_time > window_end:
                break

            # Advance event stream up to tick_time.
            while i < len(events) and as_utc(events[i].observed_at) <= tick_time:
                ev = events[i]
                i += 1
                if ev.event_type == "market.price":
                    p = MarketPricePayloadV1.model_validate(ev.payload)
                    if p.market_id == cfg.market_id:
                        latest_price = (as_utc(ev.observed_at), Decimal(p.price))
                elif ev.event_type == "market.ohlcv":
                    b = MarketOHLCVPayloadV1.model_validate(ev.payload)
                    if b.market_id == cfg.market_id:
                        ohlcv_bars.append(b)
                elif ev.event_type == "sentiment.item_summary":
                    s = SentimentItemSummaryPayloadV1.model_validate(ev.payload)
                    sentiment_summaries.append(s)

            next_base_tick, next_early_tick = advance_schedule(
                tick_time=tick_time,
                next_base_tick=next_base_tick,
                next_early_tick=next_early_tick,
                base_interval=base_interval,
            )

            # Guard: require fresh price.
            if latest_price is None:
                continue
            price_ts, price = latest_price
            if tick_time - price_ts > price_max_age:
                continue

            # Prompt inputs.
            usable_bars = select_usable_bars(
                ohlcv_bars,
                tick_time=tick_time,
                lookback_bars=int(cfg.prompt.lookback_bars),
                timeframe=cfg.prompt.timeframe,
            )
            closes = [b.c for b in usable_bars]
            features = compute_features(closes)

            portfolio_view = {
                "equity_quote": decimal_to_str(sim.equity_quote(price=price)),
                "cash_quote": decimal_to_str(sim.cash_quote()),
                "position_qty_base": decimal_to_str(sim.position_qty_base()),
                "price": decimal_to_str(price),
            }

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
                style_text=cfg.prompt.prompt_text,
                context=prompt_ctx,
                include=list(cfg.prompt.include or []),
            )

            append_event(
                session,
                ev=make_event_v1(
                    event_type="llm.stream_start",
                    source="orchestrator.replay",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=LlmStreamStartPayloadV1(tick_time=tick_time).model_dump(mode="json"),
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
                    ev=make_event_v1(
                        event_type="llm.stream_delta",
                        source="orchestrator.replay",
                        observed_at=_tick_time,
                        dedupe_key=f"{_tick_time.isoformat()}:{seq}",
                        run_id=run_id,
                        payload=LlmStreamDeltaPayloadV1(
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
                        _logger.error("streaming_commit_failed", run_id=str(run_id), exc_info=True)
                        session.rollback()
                    last_commit = now_perf

            call = gateway.call_decision_streaming(
                session,
                run_id=run_id,
                observed_at=tick_time,
                model_key=cfg.model.key,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                stub_features=StubDecisionFeatures(market_id=cfg.market_id, closes=closes),
                on_delta=_on_delta,
                temperature=cfg.model.temperature,
                max_output_tokens=cfg.model.max_output_tokens,
            )

            append_event(
                session,
                ev=make_event_v1(
                    event_type="llm.stream_end",
                    source="orchestrator.replay",
                    observed_at=tick_time,
                    dedupe_key=tick_time.isoformat(),
                    run_id=run_id,
                    payload=LlmStreamEndPayloadV1(tick_time=tick_time, error=call.error).model_dump(
                        mode="json"
                    ),
                ),
                dedupe_scope="run",
            )
            session.commit()

            accepted, reject_reason, effective_target = validate_decision_targets(
                targets=call.decision.targets,
                market_id=cfg.market_id,
                last_target=last_target,
                gross_leverage_cap=Decimal(str(cfg.execution.gross_leverage_cap)),
                net_exposure_cap=Decimal(str(cfg.execution.net_exposure_cap)),
                call_error=call.error,
            )

            # Schedule request (log even if ignored).
            requested = call.decision.next_check_seconds
            honored: int | None = None
            if requested is not None:
                honored, candidate = compute_early_tick(
                    requested_seconds=int(requested),
                    min_interval_seconds=int(cfg.scheduler.min_interval_seconds),
                    base_interval_seconds=int(cfg.scheduler.base_interval_seconds),
                    step_seconds=int(cfg.scheduler.price_tick_seconds),
                    tick_time=tick_time,
                    next_base_tick=next_base_tick,
                    align_to_step=False,
                )
                if candidate is not None:
                    next_early_tick = candidate

                append_schedule_request_event(
                    session,
                    source="orchestrator.replay",
                    tick_time=tick_time,
                    run_id=run_id,
                    requested_seconds=int(requested),
                    honored_seconds=honored,
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

            memory = append_decision_memory(memory, decision_payload.model_dump(mode="json"))

            # Execute simulation.
            fill = sim.rebalance_to_target_exposure(
                tick_time=tick_time,
                price=price,
                target_exposure=effective_target,
            )
            if fill is not None:
                append_sim_fill_event(
                    session,
                    source="orchestrator.replay",
                    tick_time=tick_time,
                    run_id=run_id,
                    market_id=cfg.market_id,
                    fill=fill,
                )

            equity = sim.equity_quote(price=price)
            cash = sim.cash_quote()
            pos = sim.position_qty_base()
            write_portfolio_snapshot(
                session,
                source="orchestrator.replay",
                tick_time=tick_time,
                run_id=run_id,
                market_id=cfg.market_id,
                equity=equity,
                cash=cash,
                position_base=pos,
            )

            last_target = effective_target

            # Commit each tick so the dashboard can poll progress.
            session.commit()

            # Stop flag support.
            session.refresh(run)
            if run.stop_requested:
                mark_run_cancelled(session, run=run)
                if run.kind == "tournament":
                    link = (
                        session.execute(
                            select(ArenaSubmissionRunRow).where(
                                ArenaSubmissionRunRow.run_id == run_id
                            )
                        )
                        .scalars()
                        .one_or_none()
                    )
                    if link is not None:
                        link.status = "failed"
                        link.error = "cancelled"
                        link.ended_at = now()
                        link.updated_at = now()
                        sub = session.get(ArenaSubmissionRow, link.submission_id)
                        if sub is not None and sub.status not in {"finished", "failed"}:
                            sub.status = "failed"
                            sub.error = "cancelled"
                            sub.ended_at = now()
                            sub.updated_at = now()
                        session.commit()
                return

        # Summary stage.
        start_equity = Decimal(str(cfg.execution.initial_equity_quote))
        end_price = latest_price[1] if latest_price else Decimal("0")
        end_equity = sim.equity_quote(price=end_price)
        ret_pct = (
            ((end_equity / start_equity) - 1) * Decimal("100")
            if start_equity != 0
            else Decimal("0")
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
        summary_call_id, summary_text = gateway.call_summary(
            session,
            run_id=run_id,
            observed_at=now(),
            model_key=cfg.summary.model_key or cfg.model.key,
            system_prompt=summary_system,
            user_prompt=summary_user,
        )

        mark_run_finished(
            session,
            run=run,
            run_id=run_id,
            source="orchestrator.replay",
            return_pct=ret_pct,
            summary_call_id=summary_call_id,
            summary_text=summary_text,
        )

        if run.kind == "tournament":
            link = (
                session.execute(
                    select(ArenaSubmissionRunRow)
                    .where(ArenaSubmissionRunRow.run_id == run_id)
                    .limit(1)
                )
                .scalars()
                .one_or_none()
            )
            if link is not None:
                link.status = "finished"
                link.return_pct = ret_pct
                link.error = None
                link.started_at = run.started_at
                link.ended_at = run.ended_at
                link.updated_at = now()

                rows = list(
                    session.execute(
                        select(ArenaSubmissionRunRow).where(
                            ArenaSubmissionRunRow.submission_id == link.submission_id
                        )
                    )
                    .scalars()
                    .all()
                )
                finished = [r for r in rows if r.status == "finished" and r.return_pct is not None]
                sub = session.get(ArenaSubmissionRow, link.submission_id)
                if sub is not None:
                    sub.windows_total = int(len(rows))
                    sub.windows_completed = int(len(finished))
                    sub.updated_at = now()

                    if len(finished) == len(rows) and rows:
                        product = Decimal("1")
                        returns = [Decimal(str(r.return_pct)) for r in finished]
                        for r in returns:
                            product *= Decimal("1") + (r / Decimal("100"))
                        total_pct = (product - Decimal("1")) * Decimal("100")
                        avg_pct = sum(returns) / Decimal(len(returns))

                        sub.total_return_pct = total_pct
                        sub.avg_return_pct = avg_pct
                        sub.status = "finished"
                        sub.ended_at = now()
                        sub.error = None
                        sub.updated_at = now()

                session.commit()
    finally:
        sim.close()
