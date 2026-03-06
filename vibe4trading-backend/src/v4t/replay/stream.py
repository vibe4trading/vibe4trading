from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.db.models import EventRow


def iter_dataset_events(
    session: Session,
    *,
    dataset_ids: list[UUID],
    start: datetime,
    end: datetime,
) -> list[EventRow]:
    """Deterministic ordered event stream for replay.

    Ordering contract: (observed_at, source, event_type, dedupe_key)
    """

    if not dataset_ids:
        return []

    stmt = (
        select(EventRow)
        .where(
            EventRow.dataset_id.in_(dataset_ids),
            EventRow.observed_at >= start,
            EventRow.observed_at <= end,
        )
        .order_by(EventRow.observed_at, EventRow.source, EventRow.event_type, EventRow.dedupe_key)
    )
    return list(session.execute(stmt).scalars().all())
