#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, cast, String
from sqlalchemy.orm import Session
from v4t.db.models import DatasetRow

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

engine = create_engine("postgresql+psycopg://postgres:postgres@localhost:5433/v4t")

with Session(engine) as db:
    datasets = db.query(DatasetRow).all()

    event_map = {e["id"]: e for e in config["events"]}

    for dataset in datasets:
        event_id = dataset.params.get("event_id")
        if event_id and event_id in event_map:
            event = event_map[event_id]
            updated_params = dict(dataset.params)
            updated_params["scoring_start"] = event["scoring_start"]
            updated_params["scoring_end"] = event["scoring_end"]
            dataset.params = updated_params
            print(
                f"{event_id}: scoring {event['scoring_start'][:10]} to {event['scoring_end'][:10]}"
            )

    db.commit()

print("\nDone!")
