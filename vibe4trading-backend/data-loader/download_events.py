#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

coins = config["coins"]
events = config["events"]

print("Historical Event Backtesting - Data Download Plan")
print("=" * 60)
print(f"\nCoins: {len(coins)}")
for coin in coins:
    print(f"  - {coin}")

print(f"\nEvents: {len(events)}")
for event in events:
    print(f"\n{event['id']}: {event['name']}")
    print(f"  Period: {event['lookback_start'][:10]} to {event['event_end'][:10]}")
    print(f"  Difficulty: {event['difficulty']}")
    print(f"  Change: {event['start_end_change']:+.2f}%")

print("\n" + "=" * 60)
print("Download Commands:")
print("=" * 60)

for event in events:
    lookback = datetime.fromisoformat(event["lookback_start"].replace("Z", "+00:00"))
    event_end = datetime.fromisoformat(event["event_end"].replace("Z", "+00:00"))

    days = (event_end - lookback).days + 1

    pairs_str = " ".join(coins)

    print(f"\n# {event['id']}: {event['name']}")
    print("freqtrade download-data \\")
    print("  --exchange binance \\")
    print(f"  --pairs {pairs_str} \\")
    print("  --timeframe 1h \\")
    print(f"  --timerange {lookback.strftime('%Y%m%d')}-{event_end.strftime('%Y%m%d')} \\")
    print(f"  --datadir ./data/{event['id']}")
