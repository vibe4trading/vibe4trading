from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fce.api.deps import get_db
from fce.api.schemas import DatasetCreateRequest, DatasetOut
from fce.db.models import DatasetRow
from fce.jobs.repo import enqueue_job
from fce.jobs.types import JOB_TYPE_DATASET_IMPORT

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _now() -> datetime:
    return datetime.now(UTC)


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
def create_dataset(req: DatasetCreateRequest, db: Session = Depends(get_db)) -> DatasetOut:
    if req.end <= req.start:
        raise HTTPException(status_code=400, detail="end must be after start")

    now = _now()
    row = DatasetRow(
        category=req.category,
        source=req.source,
        start=req.start,
        end=req.end,
        params=req.params,
        status="pending",
        error=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()

    enqueue_job(db, job_type=JOB_TYPE_DATASET_IMPORT, payload={}, dataset_id=row.dataset_id)
    db.commit()
    return _to_out(row)


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetOut]:
    rows = list(
        db.execute(select(DatasetRow).order_by(DatasetRow.created_at.desc())).scalars().all()
    )
    return [_to_out(r) for r in rows]


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: UUID, db: Session = Depends(get_db)) -> DatasetOut:
    row = db.get(DatasetRow, dataset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    return _to_out(row)
