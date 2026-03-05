#!/usr/bin/env python3
import json
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, UTC
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from v4t.db.models import DatasetRow

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5433/v4t")

print("Merging and importing datasets (1 per coin per event)...\n")

with Session(engine) as db:
    db.query(DatasetRow).delete()
    db.commit()
    print("Cleared existing datasets\n")

    for event in config["events"]:
        print(f"{event['id']}: {event['name']}")

        all_data = []

        for coin in config["coins"]:
            pair_file = coin.replace("/", "_")
            feather_path = Path(f"./data/{event['id']}/binance/{pair_file}-1h.feather")

            if not feather_path.exists():
                print(f"  ⊘ {coin}: missing")
                continue

            df = pd.read_feather(feather_path)
            df["symbol"] = coin
            df["market_id"] = f"spot:binance:{coin}"
            all_data.append(df)

        merged = pd.concat(all_data, ignore_index=True)
        merged = merged.sort_values(["date", "symbol"])

        output_path = Path(f"./data/{event['id']}/binance/merged-1h.feather")
        merged.to_feather(output_path)

        for coin in config["coins"]:
            market_id = f"spot:binance:{coin}"

            row = DatasetRow(
                dataset_id=uuid4(),
                category="spot",
                source="freqtrade",
                start=datetime.fromisoformat(event["lookback_start"].replace("Z", "+00:00")),
                end=datetime.fromisoformat(event["event_end"].replace("Z", "+00:00")),
                params={
                    "market_id": market_id,
                    "feather_path": str(output_path.absolute()),
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
            print(f"  ✓ {coin}: {row.dataset_id}")

    db.commit()

print("\nDone!")
