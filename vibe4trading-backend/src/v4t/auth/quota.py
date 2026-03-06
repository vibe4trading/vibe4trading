from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from v4t.db.models import UserQuotaRow
from v4t.settings import get_settings


def get_quota_date() -> datetime:
    """Return midnight UTC for today, matching the DateTime column type."""
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _ensure_quota_row(db: Session, *, user_id: UUID, quota_date: datetime, runs_limit: int) -> None:
    row = db.get(UserQuotaRow, (user_id, quota_date))
    if row is not None:
        return

    with db.begin_nested():
        db.add(
            UserQuotaRow(
                user_id=user_id,
                quota_date=quota_date,
                runs_used=0,
                runs_limit=runs_limit,
            )
        )
        try:
            db.flush()
        except IntegrityError:
            pass


def check_quota(db: Session, user_id: UUID) -> tuple[bool, int, int]:
    quota_date = get_quota_date()
    settings = get_settings()

    stmt = select(UserQuotaRow).where(
        UserQuotaRow.user_id == user_id, UserQuotaRow.quota_date == quota_date
    )
    quota_row = db.execute(stmt).scalar_one_or_none()
    if not quota_row:
        return True, 0, settings.daily_run_limit

    has_quota = quota_row.runs_used < quota_row.runs_limit
    return has_quota, quota_row.runs_used, quota_row.runs_limit


def claim_quota(db: Session, user_id: UUID) -> tuple[bool, int, int]:
    quota_date = get_quota_date()
    settings = get_settings()

    _ensure_quota_row(
        db,
        user_id=user_id,
        quota_date=quota_date,
        runs_limit=settings.daily_run_limit,
    )

    stmt = (
        select(UserQuotaRow)
        .where(UserQuotaRow.user_id == user_id, UserQuotaRow.quota_date == quota_date)
        .with_for_update()
    )
    quota_row = db.execute(stmt).scalar_one()
    has_quota = quota_row.runs_used < quota_row.runs_limit
    if not has_quota:
        return False, quota_row.runs_used, quota_row.runs_limit

    quota_row.runs_used += 1
    db.flush()
    return True, quota_row.runs_used, quota_row.runs_limit


def increment_quota(db: Session, user_id: UUID) -> None:
    quota_date = get_quota_date()
    settings = get_settings()

    _ensure_quota_row(
        db,
        user_id=user_id,
        quota_date=quota_date,
        runs_limit=settings.daily_run_limit,
    )

    stmt = (
        select(UserQuotaRow)
        .where(UserQuotaRow.user_id == user_id, UserQuotaRow.quota_date == quota_date)
        .with_for_update()
    )
    quota_row = db.execute(stmt).scalar_one()
    quota_row.runs_used += 1

    db.commit()
