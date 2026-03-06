from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.routes.runs import to_out
from v4t.api.schemas import LiveRunCreateRequest, LiveRunOut, RunOut
from v4t.api.utils import assert_model_selectable, now
from v4t.auth.deps import get_current_user
from v4t.benchmark.spec import get_risk_profile
from v4t.contracts.run_config import (
    DatasetRefs,
    ExecutionConfig,
    LiveConfig,
    ModelConfig,
    PromptConfig,
    PromptMasking,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.models import RunConfigSnapshotRow, RunRow, UserRow
from v4t.jobs.repo import dispatch_and_update_job, enqueue_job
from v4t.jobs.types import JOB_TYPE_RUN_EXECUTE_LIVE
from v4t.settings import get_settings

logger = structlog.get_logger()

router = APIRouter(prefix="/live", tags=["live"])


def _find_latest_live_run(db: Session) -> RunRow | None:
    results = list(
        db.execute(
            select(RunRow, RunConfigSnapshotRow)
            .join(RunConfigSnapshotRow, RunRow.config_id == RunConfigSnapshotRow.config_id)
            .order_by(RunRow.created_at.desc())
            .limit(50)
        ).all()
    )
    for run_row, cfg_row in results:
        try:
            cfg = RunConfigSnapshot.model_validate(cfg_row.config)
        except Exception:
            continue
        if cfg.mode == RunMode.live:
            return run_row
    return None


@router.get("/run", response_model=LiveRunOut)
def get_live_run(db: Session = Depends(get_db)) -> LiveRunOut:
    r = _find_latest_live_run(db)
    return LiveRunOut(run=to_out(r) if r is not None else None)


@router.post("/run", response_model=RunOut)
def start_live_run(
    req: LiveRunCreateRequest,
    db: Session = Depends(get_db),
    user: UserRow = Depends(get_current_user),
) -> RunOut:
    settings = get_settings()
    assert_model_selectable(db, user, req.model_key)

    existing = _find_latest_live_run(db)
    if existing is not None and existing.status == "running" and not req.force_restart:
        return to_out(existing)

    if existing is not None and existing.status == "running" and req.force_restart:
        existing.stop_requested = True
        existing.updated_at = now()
        db.flush()

    live_cfg = LiveConfig(
        source=req.live_source,
        chain_id=req.chain_id,
        pair_id=req.pair_id,
        base_price=req.base_price,
    )
    if live_cfg.source == "dexscreener" and (not live_cfg.chain_id or not live_cfg.pair_id):
        raise HTTPException(status_code=400, detail="dexscreener live requires chain_id + pair_id")

    risk_profile = get_risk_profile(req.risk_level) if req.decision_schema_version == 2 else None
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
        mode=RunMode.live,
        decision_schema_version=req.decision_schema_version,
        market_id=req.market_id,
        risk_level=req.risk_level,
        holding_period=req.holding_period,
        model=ModelConfig(key=req.model_key),
        datasets=DatasetRefs(market_dataset_id=None, sentiment_dataset_id=None),
        live=live_cfg,
        scheduler=SchedulerConfig(
            base_interval_seconds=settings.live_base_interval_seconds,
            min_interval_seconds=settings.live_min_interval_seconds,
            price_tick_seconds=settings.live_price_tick_seconds,
        ),
        prompt=PromptConfig(
            prompt_text=req.prompt_text,
            system_prompt_override=req.system_prompt,
            lookback_bars=settings.live_prompt_lookback_bars,
            timeframe=settings.live_prompt_timeframe,
            masking=PromptMasking(time_offset_seconds=settings.live_prompt_time_offset_seconds),
        ),
        execution=ExecutionConfig(
            fee_bps=settings.execution_fee_bps,
            initial_equity_quote=settings.execution_initial_equity_quote,
            gross_leverage_cap=gross_leverage_cap,
            net_exposure_cap=net_exposure_cap,
        ),
    )

    timestamp = now()
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=timestamp)
    db.add(cfg_row)
    db.flush()

    run = RunRow(
        market_id=req.market_id,
        model_key=req.model_key,
        config_id=cfg_row.config_id,
        owner_user_id=user.user_id,
        status="pending",
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(run)
    db.flush()

    job = enqueue_job(db, job_type=JOB_TYPE_RUN_EXECUTE_LIVE, payload={}, run_id=run.run_id)

    db.commit()

    try:
        dispatch_and_update_job(db, job)
    except Exception:
        db.refresh(run)
        run.status = "failed"
        db.commit()

    return to_out(run)
