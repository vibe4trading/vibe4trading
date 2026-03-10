from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.auth.deps import get_admin_user
from v4t.db.models import (
    ArenaSubmissionRow,
    ArenaSubmissionRunRow,
    EventRow,
    JobRow,
    LlmCallRow,
    PortfolioSnapshotRow,
    RunConfigSnapshotRow,
    RunDatasetRow,
    RunRow,
    UserRow,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/admin/arena", tags=["admin-arena"])


@router.delete("/submissions/{submission_id}")
def delete_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> dict[str, bool | str]:
    row = db.get(ArenaSubmissionRow, submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="submission not found")

    if row.status == "running":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a running submission. Stop it first.",
        )

    # Collect run_ids + config_ids upfront — deletion order matters (RESTRICT FK on config_id)
    link_rows = list(
        db.execute(
            select(ArenaSubmissionRunRow).where(
                ArenaSubmissionRunRow.submission_id == submission_id
            )
        )
        .scalars()
        .all()
    )
    run_ids = [lr.run_id for lr in link_rows]

    config_ids: list[UUID] = []
    if run_ids:
        config_ids = [
            cid
            for (cid,) in db.execute(
                select(RunRow.config_id).where(RunRow.run_id.in_(run_ids))
            ).all()
        ]

    logger.info(
        "admin_delete_submission",
        submission_id=str(submission_id),
        run_count=len(run_ids),
        config_count=len(config_ids),
    )

    if run_ids:
        db.execute(delete(EventRow).where(EventRow.run_id.in_(run_ids)))
        db.execute(delete(LlmCallRow).where(LlmCallRow.run_id.in_(run_ids)))
        db.execute(delete(JobRow).where(JobRow.run_id.in_(run_ids)))
        db.execute(delete(PortfolioSnapshotRow).where(PortfolioSnapshotRow.run_id.in_(run_ids)))
        db.execute(delete(RunDatasetRow).where(RunDatasetRow.run_id.in_(run_ids)))

    db.execute(
        delete(ArenaSubmissionRunRow).where(ArenaSubmissionRunRow.submission_id == submission_id)
    )

    if run_ids:
        db.execute(delete(RunRow).where(RunRow.run_id.in_(run_ids)))

    if config_ids:
        db.execute(
            delete(RunConfigSnapshotRow).where(RunConfigSnapshotRow.config_id.in_(config_ids))
        )

    # Job payload stores submission_id as JSON, not a FK — must match manually
    sub_jobs = list(
        db.execute(
            select(JobRow).where(
                JobRow.job_type == "arena_execute_submission",
                JobRow.run_id.is_(None),
            )
        )
        .scalars()
        .all()
    )
    for j in sub_jobs:
        if j.payload.get("submission_id") == str(submission_id):
            db.delete(j)

    db.delete(row)
    db.commit()

    return {"deleted": True, "submission_id": str(submission_id)}
