#!/usr/bin/env python3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

event = config["events"][0]

print(f"Testing merge for {event['id']}: {event['name']}")
print(f"Expected period: {event['lookback_start']} to {event['event_end']}")
print()

all_data = []

for coin in config["coins"]:
    pair_file = coin.replace("/", "_")
    feather_path = Path(f"./data/{event['id']}/binance/{pair_file}-1h.feather")

    if not feather_path.exists():
        print(f"Missing: {coin}")
        continue

    df = pd.read_feather(feather_path)
    df["symbol"] = coin
    df["market_id"] = f"spot:binance:{coin}"

    print(f"{coin}: {len(df)} rows, {df['date'].min()} to {df['date'].max()}")
    all_data.append(df)

merged = pd.concat(all_data, ignore_index=True)
merged = merged.sort_values(["date", "symbol"])

print(f"\nMerged: {len(merged)} total rows")
print(f"Date range: {merged['date'].min()} to {merged['date'].max()}")
print(f"Symbols: {merged['symbol'].nunique()}")
print(f"\nColumns: {list(merged.columns)}")

expected_start = datetime.fromisoformat(event["lookback_start"].replace("Z", "+00:00"))
expected_end = datetime.fromisoformat(event["event_end"].replace("Z", "+00:00"))

actual_start = merged["date"].min().to_pydatetime()
actual_end = merged["date"].max().to_pydatetime()

print(f"\nValidation:")
print(f"  Expected: {expected_start} to {expected_end}")
print(f"  Actual:   {actual_start} to {actual_end}")
print(f"  Match: {actual_start <= expected_start and actual_end >= expected_end}")

output_path = Path(f"./data/{event['id']}/binance/merged-1h.feather")
merged.to_feather(output_path)
print(f"\nSaved to: {output_path}")
print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
