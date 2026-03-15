from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from v4t.api.deps import get_db
from v4t.api.schemas import (
    PricePoint,
    RunCreateRequest,
    RunIndexOut,
    RunLeaderboardEntry,
    RunOut,
    TimelinePoint,
)
from v4t.api.utils import assert_model_selectable, now
from v4t.auth.deps import get_current_user
from v4t.auth.quota import claim_quota
from v4t.contracts.payloads import MarketPricePayload
from v4t.contracts.run_config import (
    DatasetRefs,
    ExecutionConfig,
    ModelConfig,
    PromptConfig,
    PromptMasking,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.engine import new_session
from v4t.db.models import (
    DatasetRow,
    EventRow,
    PortfolioSnapshotRow,
    RunConfigSnapshotRow,
    RunRow,
    UserRow,
)
from v4t.jobs.repo import dispatch_and_update_job, enqueue_job
from v4t.jobs.types import JOB_TYPE_RUN_EXECUTE_REPLAY
from v4t.settings import get_settings

logger = structlog.get_logger()

router = APIRouter(prefix="/runs", tags=["runs"])


def to_out(row: RunRow) -> RunOut:
    return RunOut(
        run_id=row.run_id,
        parent_run_id=row.parent_run_id,
        market_id=row.market_id,
        model_key=row.model_key,
        status=row.status,
        created_at=row.created_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def _assert_run_details_visible(row: RunRow) -> None:
    if row.kind == "tournament" and row.visibility == "private":
        raise HTTPException(status_code=404, detail="run not found")


def _encode_run_cursor(row: RunRow) -> str:
    return f"{row.created_at.isoformat()}|{row.run_id}"


def _parse_run_cursor(cursor: str | None) -> tuple[datetime | None, UUID | None]:
    if cursor is None:
        return None, None
    ts_text, sep, run_id_text = cursor.partition("|")
    if not sep:
        raise HTTPException(status_code=400, detail="Invalid cursor")
    try:
        return datetime.fromisoformat(ts_text), UUID(run_id_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc


@router.post("", response_model=RunOut)
def create_run(
    req: RunCreateRequest,
    db: Session = Depends(get_db),
    user: UserRow = Depends(get_current_user),
) -> RunOut:
    settings = get_settings()
    if req.model_token_pairs:
        if len(req.model_token_pairs) < 1 or len(req.model_token_pairs) > 3:
            raise HTTPException(status_code=400, detail="model_token_pairs must contain 1-3 items")
        for pair in req.model_token_pairs:
            assert_model_selectable(db, user, pair.model_key)
    else:
        assert_model_selectable(db, user, req.model_key)

    market_ds = db.get(DatasetRow, req.market_dataset_id)
    sent_ds = db.get(DatasetRow, req.sentiment_dataset_id)
    if market_ds is None or sent_ds is None:
        raise HTTPException(status_code=400, detail="dataset_id not found")
    if market_ds.status != "ready" or sent_ds.status != "ready":
        raise HTTPException(status_code=400, detail="datasets must be status=ready")
    if market_ds.start != sent_ds.start or market_ds.end != sent_ds.end:
        raise HTTPException(status_code=400, detail="dataset windows must match exactly")

    # MVP invariant: run selects exactly one market_id; ensure dataset matches.
    market_dataset_market_id = market_ds.params.get("market_id")
    if market_dataset_market_id is not None and str(market_dataset_market_id) != req.market_id:
        raise HTTPException(
            status_code=400,
            detail=f"market_id mismatch: run={req.market_id} market_dataset={market_dataset_market_id}",
        )

    has_quota, runs_used, runs_limit = claim_quota(db, user.user_id)
    if not has_quota:
        raise HTTPException(
            status_code=429, detail=f"Daily quota exceeded: {runs_used}/{runs_limit} runs used"
        )

    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id=req.market_id,
        risk_level=None,
        holding_period=None,
        model=ModelConfig(key=req.model_key),
        datasets=DatasetRefs(
            market_dataset_id=req.market_dataset_id, sentiment_dataset_id=req.sentiment_dataset_id
        ),
        scheduler=SchedulerConfig(
            base_interval_seconds=settings.replay_base_interval_seconds,
            price_tick_seconds=settings.replay_price_tick_seconds,
        ),
        prompt=PromptConfig(
            prompt_text=req.prompt_text,
            system_prompt_override=req.system_prompt,
            lookback_bars=settings.replay_prompt_lookback_bars,
            timeframe=settings.replay_prompt_timeframe,
            masking=PromptMasking(time_offset_seconds=settings.replay_prompt_time_offset_seconds),
        ),
        execution=ExecutionConfig(
            fee_bps=settings.execution_fee_bps,
            initial_equity_quote=settings.execution_initial_equity_quote,
            gross_leverage_cap=settings.execution_gross_leverage_cap,
            net_exposure_cap=settings.execution_net_exposure_cap,
        ),
    )

    timestamp = now()
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=timestamp)
    db.add(cfg_row)
    db.flush()

    if req.model_token_pairs and len(req.model_token_pairs) > 1:
        parent_run = RunRow(
            owner_user_id=user.user_id,
            market_id=req.market_id,
            model_key="multi-pair",
            config_id=cfg_row.config_id,
            status="pending",
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(parent_run)
        db.flush()

        child_runs = []
        for pair in req.model_token_pairs:
            child_cfg = RunConfigSnapshot(
                mode=RunMode.replay,
                market_id=req.market_id,
                risk_level=None,
                holding_period=None,
                model=ModelConfig(key=pair.model_key),
                datasets=DatasetRefs(
                    market_dataset_id=req.market_dataset_id,
                    sentiment_dataset_id=req.sentiment_dataset_id,
                ),
                scheduler=cfg.scheduler,
                prompt=cfg.prompt,
                execution=cfg.execution,
            )
            child_cfg_row = RunConfigSnapshotRow(
                config=child_cfg.model_dump(mode="json"), created_at=timestamp
            )
            db.add(child_cfg_row)
            db.flush()

            child_run = RunRow(
                parent_run_id=parent_run.run_id,
                owner_user_id=user.user_id,
                market_id=req.market_id,
                model_key=pair.model_key,
                config_id=child_cfg_row.config_id,
                status="pending",
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(child_run)
            child_runs.append(child_run)

        db.flush()

        jobs = []
        for child_run in child_runs:
            jobs.append(
                enqueue_job(
                    db, job_type=JOB_TYPE_RUN_EXECUTE_REPLAY, payload={}, run_id=child_run.run_id
                )
            )

        db.commit()

        dispatch_failures = 0
        for job in jobs:
            try:
                dispatch_and_update_job(db, job)
            except Exception as exc:
                dispatch_failures += 1
                logger.error("child_run_dispatch_failed", run_id=job.run_id, error=str(exc))

        if dispatch_failures == len(jobs):
            db.refresh(parent_run)
            parent_run.status = "failed"
            parent_run.error = "all child dispatches failed"
            db.commit()

        return to_out(parent_run)
    else:
        run = RunRow(
            owner_user_id=user.user_id,
            market_id=req.market_id,
            model_key=req.model_key,
            config_id=cfg_row.config_id,
            status="pending",
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(run)
        db.flush()

        job = enqueue_job(db, job_type=JOB_TYPE_RUN_EXECUTE_REPLAY, payload={}, run_id=run.run_id)

        db.commit()

        try:
            dispatch_and_update_job(db, job)
        except Exception as exc:
            logger.error("run_dispatch_failed", run_id=run.run_id, error=str(exc))
            db.refresh(run)
            run.status = "failed"
            db.commit()

        return to_out(run)


@router.get("", response_model=RunIndexOut)
def list_runs(
    limit: int = Query(100, ge=1, le=500),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
) -> RunIndexOut:
    cursor_created_at, cursor_run_id = _parse_run_cursor(cursor)
    stmt = select(RunRow).where(~and_(RunRow.kind == "tournament", RunRow.visibility == "private"))
    if cursor_created_at is not None and cursor_run_id is not None:
        stmt = stmt.where(
            or_(
                RunRow.created_at < cursor_created_at,
                and_(RunRow.created_at == cursor_created_at, RunRow.run_id < cursor_run_id),
            )
        )
    stmt = stmt.order_by(RunRow.created_at.desc(), RunRow.run_id.desc()).limit(limit + 1)
    rows = list(db.execute(stmt).scalars().all())
    visible_rows = rows[:limit]
    next_cursor = (
        _encode_run_cursor(visible_rows[-1]) if len(rows) > limit and visible_rows else None
    )
    return RunIndexOut(
        items=[to_out(r) for r in visible_rows],
        limit=limit,
        next_cursor=next_cursor,
        has_more=len(rows) > limit,
    )


@router.get("/leaderboard", response_model=list[RunLeaderboardEntry])
def get_runs_leaderboard(
    market_id: str | None = Query(None),
    parent_run_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[RunLeaderboardEntry]:
    stmt = (
        select(RunRow, PortfolioSnapshotRow)
        .join(
            PortfolioSnapshotRow,
            and_(
                PortfolioSnapshotRow.run_id == RunRow.run_id,
                PortfolioSnapshotRow.observed_at
                == select(PortfolioSnapshotRow.observed_at)
                .where(PortfolioSnapshotRow.run_id == RunRow.run_id)
                .order_by(PortfolioSnapshotRow.observed_at.desc())
                .limit(1)
                .scalar_subquery(),
            ),
        )
        .where(RunRow.status == "finished")
    )

    if market_id:
        stmt = stmt.where(RunRow.market_id == market_id)
    if parent_run_id:
        stmt = stmt.where(RunRow.parent_run_id == parent_run_id)

    stmt = stmt.order_by(PortfolioSnapshotRow.equity_quote.desc()).limit(limit)

    results = db.execute(stmt).all()

    config_ids = {run_row.config_id for run_row, _ in results}
    configs = {
        cfg.config_id: cfg
        for cfg in db.execute(
            select(RunConfigSnapshotRow).where(RunConfigSnapshotRow.config_id.in_(config_ids))
        ).scalars()
    }

    out: list[RunLeaderboardEntry] = []
    for run_row, snapshot_row in results:
        initial_equity = 10000.0
        cfg_row = configs.get(run_row.config_id)
        if cfg_row:
            cfg = RunConfigSnapshot.model_validate(cfg_row.config)
            initial_equity = cfg.execution.initial_equity_quote

        total_return_pct = (
            (float(snapshot_row.equity_quote) - initial_equity) / initial_equity
        ) * 100

        out.append(
            RunLeaderboardEntry(
                run_id=run_row.run_id,
                parent_run_id=run_row.parent_run_id,
                market_id=run_row.market_id,
                model_key=run_row.model_key,
                total_return_pct=total_return_pct,
                final_equity=float(snapshot_row.equity_quote),
                created_at=run_row.created_at,
            )
        )

    return out


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: UUID, db: Session = Depends(get_db)) -> RunOut:
    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    _assert_run_details_visible(row)
    return to_out(row)


@router.get("/{run_id}/config")
def get_run_config(run_id: UUID, db: Session = Depends(get_db)) -> dict:
    run = db.get(RunRow, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    _assert_run_details_visible(run)

    cfg_row = db.get(RunConfigSnapshotRow, run.config_id)
    if cfg_row is None:
        raise HTTPException(status_code=500, detail="run config not found")
    return cfg_row.config


def _sse(event: str, data: dict, *, event_id: str | None) -> str:
    msg = ""
    if event_id is not None:
        msg += f"id: {event_id}\n"
    if event:
        msg += f"event: {event}\n"
    msg += f"data: {json.dumps(data, separators=(',', ':'))}\n\n"
    return msg


def _parse_last_event_id(v: str | None) -> tuple[datetime | None, str | None]:
    if not v:
        return None, None
    if "|" not in v:
        return None, None
    ts_s, ev_id = v.split("|", 1)
    try:
        return datetime.fromisoformat(ts_s), ev_id
    except Exception:
        logger.warning("invalid_last_event_id", value=v)
        return None, None


def _map_event_name(event_type: str) -> str:
    if event_type.startswith("llm.stream_"):
        return event_type.replace("llm.stream_", "llm_")
    if event_type == "portfolio.snapshot":
        return "portfolio"
    return event_type


def _select_events(
    *,
    run_id: UUID | None,
    interest: set[str],
    cursor_ts: datetime | None,
    cursor_event_id: str | None,
    exclude_private_tournament_runs: bool = False,
) -> list[EventRow]:

    with new_session() as stream_db:
        stmt = select(EventRow).where(EventRow.event_type.in_(interest))
        if run_id is not None:
            stmt = stmt.where(EventRow.run_id == run_id)
        elif exclude_private_tournament_runs:
            stmt = (
                stmt.where(EventRow.run_id.is_not(None))
                .join(RunRow, EventRow.run_id == RunRow.run_id)
                .where(~and_(RunRow.kind == "tournament", RunRow.visibility == "private"))
            )

        if cursor_ts is not None:
            if cursor_event_id is not None:
                stmt = stmt.where(
                    (EventRow.ingested_at > cursor_ts)
                    | (
                        (EventRow.ingested_at == cursor_ts)
                        & (EventRow.event_id > UUID(cursor_event_id))
                    )
                )
            else:
                stmt = stmt.where(EventRow.ingested_at > cursor_ts)

        stmt = stmt.order_by(EventRow.ingested_at, EventRow.event_id).limit(500)
        return list(stream_db.execute(stmt).scalars().all())


@router.get("/{run_id}/stream")
async def stream_run_events(
    run_id: UUID,
    request: Request,
) -> StreamingResponse:
    with new_session() as check_db:
        run = check_db.get(RunRow, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        _assert_run_details_visible(run)

    interest = {
        "run.started",
        "run.finished",
        "run.failed",
        "llm.stream_start",
        "llm.stream_delta",
        "llm.stream_end",
        "llm.decision",
        "portfolio.snapshot",
    }

    last_id_hdr = request.headers.get("last-event-id")
    cursor_ts, cursor_event_id = _parse_last_event_id(last_id_hdr)

    async def gen():
        idle_started: float | None = None
        last_keepalive = time.time()
        finished_seen = False

        nonlocal cursor_ts, cursor_event_id

        while True:
            rows = await run_in_threadpool(
                _select_events,
                run_id=run_id,
                interest=interest,
                cursor_ts=cursor_ts,
                cursor_event_id=cursor_event_id,
            )

            if rows:
                idle_started = None
                for r in rows:
                    cursor_ts = r.ingested_at
                    cursor_event_id = str(r.event_id)

                    sse_id = f"{r.ingested_at.isoformat()}|{r.event_id}"
                    event_name = _map_event_name(r.event_type)

                    if r.event_type in {"run.finished", "run.failed"}:
                        finished_seen = True

                    yield _sse(
                        event_name,
                        {
                            "event_type": r.event_type,
                            "observed_at": r.observed_at.isoformat(),
                            "payload": r.payload,
                        },
                        event_id=sse_id,
                    )

                continue

            now_t = time.time()
            if now_t - last_keepalive >= 10:
                last_keepalive = now_t
                yield ": ping\n\n"

            if finished_seen:
                if idle_started is None:
                    idle_started = now_t
                if now_t - idle_started >= 5:
                    break

            await asyncio.sleep(0.25)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.websocket("/ws")
async def ws_run_lifecycle(websocket: WebSocket) -> None:
    interest = {"run.started", "run.finished", "run.failed"}

    await websocket.accept()
    cursor_ts: datetime | None = datetime.now(UTC)
    cursor_event_id: str | None = None

    last_keepalive = time.monotonic()

    try:
        while True:
            rows = await run_in_threadpool(
                _select_events,
                run_id=None,
                interest=interest,
                cursor_ts=cursor_ts,
                cursor_event_id=cursor_event_id,
                exclude_private_tournament_runs=True,
            )

            if rows:
                for r in rows:
                    cursor_ts = r.ingested_at
                    cursor_event_id = str(r.event_id)
                    await websocket.send_json(
                        {
                            "event_type": r.event_type,
                            "event_name": _map_event_name(r.event_type),
                            "observed_at": r.observed_at.isoformat(),
                            "payload": r.payload,
                        }
                    )
                continue

            now_t = time.monotonic()
            if now_t - last_keepalive >= 10:
                last_keepalive = now_t
                await websocket.send_json({"type": "ping"})

            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return


@router.websocket("/{run_id}/ws")
async def ws_run_events(websocket: WebSocket, run_id: UUID) -> None:
    def _is_visible() -> bool:
        with new_session() as check_db:
            run = check_db.get(RunRow, run_id)
            if run is None:
                return False
            try:
                _assert_run_details_visible(run)
            except HTTPException:
                return False
            return True

    interest = {
        "run.started",
        "run.finished",
        "run.failed",
        "llm.stream_start",
        "llm.stream_end",
        "llm.decision",
        "portfolio.snapshot",
    }

    await websocket.accept()
    visible = await run_in_threadpool(_is_visible)
    if not visible:
        await websocket.close(code=1008)
        return
    cursor_ts: datetime | None = datetime.now(UTC)
    cursor_event_id: str | None = None

    last_keepalive = time.monotonic()
    idle_started: float | None = None
    finished_seen = False

    try:
        while True:
            rows = await run_in_threadpool(
                _select_events,
                run_id=run_id,
                interest=interest,
                cursor_ts=cursor_ts,
                cursor_event_id=cursor_event_id,
            )

            if rows:
                idle_started = None
                for r in rows:
                    cursor_ts = r.ingested_at
                    cursor_event_id = str(r.event_id)

                    if r.event_type in {"run.finished", "run.failed"}:
                        finished_seen = True

                    await websocket.send_json(
                        {
                            "event_type": r.event_type,
                            "event_name": _map_event_name(r.event_type),
                            "observed_at": r.observed_at.isoformat(),
                            "payload": r.payload,
                        }
                    )

                continue

            now_t = time.monotonic()
            if now_t - last_keepalive >= 10:
                last_keepalive = now_t
                await websocket.send_json({"type": "ping"})

            if finished_seen:
                if idle_started is None:
                    idle_started = now_t
                if now_t - idle_started >= 5:
                    await websocket.close()
                    break

            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return


@router.post("/{run_id}/stop")
def stop_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: UserRow = Depends(get_current_user),
) -> dict[str, str]:
    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    _assert_run_details_visible(row)
    if row.owner_user_id is not None and row.owner_user_id != user.user_id:
        from v4t.auth.deps import is_admin_user

        if not is_admin_user(user):
            raise HTTPException(status_code=403, detail="not authorized to stop this run")
    row.stop_requested = True
    row.updated_at = now()
    db.commit()
    return {"status": "ok"}


@router.get("/{run_id}/timeline", response_model=list[TimelinePoint])
def get_timeline(run_id: UUID, db: Session = Depends(get_db)) -> list[TimelinePoint]:
    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    _assert_run_details_visible(row)

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

    run = db.get(RunRow, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    _assert_run_details_visible(run)

    cfg_row = db.get(RunConfigSnapshotRow, run.config_id)
    if cfg_row is None:
        raise HTTPException(status_code=500, detail="run config not found")

    cfg = RunConfigSnapshot.model_validate(cfg_row.config)

    if cfg.mode == RunMode.live:
        stmt = (
            select(EventRow)
            .where(
                EventRow.run_id == run_id,
                EventRow.event_type == "market.price",
            )
            .order_by(EventRow.observed_at.desc())
            .limit(limit)
        )
    else:
        market_ds_id = cfg.datasets.market_dataset_id
        if market_ds_id is None:
            return []
        stmt = (
            select(EventRow)
            .where(
                EventRow.dataset_id == market_ds_id,
                EventRow.event_type == "market.price",
            )
            .order_by(EventRow.observed_at.desc())
            .limit(limit)
        )

    rows = list(db.execute(stmt).scalars().all())
    rows.reverse()
    target_market = cfg.market_id
    out: list[PricePoint] = []
    for r in rows:
        try:
            p = MarketPricePayload.model_validate(r.payload)
        except Exception:
            continue
        if p.market_id != target_market:
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
    from v4t.db.models import EventRow

    row = db.get(RunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    _assert_run_details_visible(row)

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
    _assert_run_details_visible(row)
    return {"summary_text": row.summary_text}
