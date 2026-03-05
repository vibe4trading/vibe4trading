from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from v4t.contracts.events import (
    EventEnvelopeV1,
    make_event_v1,
    register_payload_upcaster,
    upcast_payload,
)


def test_event_envelope_v1_basic() -> None:
    event = EventEnvelopeV1(
        event_type="test.event",
        source="test",
        observed_at=datetime.now(UTC),
        dedupe_key="test-key",
        payload={"value": 123},
    )
    assert event.event_type == "test.event"
    assert event.source == "test"
    assert event.schema_version == 1


def test_make_event_v1() -> None:
    now = datetime.now(UTC)
    event = make_event_v1(
        event_type="test.event",
        source="test",
        observed_at=now,
        dedupe_key="key-1",
        payload={"data": "value"},
    )
    assert event.event_type == "test.event"
    assert event.observed_at == now


def test_event_with_dataset_id() -> None:
    dataset_id = uuid4()
    event = make_event_v1(
        event_type="test.event",
        source="test",
        observed_at=datetime.now(UTC),
        dedupe_key="key-1",
        payload={},
        dataset_id=dataset_id,
    )
    assert event.dataset_id == dataset_id


def test_upcast_payload_no_change() -> None:
    payload = {"value": 123}
    result, version = upcast_payload(
        event_type="test.event",
        payload=payload,
        schema_version=1,
        target_version=1,
    )
    assert result == payload
    assert version == 1


def test_upcast_payload_with_upcaster() -> None:
    def v1_to_v2(p: dict) -> dict:
        return {**p, "new_field": "added"}

    register_payload_upcaster(event_type="test.event", from_version=1, fn=v1_to_v2)

    payload = {"value": 123}
    result, version = upcast_payload(
        event_type="test.event",
        payload=payload,
        schema_version=1,
        target_version=2,
    )
    assert result["value"] == 123
    assert result["new_field"] == "added"
    assert version == 2


def test_upcast_payload_downcast_fails() -> None:
    with pytest.raises(ValueError, match="Cannot downcast"):
        upcast_payload(
            event_type="test.event",
            payload={},
            schema_version=2,
            target_version=1,
        )
