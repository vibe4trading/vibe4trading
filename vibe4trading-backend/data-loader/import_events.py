#!/usr/bin/env python3
import json
import requests
from pathlib import Path

events_file = Path(__file__).parent / "events.json"
BACKEND_URL = "http://localhost:8000"

with open(events_file) as f:
    config = json.load(f)

coins = config["coins"]
events = config["events"]

print("Importing event datasets...")

for event in events:
    print(f"\n{event['id']}: {event['name']}")

    for coin in coins:
        pair_file = coin.replace("/", "_")
        feather_path = Path(f"./data/{event['id']}/binance/{pair_file}-1h.feather").absolute()

        if not feather_path.exists():
            print(f"  ⊘ {coin}: file not found")
            continue

        market_id = f"spot:binance:{coin}"

        response = requests.post(
            f"{BACKEND_URL}/api/datasets",
            json={
                "category": "spot",
                "source": "freqtrade",
                "start": event["lookback_start"],
                "end": event["event_end"],
                "params": {
                    "market_id": market_id,
                    "feather_path": str(feather_path),
                    "event_id": event["id"],
                    "event_name": event["name"],
                },
            },
        )

        if response.ok:
            dataset = response.json()
            print(f"  ✓ {coin}: {dataset['dataset_id']}")
        else:
            print(f"  ✗ {coin}: {response.status_code}")
