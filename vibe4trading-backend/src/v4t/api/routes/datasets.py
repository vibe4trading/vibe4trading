from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.schemas import DatasetCreateRequest, DatasetIndexOut, DatasetOut
from v4t.api.utils import now
from v4t.auth.deps import get_admin_user, get_current_user
from v4t.db.models import DatasetRow, UserRow
from v4t.jobs.repo import dispatch_and_update_job, enqueue_job
from v4t.jobs.types import JOB_TYPE_DATASET_IMPORT

logger = structlog.get_logger()

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _to_out(row: DatasetRow) -> DatasetOut:
    return DatasetOut(
        dataset_id=row.dataset_id,
        category=row.category,
        source=row.source,
        start=row.start,
        end=row.end,
        status=row.status,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=DatasetOut)
def create_dataset(
    req: DatasetCreateRequest,
    db: Session = Depends(get_db),
    _user: UserRow = Depends(get_current_user),
) -> DatasetOut:
    if req.end <= req.start:
        raise HTTPException(status_code=400, detail="end must be after start")

    timestamp = now()
    row = DatasetRow(
        category=req.category,
        source=req.source,
        start=req.start,
        end=req.end,
        params=req.params,
        status="pending",
        error=None,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(row)
    db.flush()

    job = enqueue_job(db, job_type=JOB_TYPE_DATASET_IMPORT, payload={}, dataset_id=row.dataset_id)
    db.commit()

    try:
        dispatch_and_update_job(db, job)
    except Exception as exc:
        row.status = "failed"
        row.error = f"dispatch_failed: {repr(exc)}"
        db.commit()

    return _to_out(row)


@router.get("", response_model=DatasetIndexOut)
def list_datasets(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> DatasetIndexOut:
    stmt = select(DatasetRow).order_by(DatasetRow.created_at.desc()).limit(limit + 1).offset(offset)
    rows = list(db.execute(stmt).scalars().all())
    total = int(db.execute(select(func.count()).select_from(DatasetRow)).scalar_one())
    visible_rows = rows[:limit]
    return DatasetIndexOut(
        items=[_to_out(r) for r in visible_rows],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
        total=total,
    )


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: UUID, db: Session = Depends(get_db)) -> DatasetOut:
    row = db.get(DatasetRow, dataset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return _to_out(row)


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    _user: UserRow = Depends(get_admin_user),
) -> dict[str, str | bool]:
    row = db.get(DatasetRow, dataset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="dataset not found")

    db.delete(row)
    db.commit()

    return {"deleted": True, "dataset_id": str(dataset_id)}
