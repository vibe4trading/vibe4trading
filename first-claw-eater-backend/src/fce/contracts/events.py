from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

PayloadDict = dict[str, Any]


class EventEnvelopeV1(BaseModel):
    """Canonical event envelope stored in the append-only event log."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    source: str
    schema_version: int = 1

    observed_at: datetime
    event_time: datetime | None = None
    dedupe_key: str

    dataset_id: UUID | None = None
    run_id: UUID | None = None

    payload: dict[str, Any]
    raw_payload: dict[str, Any] | None = None


def make_event_v1(
    *,
    event_type: str,
    source: str,
    observed_at: datetime,
    dedupe_key: str,
    payload: dict[str, Any],
    event_time: datetime | None = None,
    dataset_id: UUID | None = None,
    run_id: UUID | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> EventEnvelopeV1:
    return EventEnvelopeV1(
        event_type=event_type,
        source=source,
        observed_at=observed_at,
        event_time=event_time,
        dedupe_key=dedupe_key,
        dataset_id=dataset_id,
        run_id=run_id,
        payload=payload,
        raw_payload=raw_payload,
    )


# --- Schema versioning scaffolding ---

# Future schema versions can be handled by registering payload upcasters keyed by
# (event_type, from_version). We keep this lightweight for MVP.
_PAYLOAD_UPCASTERS: dict[tuple[str, int], Callable[[PayloadDict], PayloadDict]] = {}


def register_payload_upcaster(
    *, event_type: str, from_version: int, fn: Callable[[PayloadDict], PayloadDict]
) -> None:
    """Register a vN -> vN+1 payload upcaster for a specific event_type."""

    _PAYLOAD_UPCASTERS[(event_type, int(from_version))] = fn


def upcast_payload(
    *, event_type: str, payload: PayloadDict, schema_version: int, target_version: int
) -> tuple[PayloadDict, int]:
    """Upcast an event payload to target_version.

    Returns (payload, new_schema_version). If no upcast is required, returns the
    input payload and schema_version.
    """

    v = int(schema_version)
    target = int(target_version)
    if v > target:
        raise ValueError(f"Cannot downcast payload for {event_type}: v{v} -> v{target}")

    out = dict(payload)
    while v < target:
        fn = _PAYLOAD_UPCASTERS.get((event_type, v))
        if fn is None:
            raise ValueError(f"Missing upcaster for {event_type}: v{v} -> v{v + 1}")
        out = fn(out)
        v += 1

    return out, v
