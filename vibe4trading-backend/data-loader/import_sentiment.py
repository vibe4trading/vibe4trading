#!/usr/bin/env python3
"""Bulk-import sentiment_raw tweet data into the database.

Creates one sentiment dataset per event (all handles merged), aligned with
the same event windows used by the market data loader.

Usage:
    python import_sentiment.py [--tweets-dir ../../sentiment_raw]
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from v4t.db.models import DatasetRow
from v4t.ingest.dataset_import import import_dataset

events_file = Path(__file__).parent / "events.json"
default_tweets_dir = Path(__file__).parent.parent.parent / "sentiment_raw"

tweets_dir = (
    Path(sys.argv[sys.argv.index("--tweets-dir") + 1])
    if "--tweets-dir" in sys.argv
    else default_tweets_dir
)

if not tweets_dir.is_dir():
    print(f"Error: tweets directory not found: {tweets_dir}")
    sys.exit(1)

with open(events_file) as f:
    config = json.load(f)

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5433/v4t")

print(f"Importing sentiment datasets from: {tweets_dir}\n")

with Session(engine) as db:
    for event in config["events"]:
        lookback_start = datetime.fromisoformat(event["lookback_start"].replace("Z", "+00:00"))
        event_end = datetime.fromisoformat(event["event_end"].replace("Z", "+00:00"))

        row = DatasetRow(
            dataset_id=uuid4(),
            category="sentiment",
            source="tweets",
            start=lookback_start,
            end=event_end,
            params={
                "tweets_dir": str(tweets_dir.absolute()),
                "event_id": event["id"],
                "event_name": event["name"],
                "scoring_start": event["scoring_start"],
                "scoring_end": event["scoring_end"],
            },
            status="pending",
            error=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        db.add(row)
        db.commit()

        print(f"{event['id']}: {event['name']}")
        print(f"  dataset_id: {row.dataset_id}")
        print(f"  range: {lookback_start.isoformat()} -> {event_end.isoformat()}")

        try:
            import_dataset(db, dataset_id=row.dataset_id)
            count = db.execute(
                text("SELECT count(*) FROM events WHERE dataset_id = :did"),
                {"did": str(row.dataset_id)},
            ).scalar()
            print(f"  status: ready ({count} events)")
        except Exception as exc:
            print(f"  status: FAILED - {exc}")

    print("\nAll sentiment dataset IDs:")
    rows = (
        db.query(DatasetRow)
        .filter(DatasetRow.category == "sentiment", DatasetRow.source == "tweets")
        .all()
    )
    for r in rows:
        eid = (r.params or {}).get("event_id", "?")
        print(f"  {eid}: {r.dataset_id}")

print("\nDone!")
