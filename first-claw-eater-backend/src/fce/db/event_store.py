from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from fce.contracts.events import EventEnvelopeV1
from fce.db.models import EventRow


def _now() -> datetime:
    return datetime.now(UTC)


def append_event(session: Session, *, ev: EventEnvelopeV1, dedupe_scope: str) -> None:
    """Append an event to the DB event log with idempotent dedupe.

    dedupe_scope:
      - "dataset" => (dataset_id, event_type, dedupe_key)
      - "run"     => (run_id, event_type, dedupe_key)
    """

    if dedupe_scope not in {"dataset", "run"}:
        raise ValueError(f"Unknown dedupe_scope={dedupe_scope}")

    if dedupe_scope == "dataset" and ev.dataset_id is None:
        raise ValueError("dedupe_scope='dataset' requires ev.dataset_id")
    if dedupe_scope == "run" and ev.run_id is None:
        raise ValueError("dedupe_scope='run' requires ev.run_id")

    values = {
        "event_id": ev.event_id,
        "event_type": ev.event_type,
        "source": ev.source,
        "schema_version": ev.schema_version,
        "observed_at": ev.observed_at,
        "event_time": ev.event_time,
        "dedupe_key": ev.dedupe_key,
        "dataset_id": ev.dataset_id,
        "run_id": ev.run_id,
        "payload": ev.payload,
        "raw_payload": ev.raw_payload,
        "ingested_at": _now(),
    }

    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        if dedupe_scope == "dataset":
            stmt = (
                pg_insert(EventRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["dataset_id", "event_type", "dedupe_key"])
            )
        else:
            stmt = (
                pg_insert(EventRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["run_id", "event_type", "dedupe_key"])
            )
    elif dialect == "sqlite":
        if dedupe_scope == "dataset":
            stmt = (
                sqlite_insert(EventRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["dataset_id", "event_type", "dedupe_key"])
            )
        else:
            stmt = (
                sqlite_insert(EventRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["run_id", "event_type", "dedupe_key"])
            )
    else:
        stmt = insert(EventRow).values(**values)

    session.execute(stmt)
