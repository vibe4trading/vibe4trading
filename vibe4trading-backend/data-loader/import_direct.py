#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime, UTC
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from v4t.db.models import DatasetRow

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5433/v4t")

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

with Session(engine) as db:
    for event in config["events"]:
        print(f"\n{event['id']}: {event['name']}")

        for coin in config["coins"]:
            pair_file = coin.replace("/", "_")
            feather_path = Path(f"./data/{event['id']}/binance/{pair_file}-1h.feather").absolute()

            if not feather_path.exists():
                print(f"  ⊘ {coin}: file not found")
                continue

            market_id = f"spot:binance:{coin}"
            relative_path = f"data/{event['id']}/binance/{pair_file}-1h.feather"

            row = DatasetRow(
                dataset_id=uuid4(),
                category="spot",
                source="freqtrade",
                start=datetime.fromisoformat(event["lookback_start"].replace("Z", "+00:00")),
                end=datetime.fromisoformat(event["event_end"].replace("Z", "+00:00")),
                params={
                    "market_id": market_id,
                    "feather_path": relative_path,
                    "event_id": event["id"],
                    "event_name": event["name"],
                },
                status="pending",
                error=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            db.add(row)
            print(f"  ✓ {coin}: {row.dataset_id}")

    db.commit()

print("\nDone!")
