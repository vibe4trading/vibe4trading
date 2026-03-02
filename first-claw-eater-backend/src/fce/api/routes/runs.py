from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from fce.api.deps import get_db
from fce.api.schemas import PricePoint, RunCreateRequest, RunOut, TimelinePoint
from fce.contracts.payloads import MarketPricePayloadV1
from fce.contracts.run_config import (
    DatasetRefsV1,
    ExecutionConfigV1,
    ModelConfigV1,
    PromptConfigV1,
    PromptMaskingV1,
    PromptTemplateSnapshotV1,
    RunConfigSnapshotV1,
    RunMode,
    SchedulerConfigV1,
)
from fce.db.models import (
    DatasetRow,
    PortfolioSnapshotRow,
    PromptTemplateRow,
    RunConfigSnapshotRow,
    RunRow,
)
from fce.jobs.repo import enqueue_job
from fce.jobs.types import JOB_TYPE_RUN_EXECUTE_REPLAY
from fce.settings import get_settings, parse_csv_set

router = APIRouter(prefix="/runs", tags=["runs"])


def _now() -> datetime:
    return datetime.now(UTC)


def _assert_model_allowed(model_key: str) -> None:
    allowed = parse_csv_set(get_settings().llm_model_allowlist)
    if model_key != "stub" and allowed is not None and model_key not in allowed:
        raise HTTPException(status_code=400, detail=f"model_key not allowed: {model_key}")


def _to_out(row: RunRow) -> RunOut:
    return RunOut(
        run_id=row.run_id,
        market_id=row.market_id,
        model_key=row.model_key,
        status=row.status,
        created_at=row.created_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def _default_templates() -> PromptTemplateSnapshotV1:
    system = (
        "You are a trading decision engine. "
        "Output ONLY a valid JSON object matching schema_version=1. "
        "Spot is long-only; exposure must be between 0 and 1."
    )
    user = (
        "market_id={{market_id}}\n"
        "tick_time={{tick_time}}\n\n"
        "Recent closes (oldest->newest):\n"
        "{{#closes}}- {{.}}\n{{/closes}}\n"
        "{{#features}}Features: momentum={{momentum}} return_pct={{return_pct}}\n{{/features}}"
        "{{^features}}Features: (insufficient data)\n{{/features}}\n"
        "Portfolio: equity={{portfolio.equity_quote}} cash={{portfolio.cash_quote}} "
        "qty={{portfolio.position_qty_base}} price={{portfolio.price}}\n\n"
        "Recent sentiment summaries:\n"
        "{{#sentiment_summaries}}- {{item_time}} {{summary_text}}\n{{/sentiment_summaries}}"
        "{{^sentiment_summaries}}(none)\n{{/sentiment_summaries}}\n"
        "Last decisions:\n"
        "{{#memory}}- accepted={{accepted}} target={{targets}} conf={{confidence}}\n  {{rationale}}\n{{/memory}}"
        "{{^memory}}(none)\n{{/memory}}\n\n"
        "Return a JSON object like:\n"
        '{"schema_version":1,"targets":{"{{market_id}}":0.25},"next_check_seconds":600,"confidence":0.6,"key_signals":["..."],"rationale":"..."}'
    )
    return PromptTemplateSnapshotV1(system=system, user=user, vars={})


def _template_snapshot_from_row(row: PromptTemplateRow, *, vars: dict) -> PromptTemplateSnapshotV1:
    if row.engine != "mustache":
        raise ValueError(f"Unsupported prompt template engine: {row.engine}")
    return PromptTemplateSnapshotV1(
        engine="mustache",
        system=row.system_template,
        user=row.user_template,
        vars=vars,
    )


@router.post("", response_model=RunOut)
def create_run(req: RunCreateRequest, db: Session = Depends(get_db)) -> RunOut:
    _assert_model_allowed(req.model_key)

    spot_ds = db.get(DatasetRow, req.spot_dataset_id)
    sent_ds = db.get(DatasetRow, req.sentiment_dataset_id)
    if spot_ds is None or sent_ds is None:
        raise HTTPException(status_code=400, detail="dataset_id not found")
    if spot_ds.status != "ready" or sent_ds.status != "ready":
        raise HTTPException(status_code=400, detail="datasets must be status=ready")
    if spot_ds.start != sent_ds.start or spot_ds.end != sent_ds.end:
        raise HTTPException(status_code=400, detail="dataset windows must match exactly")

    # MVP invariant: run selects exactly one market_id; ensure dataset matches.
    spot_market_id = spot_ds.params.get("market_id")
    if spot_market_id and str(spot_market_id) != req.market_id:
        raise HTTPException(
            status_code=400,
            detail=f"market_id mismatch: run={req.market_id} spot_dataset={spot_market_id}",
        )

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
        mode=RunMode.replay,
        market_id=req.market_id,
        model=ModelConfigV1(key=req.model_key),
        datasets=DatasetRefsV1(
            spot_dataset_id=req.spot_dataset_id, sentiment_dataset_id=req.sentiment_dataset_id
        ),
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

    enqueue_job(db, job_type=JOB_TYPE_RUN_EXECUTE_REPLAY, payload={}, run_id=run.run_id)
    db.commit()
    return _to_out(run)


@router.get("", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)) -> list[RunOut]:
    rows = list(db.execute(select(RunRow).order_by(RunRow.created_at.desc())).scalars().all())
    return [_to_out(r) for r in rows]


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: UUID, db: Session = Depends(get_db)) -> RunOut:
    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _to_out(row)


@router.post("/{run_id}/stop")
def stop_run(run_id: UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    row.stop_requested = True
    row.updated_at = _now()
    db.commit()
    return {"status": "ok"}


@router.get("/{run_id}/timeline", response_model=list[TimelinePoint])
def get_timeline(run_id: UUID, db: Session = Depends(get_db)) -> list[TimelinePoint]:
    stmt = (
        select(PortfolioSnapshotRow)
        .where(PortfolioSnapshotRow.run_id == run_id)
        .order_by(PortfolioSnapshotRow.observed_at)
    )
    rows = list(db.execute(stmt).scalars().all())
    return [
        TimelinePoint(
            observed_at=r.observed_at,
            equity_quote=float(r.equity_quote),
            cash_quote=float(r.cash_quote),
        )
        for r in rows
    ]


@router.get("/{run_id}/prices", response_model=list[PricePoint])
def get_prices(
    run_id: UUID,
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> list[PricePoint]:
    """Return recent market.price points for a run.

    - Replay runs read from the referenced spot dataset.
    - Live runs read from run-scoped market.price events.
    """

    from decimal import Decimal

    from fce.db.models import EventRow

    run = db.get(RunRow, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    cfg_row = db.get(RunConfigSnapshotRow, run.config_id)
    if cfg_row is None:
        raise HTTPException(status_code=500, detail="run config not found")

    cfg = RunConfigSnapshotV1.model_validate(cfg_row.config)

    if cfg.mode == RunMode.live:
        stmt = (
            select(EventRow)
            .where(EventRow.run_id == run_id, EventRow.event_type == "market.price")
            .order_by(EventRow.observed_at.desc())
            .limit(limit)
        )
    else:
        spot_ds_id = cfg.datasets.spot_dataset_id
        if spot_ds_id is None:
            return []
        stmt = (
            select(EventRow)
            .where(EventRow.dataset_id == spot_ds_id, EventRow.event_type == "market.price")
            .order_by(EventRow.observed_at.desc())
            .limit(limit)
        )

    rows = list(db.execute(stmt).scalars().all())
    rows.reverse()
    out: list[PricePoint] = []
    for r in rows:
        try:
            p = MarketPricePayloadV1.model_validate(r.payload)
        except Exception:
            continue
        if p.market_id != cfg.market_id:
            continue
        out.append(PricePoint(observed_at=r.observed_at, price=float(Decimal(p.price))))
    return out


@router.get("/{run_id}/decisions")
def get_decisions(
    run_id: UUID,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    from fce.db.models import EventRow

    stmt = (
        select(EventRow)
        .where(EventRow.run_id == run_id, EventRow.event_type == "llm.decision")
        .order_by(EventRow.observed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(db.execute(stmt).scalars().all())
    rows.reverse()
    return [r.payload for r in rows]


@router.get("/{run_id}/summary")
def get_summary(run_id: UUID, db: Session = Depends(get_db)) -> dict[str, str | None]:
    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {"summary_text": row.summary_text}
