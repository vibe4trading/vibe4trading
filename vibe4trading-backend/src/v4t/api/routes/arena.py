from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.schemas import (
    ArenaScenarioRunOut,
    ArenaSubmissionCreateRequest,
    ArenaSubmissionDetailOut,
    ArenaSubmissionOut,
    LeaderboardEntryOut,
    ScenarioSetOut,
    ScenarioWindowOut,
)
from v4t.api.utils import assert_model_predefined, now
from v4t.arena.env_dataset_set import list_arena_env_markets, load_arena_env_dataset_set
from v4t.arena.regime_windows import compute_regime_windows
from v4t.arena.scenario_sets import list_scenario_sets
from v4t.auth.deps import get_current_user
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, UserRow
from v4t.jobs.repo import dispatch_and_update_job, enqueue_job
from v4t.jobs.types import JOB_TYPE_ARENA_EXECUTE_SUBMISSION
from v4t.settings import get_settings
from v4t.utils.datetime import as_utc

logger = structlog.get_logger()

router = APIRouter(prefix="/arena", tags=["arena"])


@router.get("/markets", response_model=list[str])
def list_markets(db: Session = Depends(get_db)) -> list[str]:
    try:
        return list_arena_env_markets(db)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _to_submission_out(row: ArenaSubmissionRow) -> ArenaSubmissionOut:
    return ArenaSubmissionOut(
        submission_id=row.submission_id,
        scenario_set_key=row.scenario_set_key,
        market_id=row.market_id,
        model_key=row.model_key,
        visibility=row.visibility,
        status=row.status,
        windows_total=row.windows_total,
        windows_completed=row.windows_completed,
        total_return_pct=float(row.total_return_pct) if row.total_return_pct is not None else None,
        avg_return_pct=float(row.avg_return_pct) if row.avg_return_pct is not None else None,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def _to_run_out(row: ArenaSubmissionRunRow) -> ArenaScenarioRunOut:
    return ArenaScenarioRunOut(
        submission_id=row.submission_id,
        scenario_index=row.scenario_index,
        run_id=row.run_id,
        window_start=row.window_start,
        window_end=row.window_end,
        status=row.status,
        return_pct=float(row.return_pct) if row.return_pct is not None else None,
        error=row.error,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


@router.get("/scenario_sets", response_model=list[ScenarioSetOut])
def get_scenario_sets(db: Session = Depends(get_db)) -> list[ScenarioSetOut]:
    settings = get_settings()
    out: list[ScenarioSetOut] = []
    sets = list_scenario_sets()
    for s in sets:
        out.append(
            ScenarioSetOut(
                key=s.key,
                name=s.name,
                description=s.description,
                windows=[
                    ScenarioWindowOut(
                        index=w.index,
                        label=w.label,
                        start=w.start,
                        end=w.end,
                    )
                    for w in s.windows
                ],
                base_interval_seconds=settings.replay_base_interval_seconds,
                min_interval_seconds=settings.replay_min_interval_seconds,
                price_tick_seconds=settings.replay_price_tick_seconds,
                lookback_bars=settings.replay_prompt_lookback_bars,
                timeframe=settings.replay_prompt_timeframe,
                time_offset_seconds=settings.replay_prompt_time_offset_seconds,
                fee_bps=settings.execution_fee_bps,
                initial_equity_quote=settings.execution_initial_equity_quote,
            )
        )

    try:
        env_set = load_arena_env_dataset_set(db)
    except ValueError:
        env_set = None
    if env_set is not None:
        rep_market_id = env_set.market_ids[0] if env_set.market_ids else None
        fullrange_windows: list[ScenarioWindowOut] = []
        regime_windows: list[ScenarioWindowOut] = []
        if rep_market_id:
            rep_datasets = env_set.spot_by_market.get(rep_market_id) or []
            if len(rep_datasets) == 10:
                fullrange_windows = [
                    ScenarioWindowOut(
                        index=i,
                        label=f"Window {i + 1}",
                        start=as_utc(ds.start),
                        end=as_utc(ds.end),
                    )
                    for i, ds in enumerate(rep_datasets)
                ]
            elif len(rep_datasets) == 1:
                spot_ds = rep_datasets[0]
                fullrange_windows = [
                    ScenarioWindowOut(
                        index=0,
                        label="Full Range",
                        start=as_utc(spot_ds.start),
                        end=as_utc(spot_ds.end),
                    )
                ]
                regime_windows = [
                    ScenarioWindowOut(index=w.index, label=w.label, start=w.start, end=w.end)
                    for w in compute_regime_windows(
                        db,
                        dataset_id=spot_ds.dataset_id,
                        market_id=rep_market_id,
                        timeframe=settings.replay_prompt_timeframe,
                        window_hours=12,
                        n_windows=10,
                    )
                ]

        if fullrange_windows:
            out.append(
                ScenarioSetOut(
                    key="env-fullrange-v1",
                    name="Env Full Range (v1)",
                    description="Run each configured dataset window end-to-end (no slicing).",
                    windows=fullrange_windows,
                    base_interval_seconds=settings.replay_base_interval_seconds,
                    min_interval_seconds=settings.replay_min_interval_seconds,
                    price_tick_seconds=settings.replay_price_tick_seconds,
                    lookback_bars=settings.replay_prompt_lookback_bars,
                    timeframe=settings.replay_prompt_timeframe,
                    time_offset_seconds=settings.replay_prompt_time_offset_seconds,
                    fee_bps=settings.execution_fee_bps,
                    initial_equity_quote=settings.execution_initial_equity_quote,
                )
            )

        if regime_windows:
            out.append(
                ScenarioSetOut(
                    key="env-regimes-v1",
                    name="Env Regimes (v1)",
                    description=(
                        "10x 12h windows selected from each market's history to represent "
                        "different regimes (crash/rally/volatility/sideways + diverse samples)."
                    ),
                    windows=regime_windows,
                    base_interval_seconds=settings.replay_base_interval_seconds,
                    min_interval_seconds=settings.replay_min_interval_seconds,
                    price_tick_seconds=settings.replay_price_tick_seconds,
                    lookback_bars=settings.replay_prompt_lookback_bars,
                    timeframe=settings.replay_prompt_timeframe,
                    time_offset_seconds=settings.replay_prompt_time_offset_seconds,
                    fee_bps=settings.execution_fee_bps,
                    initial_equity_quote=settings.execution_initial_equity_quote,
                )
            )

        any_counts = {len(v) for v in env_set.spot_by_market.values()}
        if any_counts == {10}:
            out.append(
                ScenarioSetOut(
                    key="env-datasets-v1",
                    name="Env Datasets (v1)",
                    description=(
                        "10 fixed windows backed by pre-populated DatasetRow records (env-configured)."
                    ),
                    windows=[
                        ScenarioWindowOut(index=i, label=f"Window {i + 1}", start=st, end=en)
                        for i, (st, en) in enumerate(env_set.windows)
                    ],
                    base_interval_seconds=settings.replay_base_interval_seconds,
                    min_interval_seconds=settings.replay_min_interval_seconds,
                    price_tick_seconds=settings.replay_price_tick_seconds,
                    lookback_bars=settings.replay_prompt_lookback_bars,
                    timeframe=settings.replay_prompt_timeframe,
                    time_offset_seconds=settings.replay_prompt_time_offset_seconds,
                    fee_bps=settings.execution_fee_bps,
                    initial_equity_quote=settings.execution_initial_equity_quote,
                )
            )
    return out


@router.post("/submissions", response_model=ArenaSubmissionOut)
def create_submission(
    req: ArenaSubmissionCreateRequest,
    db: Session = Depends(get_db),
    user: UserRow = Depends(get_current_user),
) -> ArenaSubmissionOut:
    try:
        env_set = load_arena_env_dataset_set(db)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if env_set is None:
        raise HTTPException(status_code=500, detail="Arena datasets not configured")

    env_markets = env_set.market_ids

    if req.market_id not in env_markets:
        raise HTTPException(status_code=400, detail="Invalid market_id")
    assert_model_predefined(db, req.model_key)

    market_datasets = env_set.spot_by_market.get(req.market_id) or []
    windows_total = 0
    if len(market_datasets) == 10:
        windows_total = 10
    elif len(market_datasets) == 1:
        windows_total = 1
    else:
        raise HTTPException(status_code=500, detail="Arena datasets misconfigured")

    timestamp = now()
    row = ArenaSubmissionRow(
        owner_user_id=user.user_id,
        scenario_set_key="env-fullrange-v1",
        market_id=req.market_id,
        model_key=req.model_key,
        prompt_template_id=None,
        prompt_vars={"prompt_text": req.prompt_text},
        visibility=req.visibility,
        status="pending",
        windows_total=windows_total,
        windows_completed=0,
        total_return_pct=None,
        avg_return_pct=None,
        error=None,
        started_at=None,
        ended_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(row)
    db.flush()

    job = enqueue_job(
        db,
        job_type=JOB_TYPE_ARENA_EXECUTE_SUBMISSION,
        payload={"submission_id": str(row.submission_id)},
    )

    db.commit()

    try:
        dispatch_and_update_job(db, job)
    except Exception as exc:
        row.status = "failed"
        row.error = f"dispatch_failed: {repr(exc)}"
        db.commit()

    db.refresh(row)
    return _to_submission_out(row)


@router.get("/submissions", response_model=list[ArenaSubmissionOut])
def list_submissions(
    scenario_set_key: str | None = Query(None),
    market_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[ArenaSubmissionOut]:
    stmt = select(ArenaSubmissionRow)
    if scenario_set_key:
        stmt = stmt.where(ArenaSubmissionRow.scenario_set_key == scenario_set_key)
    if market_id:
        stmt = stmt.where(ArenaSubmissionRow.market_id == market_id)
    stmt = stmt.order_by(ArenaSubmissionRow.created_at.desc()).limit(limit).offset(offset)
    rows = list(db.execute(stmt).scalars().all())
    return [_to_submission_out(r) for r in rows]


@router.get("/submissions/{submission_id}", response_model=ArenaSubmissionDetailOut)
def get_submission(submission_id: UUID, db: Session = Depends(get_db)) -> ArenaSubmissionDetailOut:
    row = db.get(ArenaSubmissionRow, submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="submission not found")

    runs = list(
        db.execute(
            select(ArenaSubmissionRunRow)
            .where(ArenaSubmissionRunRow.submission_id == submission_id)
            .order_by(ArenaSubmissionRunRow.scenario_index)
        )
        .scalars()
        .all()
    )
    base = _to_submission_out(row)
    return ArenaSubmissionDetailOut(**base.model_dump(), runs=[_to_run_out(r) for r in runs])


@router.get("/leaderboards", response_model=list[LeaderboardEntryOut])
def get_leaderboard(
    scenario_set_key: str | None = Query(None),
    market_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[LeaderboardEntryOut]:
    stmt = select(ArenaSubmissionRow).where(
        ArenaSubmissionRow.status == "finished",
        ArenaSubmissionRow.total_return_pct.is_not(None),
        ArenaSubmissionRow.avg_return_pct.is_not(None),
    )
    if scenario_set_key:
        stmt = stmt.where(ArenaSubmissionRow.scenario_set_key == scenario_set_key)
    if market_id:
        stmt = stmt.where(ArenaSubmissionRow.market_id == market_id)
    stmt = stmt.order_by(ArenaSubmissionRow.total_return_pct.desc()).limit(limit)

    rows = list(db.execute(stmt).scalars().all())
    out: list[LeaderboardEntryOut] = []
    for r in rows:
        # Query filters ensure these are not None
        if r.total_return_pct is None or r.avg_return_pct is None:
            continue
        out.append(
            LeaderboardEntryOut(
                submission_id=r.submission_id,
                scenario_set_key=r.scenario_set_key,
                market_id=r.market_id,
                model_key=r.model_key,
                total_return_pct=float(r.total_return_pct),
                avg_return_pct=float(r.avg_return_pct),
                created_at=r.created_at,
            )
        )
    return out
