from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.arena.env_dataset_set import load_arena_env_dataset_set
from v4t.arena.regime_windows import compute_regime_windows
from v4t.arena.reporting import generate_submission_report
from v4t.arena.scenario_sets import (
    ScenarioSet,
    ScenarioWindow,
    get_scenario_set,
)
from v4t.benchmark.spec import HoldingPeriod, get_risk_profile
from v4t.contracts.payloads import RunFinishedPayload
from v4t.contracts.run_config import (
    DatasetRefs,
    ExecutionConfig,
    ModelConfig,
    PromptConfig,
    PromptMasking,
    ReplayConfig,
    RunConfigSnapshot,
    RunKind,
    RunMode,
    RunVisibility,
    SchedulerConfig,
)
from v4t.db.engine import new_session
from v4t.db.models import (
    ArenaSubmissionRow,
    ArenaSubmissionRunRow,
    DatasetRow,
    EventRow,
    LlmModelRow,
    RunConfigSnapshotRow,
    RunRow,
)
from v4t.ingest.dataset_import import import_dataset
from v4t.orchestrator.replay_run import execute_replay_run
from v4t.settings import get_settings
from v4t.utils.datetime import as_utc, now

DEFAULT_PROMPT_TEXT = "Analyze the market data and decide target exposure."
ALL_MARKETS_SENTINEL = "benchmark:all"


@dataclass(frozen=True)
class PendingScenarioRun:
    scenario_index: int
    run_id: UUID


def _compute_fixed_windows(
    *, start: datetime, end: datetime, window_hours: int, n_windows: int
) -> list[ScenarioWindow]:
    start = as_utc(start)
    end = as_utc(end)
    window_len = timedelta(hours=window_hours)
    latest_start = end - window_len
    if latest_start < start:
        raise ValueError("dataset range is too small for benchmark windows")
    total_hours = int((latest_start - start).total_seconds() // 3600)
    out: list[ScenarioWindow] = []
    for idx in range(n_windows):
        frac = 0.0 if n_windows == 1 else idx / (n_windows - 1)
        offset_hours = int(total_hours * frac)
        window_start = start + timedelta(hours=offset_hours)
        window_end = window_start + window_len
        out.append(
            ScenarioWindow(
                index=idx,
                label=f"Window {idx + 1}",
                start=window_start,
                end=window_end,
            )
        )
    return out


def _find_sentiment_dataset(session: Session, *, spot_ds: DatasetRow) -> UUID | None:
    """Find a sentiment dataset matching the same event window as the spot dataset."""
    event_id = (spot_ds.params or {}).get("event_id")
    if not event_id:
        return None

    rows = (
        session.execute(
            select(DatasetRow).where(
                DatasetRow.category == "sentiment",
                DatasetRow.source == "tweets",
                DatasetRow.status == "ready",
            )
        )
        .scalars()
        .all()
    )
    matches = [r for r in rows if (r.params or {}).get("event_id") == event_id]
    if not matches:
        return None

    matches.sort(key=lambda row: (as_utc(row.created_at), str(row.dataset_id)), reverse=True)
    return matches[0].dataset_id


def _assert_model_allowed(session: Session, model_key: str) -> None:
    if model_key == "stub":
        return

    row = (
        session.execute(
            select(LlmModelRow)
            .where(LlmModelRow.model_key == model_key, LlmModelRow.enabled.is_(True))
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if row is None:
        raise ValueError(f"model_key not in predefined list: {model_key}")


def _create_scenario_run(
    session: Session,
    *,
    submission: ArenaSubmissionRow,
    scenario_set: ScenarioSet,
    window: ScenarioWindow,
    market_id: str,
    market_dataset_id: UUID,
    sentiment_dataset_id: UUID | None,
) -> UUID:
    settings = get_settings()
    timestamp = now()

    prompt_text = (submission.prompt_vars or {}).get("prompt_text", DEFAULT_PROMPT_TEXT)
    risk_level = (submission.prompt_vars or {}).get("risk_level")
    holding_period_raw = (submission.prompt_vars or {}).get("holding_period")
    system_prompt_override = (submission.prompt_vars or {}).get("system_prompt")
    risk_profile = get_risk_profile(int(risk_level)) if risk_level is not None else None
    gross_leverage_cap = (
        float(risk_profile.max_abs_exposure)
        if risk_profile is not None
        else settings.execution_gross_leverage_cap
    )
    net_exposure_cap = (
        float(risk_profile.max_abs_exposure)
        if risk_profile is not None
        else settings.execution_net_exposure_cap
    )

    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        run_kind=RunKind.tournament,
        visibility=RunVisibility.public
        if submission.visibility == "public"
        else RunVisibility.private,
        market_id=market_id,
        risk_level=int(risk_level) if risk_level is not None else None,
        holding_period=HoldingPeriod(holding_period_raw) if holding_period_raw else None,
        model=ModelConfig(key=submission.model_key),
        datasets=DatasetRefs(
            market_dataset_id=market_dataset_id,
            sentiment_dataset_id=sentiment_dataset_id,
        ),
        scheduler=SchedulerConfig(
            base_interval_seconds=settings.replay_base_interval_seconds,
            price_tick_seconds=settings.replay_price_tick_seconds,
        ),
        replay=ReplayConfig(
            pace_seconds_per_base_tick=float(scenario_set.pace_seconds_per_base_tick)
        ),
        prompt=PromptConfig(
            prompt_text=prompt_text,
            system_prompt_override=system_prompt_override,
            lookback_bars=settings.replay_prompt_lookback_bars,
            timeframe=settings.replay_prompt_timeframe,
            masking=PromptMasking(time_offset_seconds=settings.replay_prompt_time_offset_seconds),
        ),
        execution=ExecutionConfig(
            fee_bps=settings.execution_fee_bps,
            initial_equity_quote=settings.execution_initial_equity_quote,
            gross_leverage_cap=gross_leverage_cap,
            net_exposure_cap=net_exposure_cap,
        ),
    )

    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=timestamp)
    session.add(cfg_row)
    session.flush()

    run = RunRow(
        kind="tournament",
        visibility=submission.visibility,
        market_id=market_id,
        model_key=submission.model_key,
        config_id=cfg_row.config_id,
        status="pending",
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(run)
    session.flush()

    link = ArenaSubmissionRunRow(
        submission_id=submission.submission_id,
        scenario_index=int(window.index),
        run_id=run.run_id,
        window_start=window.start,
        window_end=window.end,
        status="pending",
        return_pct=None,
        error=None,
        started_at=None,
        ended_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(link)

    session.commit()
    return run.run_id


def _get_run_return_pct(session: Session, *, run_id: UUID) -> Decimal | None:
    row = session.execute(
        select(EventRow)
        .where(EventRow.run_id == run_id, EventRow.event_type == "run.finished")
        .order_by(EventRow.observed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    payload = RunFinishedPayload.model_validate(row.payload)
    return Decimal(payload.return_pct)


def _execute_submission_window(*, run_id: UUID) -> None:
    with new_session() as session:
        execute_replay_run(session, run_id=run_id, finalize_submission_report=False)


def _apply_completed_window_result(
    session: Session,
    *,
    submission: ArenaSubmissionRow,
    scenario_index: int,
    run_id: UUID,
    completed_returns: list[Decimal],
) -> None:
    session.expire_all()
    ret = _get_run_return_pct(session, run_id=run_id)
    if ret is None:
        raise ValueError(f"scenario run missing run.finished: run_id={run_id}")

    link = session.get(ArenaSubmissionRunRow, (submission.submission_id, scenario_index))
    if link is not None:
        run = session.get(RunRow, run_id)
        if link.status != "finished" or link.return_pct is None:
            link.status = "finished"
            link.return_pct = ret
        if link.started_at is None and run is not None:
            link.started_at = run.started_at
        if run is not None:
            link.ended_at = run.ended_at
        link.updated_at = now()

    completed_returns.append(ret)
    submission.windows_completed = int(len(completed_returns))
    submission.updated_at = now()
    session.commit()


def _execute_pending_submission_runs(
    session: Session,
    *,
    submission: ArenaSubmissionRow,
    pending_runs: list[PendingScenarioRun],
    completed_returns: list[Decimal],
    max_parallel_windows: int,
) -> None:
    if not pending_runs:
        return

    if max_parallel_windows <= 1:
        for pending in pending_runs:
            _execute_submission_window(run_id=pending.run_id)
            _apply_completed_window_result(
                session,
                submission=submission,
                scenario_index=pending.scenario_index,
                run_id=pending.run_id,
                completed_returns=completed_returns,
            )
        return

    with ThreadPoolExecutor(
        max_workers=max_parallel_windows, thread_name_prefix="arena-run"
    ) as executor:
        future_map: dict[Future[None], PendingScenarioRun] = {
            executor.submit(_execute_submission_window, run_id=pending.run_id): pending
            for pending in pending_runs
        }
        for future in as_completed(future_map):
            pending = future_map[future]
            future.result()
            _apply_completed_window_result(
                session,
                submission=submission,
                scenario_index=pending.scenario_index,
                run_id=pending.run_id,
                completed_returns=completed_returns,
            )


def execute_arena_submission(session: Session, *, submission_id: UUID) -> None:
    submission = session.get(ArenaSubmissionRow, submission_id)
    if submission is None:
        raise ValueError(f"submission_id not found: {submission_id}")

    scenario_set = get_scenario_set(submission.scenario_set_key) or get_scenario_set("default-v1")
    if scenario_set is None:
        raise ValueError("missing default-v1 scenario set")

    _assert_model_allowed(session, submission.model_key)

    if submission.status == "finished":
        return

    submission.status = "running"
    if submission.started_at is None:
        submission.started_at = now()
    submission.updated_at = now()
    session.commit()

    completed_returns: list[Decimal] = []

    try:
        settings = get_settings()
        env_set = load_arena_env_dataset_set(session)
        if env_set is None:
            raise ValueError("Arena datasets are not configured (set V4T_ARENA_DATASET_IDS)")

        market_ids = (
            env_set.market_ids
            if submission.market_id == ALL_MARKETS_SENTINEL
            else [submission.market_id]
        )
        market_windows: list[tuple[str, list[DatasetRow], list[ScenarioWindow]]] = []
        mode = str(submission.scenario_set_key or "").strip()
        for market_id in market_ids:
            market_datasets = env_set.spot_by_market.get(market_id)
            if not market_datasets:
                raise ValueError(f"Arena datasets missing for market_id={market_id}")
            if mode == "env-regimes-v1":
                if len(market_datasets) != 1:
                    raise ValueError(
                        f"env-regimes-v1 requires exactly 1 spot dataset for market_id={market_id}"
                    )
                spot_ds = market_datasets[0]
                if spot_ds.status != "ready":
                    import_dataset(session, dataset_id=spot_ds.dataset_id)
                    session.refresh(spot_ds)
                windows = compute_regime_windows(
                    session,
                    dataset_id=spot_ds.dataset_id,
                    market_id=market_id,
                    timeframe=settings.replay_prompt_timeframe,
                    window_hours=12,
                    n_windows=10,
                )
            elif mode == "crypto-benchmark-v1" and len(market_datasets) == 1:
                spot_ds = market_datasets[0]
                if spot_ds.status != "ready":
                    import_dataset(session, dataset_id=spot_ds.dataset_id)
                    session.refresh(spot_ds)
                windows = _compute_fixed_windows(
                    start=spot_ds.start,
                    end=spot_ds.end,
                    window_hours=168,
                    n_windows=10,
                )
            elif len(market_datasets) == 10:
                windows = []
                for i, ds in enumerate(market_datasets):
                    scoring_start = (ds.params or {}).get("scoring_start")
                    scoring_end = (ds.params or {}).get("scoring_end")
                    if scoring_start and scoring_end:
                        from datetime import datetime as _dt

                        w_start = as_utc(_dt.fromisoformat(scoring_start.replace("Z", "+00:00")))
                        w_end = as_utc(_dt.fromisoformat(scoring_end.replace("Z", "+00:00")))
                    else:
                        w_start = as_utc(ds.start)
                        w_end = as_utc(ds.end)
                    windows.append(
                        ScenarioWindow(
                            index=i,
                            label=(ds.params or {}).get("event_name", f"Window {i + 1}"),
                            start=w_start,
                            end=w_end,
                        )
                    )
            elif len(market_datasets) == 1:
                ds = market_datasets[0]
                windows = [
                    ScenarioWindow(
                        index=0,
                        label="Full Range",
                        start=as_utc(ds.start),
                        end=as_utc(ds.end),
                    )
                ]
            else:
                raise ValueError(
                    f"Invalid arena dataset count for market_id={market_id}: {len(market_datasets)}"
                )
            market_windows.append((market_id, market_datasets, windows))

        submission.windows_total = int(sum(len(windows) for _, _, windows in market_windows))
        submission.updated_at = now()
        session.commit()

        max_parallel_windows = max(1, int(settings.llm_max_concurrent_requests))
        pending_runs: list[PendingScenarioRun] = []
        scenario_offset = 0
        for market_id, market_datasets, windows in market_windows:
            for w in windows:
                scenario_index = scenario_offset + int(w.index)
                existing = session.get(ArenaSubmissionRunRow, (submission_id, scenario_index))
                if existing is not None:
                    if existing.status == "finished" and existing.return_pct is not None:
                        completed_returns.append(existing.return_pct)
                        continue
                    raise ValueError(
                        f"submission already has an in-progress scenario run: index={scenario_index}"
                    )

                if len(market_datasets) == 1:
                    spot_ds = market_datasets[0]
                else:
                    spot_ds = market_datasets[int(w.index)]
                if spot_ds.status != "ready":
                    import_dataset(session, dataset_id=spot_ds.dataset_id)

                sentiment_ds_id = _find_sentiment_dataset(session, spot_ds=spot_ds)
                scenario_window = ScenarioWindow(
                    index=scenario_index,
                    label=f"{market_id} - {w.label}",
                    start=w.start,
                    end=w.end,
                )

                run_id = _create_scenario_run(
                    session,
                    submission=submission,
                    scenario_set=scenario_set,
                    window=scenario_window,
                    market_id=market_id,
                    market_dataset_id=spot_ds.dataset_id,
                    sentiment_dataset_id=sentiment_ds_id,
                )
                pending_runs.append(
                    PendingScenarioRun(scenario_index=scenario_index, run_id=run_id)
                )
            scenario_offset += len(windows)

        _execute_pending_submission_runs(
            session,
            submission=submission,
            pending_runs=pending_runs,
            completed_returns=completed_returns,
            max_parallel_windows=min(max_parallel_windows, len(pending_runs) or 1),
        )

        if not completed_returns:
            raise ValueError("tournament produced no window results")

        mult = Decimal("1")
        for r in completed_returns:
            mult *= Decimal("1") + (r / Decimal("100"))

        submission.total_return_pct = (mult - Decimal("1")) * Decimal("100")
        submission.avg_return_pct = sum(completed_returns) / Decimal(len(completed_returns))
        submission.status = "finished"
        submission.error = None
        submission.ended_at = now()
        submission.updated_at = now()
        session.commit()
        generate_submission_report(session, submission_id=submission_id)
    except Exception as exc:  # noqa: BLE001
        try:
            session.rollback()
        except Exception:
            pass

        submission2 = session.get(ArenaSubmissionRow, submission_id)
        if submission2 is not None:
            submission2.status = "failed"
            submission2.error = repr(exc)
            submission2.ended_at = now()
            submission2.updated_at = now()
            session.commit()
        raise
