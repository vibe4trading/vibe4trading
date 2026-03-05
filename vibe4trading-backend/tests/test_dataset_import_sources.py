from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from v4t.db.models import DatasetRow, EventRow
from v4t.ingest.dataset_import import import_dataset


def test_import_dataset_empty_sentiment_is_allowed(db_session) -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    ds = DatasetRow(
        category="sentiment",
        source="empty",
        start=start,
        end=end,
        params={},
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ds)
    db_session.commit()

    import_dataset(db_session, dataset_id=ds.dataset_id)
    db_session.refresh(ds)
    assert ds.status == "ready"

    cnt = db_session.execute(
        select(func.count()).select_from(EventRow).where(EventRow.dataset_id == ds.dataset_id)
    ).scalar_one()
    assert cnt == 0


def test_import_dataset_dexscreener_can_run_without_network_when_seeded(db_session) -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    ds = DatasetRow(
        category="spot",
        source="dexscreener",
        start=start,
        end=end,
        params={"market_id": "spot:raydium:DEMOPOOL", "base_price": "1.23"},
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ds)
    db_session.commit()

    import_dataset(db_session, dataset_id=ds.dataset_id)
    db_session.refresh(ds)
    assert ds.status == "ready"

    price_cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.dataset_id == ds.dataset_id,
            EventRow.event_type == "market.price",
        )
    ).scalar_one()
    assert price_cnt > 0
