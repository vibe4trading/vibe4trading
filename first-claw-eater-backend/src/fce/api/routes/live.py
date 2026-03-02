from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fce.api.deps import get_db
from fce.api.routes.runs import _default_templates, _template_snapshot_from_row, _to_out
from fce.api.schemas import LiveRunCreateRequest, LiveRunOut, RunOut
from fce.contracts.run_config import (
    DatasetRefsV1,
    ExecutionConfigV1,
    LiveConfigV1,
    ModelConfigV1,
    PromptConfigV1,
    PromptMaskingV1,
    RunConfigSnapshotV1,
    RunMode,
    SchedulerConfigV1,
)
from fce.db.models import PromptTemplateRow, RunConfigSnapshotRow, RunRow
from fce.jobs.repo import enqueue_job
from fce.jobs.types import JOB_TYPE_RUN_EXECUTE_LIVE
from fce.settings import get_settings, parse_csv_set

router = APIRouter(prefix="/live", tags=["live"])


def _now() -> datetime:
    return datetime.now(UTC)


def _assert_model_allowed(model_key: str) -> None:
    allowed = parse_csv_set(get_settings().llm_model_allowlist)
    if model_key != "stub" and allowed is not None and model_key not in allowed:
        raise HTTPException(status_code=400, detail=f"model_key not allowed: {model_key}")


def _find_latest_live_run(db: Session) -> RunRow | None:
    # Avoid JSON queries for portability (SQLite in tests).
    rows = list(
        db.execute(select(RunRow).order_by(RunRow.created_at.desc()).limit(50)).scalars().all()
    )
    for r in rows:
        cfg_row = db.get(RunConfigSnapshotRow, r.config_id)
        if cfg_row is None:
            continue
        try:
            cfg = RunConfigSnapshotV1.model_validate(cfg_row.config)
        except Exception:
            continue
        if cfg.mode == RunMode.live:
            return r
    return None


@router.get("/run", response_model=LiveRunOut)
def get_live_run(db: Session = Depends(get_db)) -> LiveRunOut:
    r = _find_latest_live_run(db)
    return LiveRunOut(run=_to_out(r) if r is not None else None)


@router.post("/run", response_model=RunOut)
def start_live_run(req: LiveRunCreateRequest, db: Session = Depends(get_db)) -> RunOut:
    _assert_model_allowed(req.model_key)

    existing = _find_latest_live_run(db)
    if existing is not None and existing.status == "running" and not req.force_restart:
        return _to_out(existing)

    if existing is not None and existing.status == "running" and req.force_restart:
        existing.stop_requested = True
        existing.updated_at = _now()
        db.commit()

    live_cfg = LiveConfigV1(
        source=req.live_source,
        chain_id=req.chain_id,
        pair_id=req.pair_id,
        base_price=req.base_price,
    )
    if live_cfg.source == "dexscreener" and (not live_cfg.chain_id or not live_cfg.pair_id):
        raise HTTPException(status_code=400, detail="dexscreener live requires chain_id + pair_id")

    templates = _default_templates()
    if req.prompt_template_id is not None:
        tpl = db.get(PromptTemplateRow, req.prompt_template_id)
        if tpl is None:
            raise HTTPException(status_code=400, detail="prompt_template_id not found")
        try:
            templates = _template_snapshot_from_row(tpl, vars=req.prompt_vars)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    cfg = RunConfigSnapshotV1(
        mode=RunMode.live,
        market_id=req.market_id,
        model=ModelConfigV1(key=req.model_key),
        datasets=DatasetRefsV1(spot_dataset_id=None, sentiment_dataset_id=None),
        live=live_cfg,
        scheduler=SchedulerConfigV1(
            base_interval_seconds=req.base_interval_seconds,
            min_interval_seconds=req.min_interval_seconds,
            price_tick_seconds=req.price_tick_seconds,
        ),
        prompt=PromptConfigV1(
            template=templates,
            lookback_bars=req.lookback_bars,
            timeframe=req.timeframe,
            masking=PromptMaskingV1(time_offset_seconds=req.time_offset_seconds),
        ),
        execution=ExecutionConfigV1(
            fee_bps=req.fee_bps,
            initial_equity_quote=req.initial_equity_quote,
            gross_leverage_cap=1.0,
            net_exposure_cap=1.0,
        ),
    )

    now = _now()
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=now)
    db.add(cfg_row)
    db.flush()

    run = RunRow(
        market_id=req.market_id,
        model_key=req.model_key,
        config_id=cfg_row.config_id,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    db.flush()

    enqueue_job(db, job_type=JOB_TYPE_RUN_EXECUTE_LIVE, payload={}, run_id=run.run_id)
    db.commit()
    return _to_out(run)
