#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

coins = config["coins"]
events = config["events"]

event_id = sys.argv[1] if len(sys.argv) > 1 else None

if event_id:
    events = [e for e in events if e["id"] == event_id]
    if not events:
        print(f"Event {event_id} not found")
        sys.exit(1)

for event in events:
    lookback = datetime.fromisoformat(event["lookback_start"].replace("Z", "+00:00"))
    event_end = datetime.fromisoformat(event["event_end"].replace("Z", "+00:00"))

    pairs_str = " ".join(coins)

    print(f"Downloading {event['id']}: {event['name']}")
    print(f"Period: {lookback.date()} to {event_end.date()}")

    import subprocess

    result = subprocess.run(
        [
            "freqtrade",
            "download-data",
            "--exchange",
            "binance",
            "--pairs",
            *coins,
            "--timeframe",
            "1h",
            "--timerange",
            f"{lookback.strftime('%Y%m%d')}-{event_end.strftime('%Y%m%d')}",
            "--datadir",
            f"./data/{event['id']}",
        ]
    )

    if result.returncode != 0:
        print(f"Failed to download {event['id']}")
        continue

    print(f"Converting to feather...")
    for pair in coins:
        subprocess.run(
            [
                "freqtrade",
                "convert-data",
                "--format-from",
                "json",
                "--format-to",
                "feather",
                "--datadir",
                f"./data/{event['id']}",
                "--pairs",
                pair,
            ]
        )

    print(f"✓ {event['id']} complete\n")
