from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.db.models import UserQuotaRow
from v4t.settings import get_settings


def get_quota_date() -> datetime:
    """Return midnight UTC for today, matching the DateTime column type."""
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def check_quota(db: Session, user_id: UUID) -> tuple[bool, int, int]:
    quota_date = get_quota_date()
    settings = get_settings()

    stmt = (
        select(UserQuotaRow)
        .where(UserQuotaRow.user_id == user_id, UserQuotaRow.quota_date == quota_date)
        .with_for_update()
    )
    quota_row = db.execute(stmt).scalar_one_or_none()

    if not quota_row:
        quota_row = UserQuotaRow(
            user_id=user_id, quota_date=quota_date, runs_used=0, runs_limit=settings.daily_run_limit
        )
        db.add(quota_row)
        db.commit()
        db.refresh(quota_row)

    has_quota = quota_row.runs_used < quota_row.runs_limit
    return has_quota, quota_row.runs_used, quota_row.runs_limit


def increment_quota(db: Session, user_id: UUID) -> None:
    quota_date = get_quota_date()
    settings = get_settings()

    stmt = (
        select(UserQuotaRow)
        .where(UserQuotaRow.user_id == user_id, UserQuotaRow.quota_date == quota_date)
        .with_for_update()
    )
    quota_row = db.execute(stmt).scalar_one_or_none()

    if not quota_row:
        quota_row = UserQuotaRow(
            user_id=user_id, quota_date=quota_date, runs_used=1, runs_limit=settings.daily_run_limit
        )
        db.add(quota_row)
    else:
        quota_row.runs_used += 1

    db.commit()
