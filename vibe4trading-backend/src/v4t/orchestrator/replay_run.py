from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.arena.reporting import generate_submission_report
from v4t.benchmark.spec import PositionMode
from v4t.contracts.events import make_event
from v4t.contracts.numbers import decimal_to_str
from v4t.contracts.payloads import (
    FundingRatePayload,
    LlmDecisionPayload,
    LlmStreamDeltaPayload,
    LlmStreamEndPayload,
    LlmStreamStartPayload,
    MarketOHLCVPayload,
    MarketPricePayload,
    SentimentItemPayload,
    SentimentItemSummaryPayload,
)
from v4t.contracts.run_config import RunMode
from v4t.db.event_store import append_event
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, DatasetRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.orchestrator.prompt_builder import render_user_prompt
from v4t.orchestrator.run_base import (
    SentimentPromptItem,
    advance_base_tick,
    append_decision_memory,
    append_sim_fill_event,
    build_prompt_context,
    compute_features,
    get_strategy_prompt,
    get_system_prompt,
    load_run_and_config,
    mark_run_cancelled,
    mark_run_failed,
    mark_run_finished,
    mark_run_started,
    select_usable_bars,
    validate_decision,
    write_portfolio_snapshot,
)
from v4t.replay.stream import iter_dataset_events
from v4t.sim.benchmark_sim import BenchmarkPaperSim
from v4t.utils.datetime import as_utc, now

_logger = logging.getLogger(__name__)


def execute_replay_run(
    session: Session, *, run_id: UUID, finalize_submission_report: bool = True
) -> None:
    run, cfg = load_run_and_config(session, run_id=run_id, expected_mode=RunMode.replay)

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
    ohlcv_bars: list[MarketOHLCVPayload] = []
    sentiment_items: list[SentimentPromptItem] = []
    sentiment_summaries: list[SentimentItemSummaryPayload] = []

    # Portfolio state (Nautilus-backed).
    fee_bps = Decimal(str(cfg.execution.fee_bps))
    sim = BenchmarkPaperSim(
        market_id=cfg.market_id,
        initial_equity_quote=Decimal(str(cfg.execution.initial_equity_quote)),
        fee_bps=fee_bps,
    )

    # Decision memory (last 3 payloads for prompt context).
    memory: list[dict[str, Any]] = []
    last_target = Decimal("0")
    last_mode = PositionMode.spot
    last_leverage = 1

    base_interval = timedelta(seconds=cfg.scheduler.base_interval_seconds)
    next_base_tick = window_start

    price_max_age = timedelta(seconds=cfg.scheduler.price_tick_seconds)

    gateway = LlmGateway()

    try:
        i = 0
        while True:
            tick_time = next_base_tick

            if tick_time > window_end:
                break

            # Advance event stream up to tick_time.
            while i < len(events) and as_utc(events[i].observed_at) <= tick_time:
                ev = events[i]
                i += 1
                if ev.event_type == "market.price":
                    p = MarketPricePayload.model_validate(ev.payload)
                    if p.market_id == cfg.market_id:
                        latest_price = (as_utc(ev.observed_at), Decimal(p.price))
                        trigger_fill = sim.process_price_update(
                            tick_time=as_utc(ev.observed_at),
                            price=Decimal(p.price),
                        )
                        if trigger_fill is not None:
                            append_sim_fill_event(
                                session,
                                source="orchestrator.replay",
                                tick_time=as_utc(ev.observed_at),
                                run_id=run_id,
                                market_id=cfg.market_id,
                                fill=trigger_fill,
                            )
                        sim.maybe_apply_default_funding(
                            tick_time=as_utc(ev.observed_at),
                            price=Decimal(p.price),
                            funding_rate=Decimal(str(cfg.execution.funding_rate_per_8h)),
                        )
                elif ev.event_type == "market.ohlcv":
                    b = MarketOHLCVPayload.model_validate(ev.payload)
                    if b.market_id == cfg.market_id:
                        ohlcv_bars.append(b)
                elif ev.event_type == "funding.rate":
                    funding = FundingRatePayload.model_validate(ev.payload)
                    if funding.market_id == cfg.market_id and latest_price is not None:
                        sim.apply_funding_rate(
                            tick_time=funding.funding_time,
                            price=latest_price[1],
                            funding_rate=Decimal(funding.funding_rate),
                        )
                elif ev.event_type == "sentiment.item":
                    sentiment_items.append(
                        SentimentPromptItem(
                            payload=SentimentItemPayload.model_validate(ev.payload),
                            raw_payload=ev.raw_payload,
                        )
                    )
                elif ev.event_type == "sentiment.item_summary":
                    s = SentimentItemSummaryPayload.model_validate(ev.payload)
                    sentiment_summaries.append(s)

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

            # Prompt inputs.
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
                sentiment_items=sentiment_items,
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
                    source="orchestrator.replay",
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
                        source="orchestrator.replay",
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
                    except Exception as exc:
                        _logger.exception(
                            "streaming_commit_failed run_id=%s",
                            str(run_id),
                        )
                        session.rollback()
                        raise RuntimeError(
                            f"failed to persist replay stream delta for run_id={run_id}"
                        ) from exc
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
                ),
                on_delta=_on_delta,
                temperature=cfg.model.temperature,
                max_output_tokens=cfg.model.max_output_tokens,
            )

            append_event(
                session,
                ev=make_event(
                    event_type="llm.stream_end",
                    source="orchestrator.replay",
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
            )

            # Persist decision event.
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
                    source="orchestrator.replay",
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
                source="orchestrator.replay",
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

        summary_call_id = None
        summary_text = None
        if run.kind != "tournament":
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

                    if finalize_submission_report and len(finished) == len(rows) and rows:
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
                if finalize_submission_report and len(finished) == len(rows) and rows:
                    generate_submission_report(session, submission_id=link.submission_id)
    except Exception as exc:
        _logger.exception("replay_run_failed run_id=%s", str(run_id))
        try:
            session.rollback()
            session.refresh(run)
            mark_run_failed(
                session,
                run=run,
                run_id=run_id,
                source="orchestrator.replay",
                error=str(exc),
            )
            if run.kind == "tournament":
                link = (
                    session.execute(
                        select(ArenaSubmissionRunRow).where(ArenaSubmissionRunRow.run_id == run_id)
                    )
                    .scalars()
                    .one_or_none()
                )
                if link is not None:
                    link.status = "failed"
                    link.error = str(exc)
                    link.ended_at = now()
                    link.updated_at = now()
                    session.commit()
        except Exception:
            _logger.exception("replay_run_failed_cleanup_error run_id=%s", str(run_id))
    finally:
        sim.close()
