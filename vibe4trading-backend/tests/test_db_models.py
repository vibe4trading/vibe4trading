from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from v4t.db.models import DatasetRow, EventRow, UserRow


def test_user_row_creates_with_defaults(db_session) -> None:  # noqa: ANN001
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
    )
    db_session.add(user)
    db_session.commit()

    assert user.user_id is not None
    assert user.created_at is not None


def test_user_row_unique_oidc_constraint(db_session) -> None:  # noqa: ANN001
    user1 = UserRow(oidc_issuer="test", oidc_sub="sub1", email="test1@example.com")
    db_session.add(user1)
    db_session.commit()

    user2 = UserRow(oidc_issuer="test", oidc_sub="sub1", email="test2@example.com")
    db_session.add(user2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_event_row_creates_with_required_fields(db_session) -> None:  # noqa: ANN001
    event = EventRow(
        event_type="test.event",
        source="test",
        observed_at=datetime.now(UTC),
        dedupe_key="key1",
        payload={"data": "value"},
    )
    db_session.add(event)
    db_session.commit()

    assert event.event_id is not None
    assert event.ingested_at is not None


def test_event_row_dataset_dedupe_constraint(db_session) -> None:  # noqa: ANN001
    dataset_id = uuid4()
    event1 = EventRow(
        event_type="test.event",
        source="test",
        observed_at=datetime.now(UTC),
        dedupe_key="key1",
        dataset_id=dataset_id,
        payload={},
    )
    db_session.add(event1)
    db_session.commit()

    event2 = EventRow(
        event_type="test.event",
        source="test",
        observed_at=datetime.now(UTC),
        dedupe_key="key1",
        dataset_id=dataset_id,
        payload={},
    )
    db_session.add(event2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_dataset_row_creates_with_defaults(db_session) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    dataset = DatasetRow(
        category="spot",
        source="demo",
        start=now,
        end=now,
        params={},
    )
    db_session.add(dataset)
    db_session.commit()

    assert dataset.dataset_id is not None
    assert dataset.status == "pending"
    assert dataset.created_at is not None
