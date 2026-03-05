from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.arena.env_dataset_set import load_arena_env_dataset_set
from v4t.arena.regime_windows import compute_regime_windows
from v4t.arena.scenario_sets import (
    ScenarioSet,
    ScenarioWindow,
    get_scenario_set,
)
from v4t.contracts.payloads import RunFinishedPayloadV1
from v4t.contracts.run_config import (
    DatasetRefsV1,
    ExecutionConfigV1,
    ModelConfigV1,
    PromptConfigV1,
    PromptMaskingV1,
    ReplayConfigV1,
    RunConfigSnapshotV1,
    RunKind,
    RunMode,
    RunVisibility,
    SchedulerConfigV1,
)
from v4t.db.models import (
    ArenaSubmissionRow,
    ArenaSubmissionRunRow,
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
    market_dataset_id: UUID,
    sentiment_dataset_id: UUID | None,
) -> UUID:
    settings = get_settings()
    timestamp = now()

    prompt_text = (submission.prompt_vars or {}).get("prompt_text", DEFAULT_PROMPT_TEXT)

    cfg = RunConfigSnapshotV1(
        mode=RunMode.replay,
        run_kind=RunKind.tournament,
        visibility=RunVisibility.public
        if submission.visibility == "public"
        else RunVisibility.private,
        market_id=submission.market_id,
        model=ModelConfigV1(key=submission.model_key),
        datasets=DatasetRefsV1(
            market_dataset_id=market_dataset_id,
            sentiment_dataset_id=sentiment_dataset_id,
        ),
        scheduler=SchedulerConfigV1(
            base_interval_seconds=settings.replay_base_interval_seconds,
            min_interval_seconds=settings.replay_min_interval_seconds,
            price_tick_seconds=settings.replay_price_tick_seconds,
        ),
        replay=ReplayConfigV1(
            pace_seconds_per_base_tick=float(scenario_set.pace_seconds_per_base_tick)
        ),
        prompt=PromptConfigV1(
            prompt_text=prompt_text,
            lookback_bars=settings.replay_prompt_lookback_bars,
            timeframe=settings.replay_prompt_timeframe,
            masking=PromptMaskingV1(time_offset_seconds=settings.replay_prompt_time_offset_seconds),
        ),
        execution=ExecutionConfigV1(
            fee_bps=settings.execution_fee_bps,
            initial_equity_quote=settings.execution_initial_equity_quote,
            gross_leverage_cap=settings.execution_gross_leverage_cap,
            net_exposure_cap=settings.execution_net_exposure_cap,
        ),
    )

    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=timestamp)
    session.add(cfg_row)
    session.flush()

    run = RunRow(
        kind="tournament",
        visibility=submission.visibility,
        market_id=submission.market_id,
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
    payload = RunFinishedPayloadV1.model_validate(row.payload)
    return Decimal(payload.return_pct)


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

        market_datasets = env_set.spot_by_market.get(submission.market_id)
        if not market_datasets:
            raise ValueError(f"Arena datasets missing for market_id={submission.market_id}")

        mode = str(submission.scenario_set_key or "").strip()
        if mode == "env-regimes-v1":
            if len(market_datasets) != 1:
                raise ValueError(
                    f"env-regimes-v1 requires exactly 1 spot dataset for market_id={submission.market_id}"
                )
            spot_ds = market_datasets[0]
            if spot_ds.status != "ready":
                import_dataset(session, dataset_id=spot_ds.dataset_id)
                session.refresh(spot_ds)
            windows = compute_regime_windows(
                session,
                dataset_id=spot_ds.dataset_id,
                market_id=submission.market_id,
                timeframe=settings.replay_prompt_timeframe,
                window_hours=12,
                n_windows=10,
            )
        elif len(market_datasets) == 10:
            windows = [
                ScenarioWindow(
                    index=i,
                    label=f"Window {i + 1}",
                    start=as_utc(ds.start),
                    end=as_utc(ds.end),
                )
                for i, ds in enumerate(market_datasets)
            ]
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
                f"Invalid arena dataset count for market_id={submission.market_id}: {len(market_datasets)}"
            )

        submission.windows_total = int(len(windows))
        submission.updated_at = now()
        session.commit()

        for w in windows:
            existing = session.get(ArenaSubmissionRunRow, (submission_id, int(w.index)))
            if existing is not None:
                if existing.status == "finished" and existing.return_pct is not None:
                    completed_returns.append(existing.return_pct)
                    continue
                raise ValueError(
                    f"submission already has an in-progress scenario run: index={w.index}"
                )

            if len(market_datasets) == 1:
                spot_ds = market_datasets[0]
            else:
                spot_ds = market_datasets[int(w.index)]
            if spot_ds.status != "ready":
                import_dataset(session, dataset_id=spot_ds.dataset_id)

            run_id = _create_scenario_run(
                session,
                submission=submission,
                scenario_set=scenario_set,
                window=w,
                market_dataset_id=spot_ds.dataset_id,
                sentiment_dataset_id=None,
            )

            execute_replay_run(session, run_id=run_id)

            ret = _get_run_return_pct(session, run_id=run_id)
            if ret is None:
                raise ValueError(f"scenario run missing run.finished: run_id={run_id}")

            link = session.get(ArenaSubmissionRunRow, (submission_id, int(w.index)))
            if link is not None:
                link.status = "finished"
                link.return_pct = ret
                run = session.get(RunRow, run_id)
                link.started_at = run.started_at if run is not None else None
                link.ended_at = run.ended_at if run is not None else None
                link.updated_at = now()

            completed_returns.append(ret)
            submission.windows_completed = int(len(completed_returns))
            submission.updated_at = now()
            session.commit()

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
