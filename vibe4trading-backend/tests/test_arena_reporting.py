from __future__ import annotations

from datetime import UTC, datetime

from v4t.arena.reporting import _event_payload_dict
from v4t.db.models import EventRow


def test_event_payload_dict_handles_invalid_json() -> None:
    class NonSerializable:
        pass

    row = EventRow(
        event_type="test.event",
        observed_at=datetime.now(UTC),
        dedupe_key="test-key",
        payload=NonSerializable(),
    )

    result = _event_payload_dict(row)
    assert result == {}
