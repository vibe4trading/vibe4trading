from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fce.db.models import EventRow
from fce.replay.stream import iter_dataset_events


def test_replay_ordering(db_session) -> None:
    ds_id = uuid4()
    t1 = datetime(2026, 3, 1, 0, 1, tzinfo=UTC)
    t0 = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)

    # Insert out-of-order.
    db_session.add(
        EventRow(
            event_type="market.price",
            source="t",
            schema_version=1,
            observed_at=t1,
            event_time=t1,
            dedupe_key="k1",
            dataset_id=ds_id,
            run_id=None,
            payload={"market_id": "m", "price": "1", "price_type": "mid"},
            raw_payload=None,
            ingested_at=t1,
        )
    )
    db_session.add(
        EventRow(
            event_type="market.price",
            source="t",
            schema_version=1,
            observed_at=t0,
            event_time=t0,
            dedupe_key="k0",
            dataset_id=ds_id,
            run_id=None,
            payload={"market_id": "m", "price": "1", "price_type": "mid"},
            raw_payload=None,
            ingested_at=t0,
        )
    )
    db_session.commit()

    events = iter_dataset_events(db_session, dataset_ids=[ds_id], start=t0, end=t1)
    assert [e.dedupe_key for e in events] == ["k0", "k1"]
