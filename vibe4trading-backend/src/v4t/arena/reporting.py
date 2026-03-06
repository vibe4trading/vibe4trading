from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.arena.metrics import compute_run_metrics
from v4t.contracts.arena_report import (
    ArenaSubmissionReport,
    ArenaSubmissionReportKeyMetrics,
    ArenaSubmissionReportNarrative,
    ArenaSubmissionReportWindow,
    ArenaSubmissionReportWindowHighlight,
)
from v4t.contracts.payloads import (
    LlmDecisionPayload,
    PortfolioSnapshotPayload,
    SimFillPayload,
)
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, EventRow, RunRow
from v4t.llm.gateway import LlmGateway
from v4t.settings import get_settings
from v4t.utils.datetime import now


def compute_sharpe_from_returns(returns_pct: list[float]) -> float | None:
    if len(returns_pct) < 2:
        return 0.0 if returns_pct else None

    returns = [r / 100.0 for r in returns_pct]
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance)
    if std_r == 0:
        return 0.0
    sharpe = (mean_r / std_r) * math.sqrt(len(returns))
    return round(sharpe, 2)


def compute_max_drawdown_from_returns(returns_pct: list[float]) -> float | None:
    if not returns_pct:
        return None

    equity = 100.0
    peak = equity
    max_drawdown = 0.0
    for ret in returns_pct:
        equity *= 1.0 + (ret / 100.0)
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, ((peak - equity) / peak) * 100.0)
    return round(max_drawdown, 2)


def compute_profit_factor_from_returns(returns_pct: list[float]) -> float | None:
    if not returns_pct:
        return None

    gross_profit = sum(r for r in returns_pct if r > 0)
    gross_loss = abs(sum(r for r in returns_pct if r < 0))
    if gross_loss > 0:
        return round(gross_profit / gross_loss, 2)
    if gross_profit > 0:
        return 99.99
    return 0.0


def generate_submission_report(
    session: Session, *, submission_id: UUID
) -> ArenaSubmissionReport | None:
    submission = session.get(ArenaSubmissionRow, submission_id)
    if submission is None:
        raise ValueError(f"submission_id not found: {submission_id}")

    links = list(
        session.execute(
            select(ArenaSubmissionRunRow)
            .where(ArenaSubmissionRunRow.submission_id == submission_id)
            .order_by(ArenaSubmissionRunRow.scenario_index)
        )
        .scalars()
        .all()
    )
    if not links:
        return None

    finished_links = [
        link for link in links if link.status == "finished" and link.return_pct is not None
    ]
    if len(finished_links) != len(links):
        return None

    run_ids = {link.run_id for link in links}
    runs_by_id = {
        row.run_id: row
        for row in session.execute(select(RunRow).where(RunRow.run_id.in_(run_ids))).scalars().all()
    }

    windows: list[ArenaSubmissionReportWindow] = []
    submission_confidences: list[float] = []
    submission_targets: list[float] = []
    total_decisions = 0
    total_accepted = 0
    total_trades = 0
    per_window_returns: list[float] = []

    for link in links:
        run = runs_by_id.get(link.run_id)
        market_id = run.market_id if run is not None else submission.market_id
        window = _build_window_report(
            session,
            submission=submission,
            link=link,
            market_id=market_id,
            submission_confidences=submission_confidences,
            submission_targets=submission_targets,
        )
        total_decisions += window.decision_count
        total_trades += window.num_trades
        if window.acceptance_rate_pct is not None and window.decision_count > 0:
            total_accepted += round((window.acceptance_rate_pct / 100.0) * window.decision_count)
        if window.return_pct is not None:
            per_window_returns.append(window.return_pct)
        windows.append(window)

    key_metrics = ArenaSubmissionReportKeyMetrics(
        total_return_pct=_round_float(_to_float(submission.total_return_pct), 2),
        avg_window_return_pct=_round_float(_to_float(submission.avg_return_pct), 2),
        win_rate_pct=_round_float(
            (sum(1 for value in per_window_returns if value >= 0) / len(per_window_returns)) * 100.0
            if per_window_returns
            else None,
            1,
        ),
        sharpe_ratio=compute_sharpe_from_returns(per_window_returns),
        max_drawdown_pct=compute_max_drawdown_from_returns(per_window_returns),
        profit_factor=compute_profit_factor_from_returns(per_window_returns),
        num_trades=total_trades,
        decision_count=total_decisions,
        acceptance_rate_pct=_round_float(
            (total_accepted / total_decisions) * 100.0 if total_decisions > 0 else None,
            1,
        ),
        avg_confidence=_round_float(
            sum(submission_confidences) / len(submission_confidences)
            if submission_confidences
            else None,
            3,
        ),
        avg_target_exposure_pct=_round_float(
            sum(submission_targets) / len(submission_targets) if submission_targets else None,
            1,
        ),
        window_return_dispersion_pct=_round_float(
            statistics.pstdev(per_window_returns) if len(per_window_returns) > 1 else 0.0,
            2,
        ),
    )

    best_window = max(
        (window for window in windows if window.return_pct is not None),
        key=lambda window: window.return_pct if window.return_pct is not None else float("-inf"),
        default=None,
    )
    worst_window = min(
        (window for window in windows if window.return_pct is not None),
        key=lambda window: window.return_pct if window.return_pct is not None else float("inf"),
        default=None,
    )

    style_context = _build_submission_style_context(
        session,
        submission=submission,
        links=links,
        run_ids=run_ids,
        key_metrics=key_metrics,
    )
    style_metrics = style_context["style_metrics"]

    deterministic_score = _compute_submission_score(key_metrics, style_metrics=style_metrics)
    fallback = _build_fallback_report(
        score=deterministic_score,
        key_metrics=key_metrics,
        windows=windows,
        best_window=best_window,
        worst_window=worst_window,
        style_metrics=style_metrics,
    )
    report = _generate_llm_report(
        session,
        submission=submission,
        key_metrics=key_metrics,
        windows=windows,
        best_window=best_window,
        worst_window=worst_window,
        style_context=style_context,
        fallback=fallback,
    )

    submission.report_json = report.model_dump(mode="json")
    submission.updated_at = now()
    session.commit()
    return report


def _build_window_report(
    session: Session,
    *,
    submission: ArenaSubmissionRow,
    link: ArenaSubmissionRunRow,
    market_id: str,
    submission_confidences: list[float],
    submission_targets: list[float],
) -> ArenaSubmissionReportWindow:
    decision_rows = list(
        session.execute(
            select(EventRow)
            .where(EventRow.run_id == link.run_id, EventRow.event_type == "llm.decision")
            .order_by(EventRow.observed_at)
        )
        .scalars()
        .all()
    )
    decisions: list[LlmDecisionPayload] = []
    for row in decision_rows:
        decisions.append(LlmDecisionPayload.model_validate(_event_payload_dict(row)))
    decision_count = len(decisions)
    accepted_count = sum(1 for decision in decisions if decision.accepted)

    confidences = [
        float(Decimal(decision.confidence))
        for decision in decisions
        if decision.confidence is not None
    ]
    submission_confidences.extend(confidences)

    exposures = [_decision_exposure_pct(decision, market_id=market_id) for decision in decisions]
    exposures = [value for value in exposures if value is not None]
    submission_targets.extend(exposures)

    sharpe_ratio: float | None = None
    max_drawdown_pct: float | None = None
    win_rate_pct: float | None = None
    profit_factor: float | None = None
    num_trades = 0
    if link.status == "finished":
        run_metrics = compute_run_metrics(session, run_id=link.run_id)
        sharpe_ratio = _round_float(_to_float(run_metrics.sharpe_ratio), 4)
        max_drawdown_pct = _round_float(_to_float(run_metrics.max_drawdown_pct), 2)
        win_rate_pct = _round_float(_to_float(run_metrics.win_rate_pct), 2)
        profit_factor = _round_float(_to_float(run_metrics.profit_factor), 2)
        num_trades = int(run_metrics.num_trades)

    return ArenaSubmissionReportWindow(
        scenario_index=link.scenario_index,
        window_code=_window_code(link.scenario_index),
        label=_window_label(submission=submission, scenario_index=link.scenario_index),
        market_id=market_id,
        status=link.status,
        return_pct=_round_float(_to_float(link.return_pct), 2),
        sharpe_ratio=sharpe_ratio,
        max_drawdown_pct=max_drawdown_pct,
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
        num_trades=num_trades,
        decision_count=decision_count,
        acceptance_rate_pct=_round_float(
            (accepted_count / decision_count) * 100.0 if decision_count > 0 else None,
            1,
        ),
        avg_confidence=_round_float(
            sum(confidences) / len(confidences) if confidences else None,
            3,
        ),
        avg_target_exposure_pct=_round_float(
            sum(exposures) / len(exposures) if exposures else None,
            1,
        ),
    )


def _decision_exposure_pct(decision: LlmDecisionPayload, *, market_id: str) -> float | None:
    if decision.target is not None:
        return abs(float(Decimal(decision.target))) * 100.0

    target = decision.targets.get(market_id)
    if target is None and decision.targets:
        first_key = next(iter(decision.targets))
        target = decision.targets.get(first_key)
    if target is None:
        return None
    return abs(float(Decimal(target))) * 100.0


_TRADE_STYLE_JUDGE_PROMPT = (
    'You are a "Freqtrade Trading Style Judge." '
    "You may only use raw fields from the input JSON. Do not infer or fabricate data.\n\n"
    "## Input Structure\n"
    '{"summary":{"Total profit %":number,"Sharpe":number,"Profit factor":number,'
    '"Max % of account underwater":number},'
    '"trades":[{"pair":string,"open_date_utc":string,"close_date_utc":string,'
    '"leverage":number,"is_short":boolean,"exit_reason":string,'
    '"profit_ratio":number,"profit_abs":number}]}\n\n'
    "If any field is missing, treat missing numeric fields as 0 and missing booleans as false. "
    "Still produce a best-effort classification.\n\n"
    "## Derived Metrics (from trades array)\n"
    "total_trades = number of trades; "
    "backtest_days = (max(close_date_utc) - min(open_date_utc)) / 86400, minimum 1; "
    "trades_per_day = total_trades / backtest_days; "
    "median_hold_hours = median of (close_date - open_date) in hours; "
    "short_ratio_pct = percentage of trades where is_short = true; "
    "avg_leverage = mean of leverage across all trades; "
    "top1_position_pct = percentage of trades in the most frequently traded pair; "
    "stoploss_exit_ratio_pct = percentage of trades where exit_reason contains 'stop'; "
    "win_rate_pct = percentage of trades where profit_ratio > 0; "
    "pnl_dispersion = standard deviation of profit_ratio.\n\n"
    "## Scoring\n"
    "norm(x, a, b) = clamp((x - a) / (b - a), 0, 1) * 100\n"
    "P = 0.40 * norm(Total profit %, -20, 120) + 0.25 * norm(Sharpe, -0.5, 2.5) "
    "+ 0.20 * norm(Profit factor, 0.8, 2.0) + 0.15 * norm(win_rate_pct, 25, 70)\n"
    "R = 0.50 * (100 - norm(Max % of account underwater, 5, 60)) "
    "+ 0.30 * (100 - norm(avg_leverage, 1, 20)) "
    "+ 0.20 * (100 - norm(pnl_dispersion, 0.01, 0.15))\n"
    "score = round(0.60 * P + 0.40 * R)\n\n"
    "## Style Matching (9 archetypes)\n"
    "Each style has 4 conditions. Each condition met = +25 points (max 100). "
    "Assign the style with the highest match score.\n\n"
    "Meme Hunter: trades_per_day>=5, median_hold_hours<=24, avg_leverage>=3, top1_position_pct>=25\n"
    "Diamond Hands: trades_per_day<=0.8, median_hold_hours>=168, avg_leverage<=2, short_ratio_pct<=15\n"
    "Macro Speculator: trades_per_day in [1,5], median_hold_hours in [24,240], "
    "short_ratio_pct in [20,70], avg_leverage in [2,8]\n"
    "FOMO Warrior: trades_per_day>=8, median_hold_hours<=12, stoploss_exit_ratio_pct>=25, Profit factor<1.0\n"
    "The Contrarian: trades_per_day in [1,5], median_hold_hours in [24,336], "
    "short_ratio_pct in [10,50], Profit factor>=1.1\n"
    "Contract King: avg_leverage in [3,10], short_ratio_pct in [20,60], "
    "trades_per_day in [1,6], Sharpe>=1.0\n"
    "On-chain Detective: avg_leverage<=2, Max % of account underwater<=15, "
    "trades_per_day<=2, Profit factor>=1.1\n"
    "SuperCycle Believer: short_ratio_pct<=10, median_hold_hours>=120, "
    "avg_leverage>=5, stoploss_exit_ratio_pct<=10\n"
    "Degen Whale: avg_leverage>=12, top1_position_pct>=45, "
    "Max % of account underwater>=40, pnl_dispersion>=0.08\n\n"
    "Tiebreak: pick the style whose leverage center is closest to avg_leverage. "
    "Centers: Meme Hunter=4, Diamond Hands=1, Macro Speculator=5, FOMO Warrior=3, "
    "The Contrarian=3, Contract King=6, On-chain Detective=1.5, SuperCycle Believer=8, Degen Whale=15.\n\n"
    "## Output\n"
    "Return ONLY a valid JSON object: "
    '{"Score":<integer 0-100>,"Style":"<exact archetype name>","Description":"<15 words or fewer>"}.'
)


def _generate_llm_report(
    session: Session,
    *,
    submission: ArenaSubmissionRow,
    key_metrics: ArenaSubmissionReportKeyMetrics,
    windows: list[ArenaSubmissionReportWindow],
    best_window: ArenaSubmissionReportWindow | None,
    worst_window: ArenaSubmissionReportWindow | None,
    style_context: dict[str, Any],
    fallback: ArenaSubmissionReport,
) -> ArenaSubmissionReport:
    gateway = LlmGateway()
    report_input: dict[str, Any] = {
        "summary": {
            "Total profit %": key_metrics.total_return_pct or 0.0,
            "Sharpe": key_metrics.sharpe_ratio or 0.0,
            "Profit factor": key_metrics.profit_factor or 0.0,
            "Max % of account underwater": key_metrics.max_drawdown_pct or 0.0,
        },
        "trades": style_context["trade_samples"],
    }

    system_prompt = _TRADE_STYLE_JUDGE_PROMPT
    user_prompt = json.dumps(report_input, ensure_ascii=True, indent=2)

    settings = get_settings()
    report_model_key = settings.llm_report_model or submission.model_key

    fallback_payload = fallback.model_dump(mode="json")
    call_id, response_json, used_fallback = gateway.call_submission_report(
        session,
        submission_id=submission.submission_id,
        observed_at=now(),
        model_key=report_model_key,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback_report=fallback_payload,
    )

    if used_fallback:
        fallback.generation_mode = "fallback"
        submission.report_call_id = call_id
        return fallback

    try:
        narrative = ArenaSubmissionReportNarrative.model_validate(response_json)
    except Exception:
        submission.report_call_id = call_id
        return fallback

    archetype = narrative.Style
    if archetype not in ARCHETYPE_REPRESENTATIVES:
        archetype = fallback.archetype

    submission.report_call_id = call_id
    return ArenaSubmissionReport(
        schema_version=1,
        generation_mode="llm",
        overall_score=max(0, min(100, narrative.Score)),
        archetype=archetype,
        representative=ARCHETYPE_REPRESENTATIVES.get(archetype),
        overview=narrative.Description,
        strengths=fallback.strengths,
        weaknesses=fallback.weaknesses,
        recommendations=fallback.recommendations,
        key_metrics=key_metrics,
        best_window=fallback.best_window,
        worst_window=fallback.worst_window,
        windows=windows,
    )


def _build_submission_style_context(
    session: Session,
    *,
    submission: ArenaSubmissionRow,
    links: list[ArenaSubmissionRunRow],
    run_ids: set[UUID],
    key_metrics: ArenaSubmissionReportKeyMetrics,
) -> dict[str, Any]:
    decisions = _load_submission_decisions(session, run_ids=run_ids)
    fills_by_run = _load_submission_fills(session, run_ids=run_ids)
    snapshots_by_run = _load_submission_snapshots(session, run_ids=run_ids)
    run_to_link = {link.run_id: link for link in links}

    decision_targets = [
        target_pct
        for decision in decisions
        if (target_pct := _decision_signed_target_pct(decision)) is not None
    ]
    leverage_values = [
        float(fill.leverage)
        for fills in fills_by_run.values()
        for fill in fills
        if fill.leverage is not None
    ]
    fill_count = sum(len(fills) for fills in fills_by_run.values())
    closing_reasons = [
        (fill.reason or "").lower()
        for fills in fills_by_run.values()
        for fill in fills
        if fill.reason
    ]

    total_window_days = max(_compute_submission_window_days(links), 1.0)
    trade_samples, trade_sample_truncated_count = _sample_trade_entries(
        fills_by_run=fills_by_run,
        run_to_link=run_to_link,
        max_items=120,
    )

    style_metrics = {
        "source": "summary_prompt.md-single-coin-adaptation",
        "window_days": round(total_window_days, 2),
        "trade_count": key_metrics.num_trades,
        "fills_count": fill_count,
        "trades_per_day": round(key_metrics.num_trades / total_window_days, 3),
        "median_hold_hours": _compute_median_hold_hours(snapshots_by_run=snapshots_by_run),
        "decision_count": key_metrics.decision_count,
        "long_decision_ratio_pct": _ratio_pct(
            sum(1 for value in decision_targets if value > 0), len(decision_targets)
        ),
        "short_decision_ratio_pct": _ratio_pct(
            sum(1 for value in decision_targets if value < 0), len(decision_targets)
        ),
        "flat_decision_ratio_pct": _ratio_pct(
            sum(1 for value in decision_targets if value == 0), len(decision_targets)
        ),
        "avg_signed_target_exposure_pct": _round_float(
            sum(decision_targets) / len(decision_targets) if decision_targets else None,
            2,
        ),
        "target_exposure_dispersion_pct": _round_float(
            statistics.pstdev(decision_targets) if len(decision_targets) > 1 else 0.0,
            2,
        ),
        "futures_fill_ratio_pct": _ratio_pct(
            sum(
                1
                for fills in fills_by_run.values()
                for fill in fills
                if fill.position_mode == "futures"
            ),
            fill_count,
        ),
        "avg_leverage": _round_float(
            sum(leverage_values) / len(leverage_values) if leverage_values else None,
            2,
        ),
        "stoploss_exit_ratio_pct": _ratio_pct(
            sum(1 for reason in closing_reasons if "stop" in reason), len(closing_reasons)
        ),
        "takeprofit_exit_ratio_pct": _ratio_pct(
            sum(1 for reason in closing_reasons if "take_profit" in reason), len(closing_reasons)
        ),
        "liquidation_exit_ratio_pct": _ratio_pct(
            sum(1 for reason in closing_reasons if "liquidation" in reason), len(closing_reasons)
        ),
        "flip_exit_ratio_pct": _ratio_pct(
            sum(1 for reason in closing_reasons if "flip" in reason), len(closing_reasons)
        ),
        "removed_multi_pair_metrics": ["btc_exposure_pct", "top1_position_pct"],
    }

    return {
        "style_metrics": style_metrics,
        "trade_samples": trade_samples,
        "trade_sample_truncated_count": trade_sample_truncated_count,
    }


def _load_submission_decisions(session: Session, *, run_ids: set[UUID]) -> list[LlmDecisionPayload]:
    rows = list(
        session.execute(
            select(EventRow)
            .where(EventRow.run_id.in_(run_ids), EventRow.event_type == "llm.decision")
            .order_by(EventRow.run_id, EventRow.observed_at)
        )
        .scalars()
        .all()
    )
    return [LlmDecisionPayload.model_validate(_event_payload_dict(row)) for row in rows]


def _load_submission_fills(
    session: Session, *, run_ids: set[UUID]
) -> dict[UUID, list[SimFillPayload]]:
    rows = list(
        session.execute(
            select(EventRow)
            .where(EventRow.run_id.in_(run_ids), EventRow.event_type == "sim.fill")
            .order_by(EventRow.run_id, EventRow.observed_at)
        )
        .scalars()
        .all()
    )
    out: dict[UUID, list[SimFillPayload]] = defaultdict(list)
    for row in rows:
        if row.run_id is None:
            continue
        out[row.run_id].append(SimFillPayload.model_validate(_event_payload_dict(row)))
    return dict(out)


def _load_submission_snapshots(
    session: Session, *, run_ids: set[UUID]
) -> dict[UUID, list[PortfolioSnapshotPayload]]:
    rows = list(
        session.execute(
            select(EventRow)
            .where(EventRow.run_id.in_(run_ids), EventRow.event_type == "portfolio.snapshot")
            .order_by(EventRow.run_id, EventRow.observed_at)
        )
        .scalars()
        .all()
    )
    out: dict[UUID, list[PortfolioSnapshotPayload]] = defaultdict(list)
    for row in rows:
        if row.run_id is None:
            continue
        out[row.run_id].append(PortfolioSnapshotPayload.model_validate(_event_payload_dict(row)))
    return dict(out)


def _compute_submission_window_days(links: list[ArenaSubmissionRunRow]) -> float:
    total_seconds = 0.0
    for link in links:
        seconds = (link.window_end - link.window_start).total_seconds()
        if seconds > 0:
            total_seconds += seconds
    return total_seconds / 86400.0


def _compute_median_hold_hours(
    *, snapshots_by_run: dict[UUID, list[PortfolioSnapshotPayload]]
) -> float | None:
    hold_hours: list[float] = []
    for snapshots in snapshots_by_run.values():
        active_start = None
        prev_direction = "flat"
        prev_time = None
        for snapshot in snapshots:
            direction = snapshot.position_direction or "flat"
            current_time = snapshot.snapshot_time
            if direction == "flat":
                if active_start is not None:
                    hold_hours.append(
                        max(0.0, (current_time - active_start).total_seconds() / 3600.0)
                    )
                    active_start = None
            else:
                if active_start is None:
                    active_start = current_time
                elif prev_direction != "flat" and prev_direction != direction:
                    hold_hours.append(
                        max(0.0, (current_time - active_start).total_seconds() / 3600.0)
                    )
                    active_start = current_time
            prev_direction = direction
            prev_time = current_time
        if active_start is not None and prev_time is not None:
            hold_hours.append(max(0.0, (prev_time - active_start).total_seconds() / 3600.0))
    if not hold_hours:
        return None
    return round(float(statistics.median(hold_hours)), 2)


def _sample_trade_entries(
    *,
    fills_by_run: dict[UUID, list[SimFillPayload]],
    run_to_link: dict[UUID, ArenaSubmissionRunRow],
    max_items: int,
) -> tuple[list[dict[str, Any]], int]:
    entries: list[dict[str, Any]] = []
    for run_id, fills in fills_by_run.items():
        link = run_to_link.get(run_id)
        for fill in fills:
            entries.append(
                {
                    "window_code": _window_code(link.scenario_index) if link is not None else None,
                    "tick_time": fill.tick_time.isoformat(),
                    "side": fill.side,
                    "qty_base": str(fill.qty_base),
                    "price": str(fill.price),
                    "notional_quote": str(fill.notional_quote),
                    "reason": fill.reason,
                    "position_mode": fill.position_mode,
                    "leverage": fill.leverage,
                }
            )
    entries.sort(
        key=lambda item: (str(item.get("window_code") or ""), str(item.get("tick_time") or ""))
    )
    if len(entries) <= max_items:
        return entries, 0
    head = max_items // 2
    tail = max_items - head
    sampled = entries[:head] + entries[-tail:]
    return sampled, len(entries) - len(sampled)


def _decision_signed_target_pct(decision: LlmDecisionPayload) -> float | None:
    if decision.target is not None:
        return float(Decimal(decision.target)) * 100.0
    target = decision.targets.get(decision.market_id)
    if target is None and decision.targets:
        first_key = next(iter(decision.targets))
        target = decision.targets.get(first_key)
    if target is None:
        return None
    return float(Decimal(target)) * 100.0


def _ratio_pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 2)


def _event_payload_dict(row: EventRow) -> dict[str, Any]:
    payload_raw: Any = row.__dict__.get("payload")
    payload_json = json.dumps(payload_raw)
    payload: Any = json.loads(payload_json)
    if isinstance(payload, dict):
        return cast(dict[str, Any], payload)
    return {}


def _build_fallback_report(
    *,
    score: int,
    key_metrics: ArenaSubmissionReportKeyMetrics,
    windows: list[ArenaSubmissionReportWindow],
    best_window: ArenaSubmissionReportWindow | None,
    worst_window: ArenaSubmissionReportWindow | None,
    style_metrics: dict[str, Any] | None = None,
) -> ArenaSubmissionReport:
    archetype = _fallback_archetype(key_metrics, style_metrics=style_metrics)
    strengths = _fallback_strengths(key_metrics=key_metrics, best_window=best_window)
    weaknesses = _fallback_weaknesses(key_metrics=key_metrics, worst_window=worst_window)
    recommendations = _fallback_recommendations(key_metrics=key_metrics, worst_window=worst_window)
    overview = _fallback_overview(
        archetype=archetype,
        key_metrics=key_metrics,
        best_window=best_window,
        worst_window=worst_window,
    )
    return ArenaSubmissionReport(
        schema_version=1,
        generation_mode="fallback",
        overall_score=score,
        archetype=archetype,
        representative=ARCHETYPE_REPRESENTATIVES.get(archetype),
        overview=overview,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        key_metrics=key_metrics,
        best_window=ArenaSubmissionReportWindowHighlight(
            window_code=best_window.window_code,
            label=best_window.label,
            return_pct=best_window.return_pct,
            reason=(
                f"Best-performing slice with {best_window.return_pct:.2f}% return and {best_window.num_trades} trades."
                if best_window.return_pct is not None
                else None
            ),
        )
        if best_window is not None
        else None,
        worst_window=ArenaSubmissionReportWindowHighlight(
            window_code=worst_window.window_code,
            label=worst_window.label,
            return_pct=worst_window.return_pct,
            reason=(
                f"Weakest slice with {worst_window.return_pct:.2f}% return and drawdown pressure."
                if worst_window.return_pct is not None
                else None
            ),
        )
        if worst_window is not None
        else None,
        windows=windows,
    )


ARCHETYPE_REPRESENTATIVES: dict[str, str] = {
    "Meme Hunter": "Ansem",
    "Diamond Hands": "Michael Saylor",
    "Macro Speculator": "Arthur Hayes",
    "FOMO Warrior": "Typical Retail",
    "The Contrarian": "DonAlt",
    "Contract King": "PickleCat (0xPickleCat)",
    "On-chain Detective": "ZachXBT",
    "SuperCycle Believer": "Su Zhu (3AC)",
    "Degen Whale": "James Wynn",
}

ARCHETYPE_DESCRIPTIONS: dict[str, str] = {
    "Meme Hunter": "High-frequency short-term narrative chaser. Aggressive position sizing.",
    "Diamond Hands": "Low-frequency long holder. Disciplined and steady.",
    "Macro Speculator": "Bidirectional swing trader driven by macro rhythms.",
    "FOMO Warrior": "Emotional buy-high sell-low pattern. Overtrades consistently.",
    "The Contrarian": "Counter-consensus bottom fisher. Swing-oriented and patient.",
    "Contract King": "Futures-dominant medium-frequency trader. High leverage, high conviction.",
    "On-chain Detective": "Low leverage, risk-first approach. Defense over offense.",
    "SuperCycle Believer": "Perma-long with high leverage. Weak downside protection.",
    "Degen Whale": "Extreme leverage, concentrated bets. Massive volatility.",
}

ARCHETYPE_LEVERAGE_CENTERS: dict[str, float] = {
    "Meme Hunter": 4.0,
    "Diamond Hands": 1.0,
    "Macro Speculator": 5.0,
    "FOMO Warrior": 3.0,
    "The Contrarian": 3.0,
    "Contract King": 6.0,
    "On-chain Detective": 1.5,
    "SuperCycle Believer": 8.0,
    "Degen Whale": 15.0,
}


def _in_range(value: float, low: float, high: float) -> bool:
    return low <= value <= high


def _archetype_match_score(
    *,
    trades_per_day: float,
    median_hold_hours: float,
    avg_leverage: float,
    short_ratio_pct: float,
    stoploss_exit_ratio_pct: float,
    profit_factor: float,
    sharpe: float,
    max_drawdown_pct: float,
    pnl_dispersion: float,
) -> dict[str, int]:
    scores: dict[str, int] = {}

    scores["Meme Hunter"] = (
        (25 if trades_per_day >= 5 else 0)
        + (25 if median_hold_hours <= 24 else 0)
        + (25 if avg_leverage >= 3 else 0)
        + 25  # top1_position_pct >= 25 always true (single-market)
    )

    scores["Diamond Hands"] = (
        (25 if trades_per_day <= 0.8 else 0)
        + (25 if median_hold_hours >= 168 else 0)
        + (25 if avg_leverage <= 2 else 0)
        + (25 if short_ratio_pct <= 15 else 0)
    )

    scores["Macro Speculator"] = (
        (25 if _in_range(trades_per_day, 1, 5) else 0)
        + (25 if _in_range(median_hold_hours, 24, 240) else 0)
        + (25 if _in_range(short_ratio_pct, 20, 70) else 0)
        + (25 if _in_range(avg_leverage, 2, 8) else 0)
    )

    scores["FOMO Warrior"] = (
        (25 if trades_per_day >= 8 else 0)
        + (25 if median_hold_hours <= 12 else 0)
        + (25 if stoploss_exit_ratio_pct >= 25 else 0)
        + (25 if profit_factor < 1.0 else 0)
    )

    scores["The Contrarian"] = (
        (25 if _in_range(trades_per_day, 1, 5) else 0)
        + (25 if _in_range(median_hold_hours, 24, 336) else 0)
        + (25 if _in_range(short_ratio_pct, 10, 50) else 0)
        + (25 if profit_factor >= 1.1 else 0)
    )

    scores["Contract King"] = (
        (25 if _in_range(avg_leverage, 3, 10) else 0)
        + (25 if _in_range(short_ratio_pct, 20, 60) else 0)
        + (25 if _in_range(trades_per_day, 1, 6) else 0)
        + (25 if sharpe >= 1.0 else 0)
    )

    scores["On-chain Detective"] = (
        (25 if avg_leverage <= 2 else 0)
        + (25 if max_drawdown_pct <= 15 else 0)
        + (25 if trades_per_day <= 2 else 0)
        + (25 if profit_factor >= 1.1 else 0)
    )

    scores["SuperCycle Believer"] = (
        (25 if short_ratio_pct <= 10 else 0)
        + (25 if median_hold_hours >= 120 else 0)
        + (25 if avg_leverage >= 5 else 0)
        + (25 if stoploss_exit_ratio_pct <= 10 else 0)
    )

    scores["Degen Whale"] = (
        (25 if avg_leverage >= 12 else 0)
        + 25  # top1_position_pct >= 45 always true (single-market)
        + (25 if max_drawdown_pct >= 40 else 0)
        + (25 if pnl_dispersion >= 0.08 else 0)
    )

    return scores


def _fallback_archetype(
    key_metrics: ArenaSubmissionReportKeyMetrics,
    *,
    style_metrics: dict[str, Any] | None = None,
) -> str:
    sm = style_metrics or {}
    trades_per_day = float(sm.get("trades_per_day", 0))
    median_hold_hours = float(sm.get("median_hold_hours") or 48)
    avg_leverage = float(sm.get("avg_leverage") or 1.0)
    short_ratio_pct = float(sm.get("short_decision_ratio_pct") or 0.0)
    stoploss_exit_ratio_pct = float(sm.get("stoploss_exit_ratio_pct") or 0.0)
    profit_factor = key_metrics.profit_factor or 1.0
    sharpe = key_metrics.sharpe_ratio or 0.0
    max_drawdown_pct = key_metrics.max_drawdown_pct or 0.0
    pnl_dispersion = (key_metrics.window_return_dispersion_pct or 0.0) / 100.0

    scores = _archetype_match_score(
        trades_per_day=trades_per_day,
        median_hold_hours=median_hold_hours,
        avg_leverage=avg_leverage,
        short_ratio_pct=short_ratio_pct,
        stoploss_exit_ratio_pct=stoploss_exit_ratio_pct,
        profit_factor=profit_factor,
        sharpe=sharpe,
        max_drawdown_pct=max_drawdown_pct,
        pnl_dispersion=pnl_dispersion,
    )

    max_score = max(scores.values())
    candidates = [name for name, s in scores.items() if s == max_score]
    if len(candidates) == 1:
        return candidates[0]
    return min(
        candidates,
        key=lambda name: abs(ARCHETYPE_LEVERAGE_CENTERS.get(name, 5.0) - avg_leverage),
    )


def _fallback_overview(
    *,
    archetype: str,
    key_metrics: ArenaSubmissionReportKeyMetrics,
    best_window: ArenaSubmissionReportWindow | None,
    worst_window: ArenaSubmissionReportWindow | None,
) -> str:
    desc = ARCHETYPE_DESCRIPTIONS.get(archetype, archetype)
    total_return = _fmt_pct(key_metrics.total_return_pct)
    best_code = best_window.window_code if best_window is not None else "n/a"
    worst_code = worst_window.window_code if worst_window is not None else "n/a"
    return (
        f"{desc} {total_return} compounded return. "
        f"Best slice {best_code}; weakest slice {worst_code}."
    )


def _fallback_strengths(
    *,
    key_metrics: ArenaSubmissionReportKeyMetrics,
    best_window: ArenaSubmissionReportWindow | None,
) -> list[str]:
    out: list[str] = []
    if (key_metrics.total_return_pct or 0) >= 0:
        out.append(f"Finished positive overall at {_fmt_pct(key_metrics.total_return_pct)}.")
    if (key_metrics.profit_factor or 0) >= 1.1:
        out.append(f"Profit factor held at {key_metrics.profit_factor:.2f}.")
    if (key_metrics.max_drawdown_pct or 100) <= 12:
        out.append(
            f"Drawdown stayed contained at {_fmt_pct(-(key_metrics.max_drawdown_pct or 0))}."
        )
    if best_window is not None and best_window.return_pct is not None:
        out.append(f"{best_window.window_code} led with {_fmt_pct(best_window.return_pct)}.")
    return (out + ["Window-level coverage completed across the full submission."])[:3]


def _fallback_weaknesses(
    *,
    key_metrics: ArenaSubmissionReportKeyMetrics,
    worst_window: ArenaSubmissionReportWindow | None,
) -> list[str]:
    out: list[str] = []
    if (key_metrics.max_drawdown_pct or 0) >= 15:
        out.append(f"Drawdown reached {_fmt_pct(-(key_metrics.max_drawdown_pct or 0))}.")
    if (key_metrics.profit_factor or 1.0) < 1.0:
        out.append("Loss-making windows outweighed winners.")
    if (key_metrics.window_return_dispersion_pct or 0) >= 8:
        out.append("Window-to-window performance was inconsistent.")
    if worst_window is not None and worst_window.return_pct is not None:
        out.append(
            f"{worst_window.window_code} dragged results with {_fmt_pct(worst_window.return_pct)}."
        )
    return (
        out
        + ["Narrative quality falls back to deterministic rules when no LLM review is available."]
    )[:3]


def _fallback_recommendations(
    *,
    key_metrics: ArenaSubmissionReportKeyMetrics,
    worst_window: ArenaSubmissionReportWindow | None,
) -> list[str]:
    out: list[str] = []
    if (key_metrics.max_drawdown_pct or 0) >= 12:
        out.append("Reduce downside exposure in the weakest windows.")
    if (key_metrics.acceptance_rate_pct or 100) < 60:
        out.append("Review rejection causes to tighten decision quality.")
    if (key_metrics.avg_target_exposure_pct or 0) >= 80:
        out.append("Trim average target exposure to improve resilience.")
    if worst_window is not None:
        out.append(
            f"Inspect {worst_window.window_code} replay details before adjusting the prompt."
        )
    return (out + ["Compare best and worst windows before changing strategy wording."])[:3]


def _compute_submission_score(
    key_metrics: ArenaSubmissionReportKeyMetrics,
    *,
    style_metrics: dict[str, Any] | None = None,
) -> int:
    avg_leverage = float((style_metrics or {}).get("avg_leverage") or 1.0)
    pnl_dispersion = (key_metrics.window_return_dispersion_pct or 0.0) / 100.0

    performance = (
        0.40 * _norm(key_metrics.total_return_pct, -20.0, 120.0)
        + 0.25 * _norm(key_metrics.sharpe_ratio, -0.5, 2.5)
        + 0.20 * _norm(key_metrics.profit_factor, 0.8, 2.0)
        + 0.15 * _norm(key_metrics.win_rate_pct, 25.0, 70.0)
    )
    risk = (
        0.50 * (100.0 - _norm(key_metrics.max_drawdown_pct, 5.0, 60.0))
        + 0.30 * (100.0 - _norm(avg_leverage, 1.0, 20.0))
        + 0.20 * (100.0 - _norm(pnl_dispersion, 0.01, 0.15))
    )
    score = round((0.60 * performance) + (0.40 * risk))
    return max(0, min(100, score))


def _norm(value: float | None, low: float, high: float) -> float:
    if value is None:
        return 50.0
    if high <= low:
        return 50.0
    clamped = max(low, min(high, value))
    return ((clamped - low) / (high - low)) * 100.0


def _window_code(index: int) -> str:
    return f"W{index + 1:02d}"


def _window_label(*, submission: ArenaSubmissionRow, scenario_index: int) -> str:
    if submission.scenario_set_key == "env-fullrange-v1" and submission.windows_total == 1:
        return "Full Range"
    if submission.scenario_set_key == "env-regimes-v1":
        return f"Regime {scenario_index + 1}"
    return f"Window {scenario_index + 1}"


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _round_float(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None else None


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"
