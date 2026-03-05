from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from v4t.contracts.events import make_event_v1
from v4t.db.event_store import append_event
from v4t.db.models import EventRow


def test_append_event_dataset_dedupe_is_idempotent(db_session) -> None:
    ds_id = uuid4()
    t0 = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)

    ev1 = make_event_v1(
        event_type="market.price",
        source="t",
        observed_at=t0,
        event_time=t0,
        dedupe_key="k0",
        dataset_id=ds_id,
        payload={"market_id": "m", "price": "1", "price_type": "mid"},
    )
    ev2 = make_event_v1(
        event_type="market.price",
        source="t2",
        observed_at=t0,
        event_time=t0,
        dedupe_key="k0",
        dataset_id=ds_id,
        payload={"market_id": "m", "price": "1", "price_type": "mid"},
    )

    append_event(db_session, ev=ev1, dedupe_scope="dataset")
    append_event(db_session, ev=ev2, dedupe_scope="dataset")
    db_session.commit()

    cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.dataset_id == ds_id,
            EventRow.event_type == "market.price",
            EventRow.dedupe_key == "k0",
        )
    ).scalar_one()
    assert int(cnt) == 1


def test_append_event_run_dedupe_is_idempotent(db_session) -> None:
    run_id = uuid4()
    t0 = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)

    ev1 = make_event_v1(
        event_type="llm.decision",
        source="t",
        observed_at=t0,
        event_time=t0,
        dedupe_key="tick-0",
        run_id=run_id,
        payload={"tick_time": t0.isoformat(), "market_id": "m", "targets": {}, "accepted": True},
    )
    ev2 = make_event_v1(
        event_type="llm.decision",
        source="t2",
        observed_at=t0,
        event_time=t0,
        dedupe_key="tick-0",
        run_id=run_id,
        payload={"tick_time": t0.isoformat(), "market_id": "m", "targets": {}, "accepted": True},
    )

    append_event(db_session, ev=ev1, dedupe_scope="run")
    append_event(db_session, ev=ev2, dedupe_scope="run")
    db_session.commit()

    cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.run_id == run_id,
            EventRow.event_type == "llm.decision",
            EventRow.dedupe_key == "tick-0",
        )
    ).scalar_one()
    assert int(cnt) == 1


def test_append_event_validates_dedupe_scope_ids(db_session) -> None:
    t0 = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)

    ev_missing_ds = make_event_v1(
        event_type="market.price",
        source="t",
        observed_at=t0,
        dedupe_key="k0",
        payload={"market_id": "m", "price": "1", "price_type": "mid"},
    )
    with pytest.raises(ValueError, match="requires ev.dataset_id"):
        append_event(db_session, ev=ev_missing_ds, dedupe_scope="dataset")

    ev_missing_run = make_event_v1(
        event_type="llm.decision",
        source="t",
        observed_at=t0,
        dedupe_key="k0",
        payload={"tick_time": t0.isoformat(), "market_id": "m", "targets": {}, "accepted": True},
    )
    with pytest.raises(ValueError, match="requires ev.run_id"):
        append_event(db_session, ev=ev_missing_run, dedupe_scope="run")
