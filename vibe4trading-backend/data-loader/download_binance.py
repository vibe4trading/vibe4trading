#!/usr/bin/env python3
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)


def download_binance_klines(symbol, start_date, end_date):
    start_ts = int(datetime.fromisoformat(start_date.replace("Z", "+00:00")).timestamp() * 1000)
    end_ts = int(datetime.fromisoformat(end_date.replace("Z", "+00:00")).timestamp() * 1000)

    url = "https://api.binance.com/api/v3/klines"
    all_data = []
    current_ts = start_ts

    while current_ts < end_ts:
        params = {
            "symbol": symbol.replace("/", ""),
            "interval": "1h",
            "startTime": current_ts,
            "endTime": end_ts,
            "limit": 1000,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            all_data.extend(data)
            current_ts = data[-1][0] + 3600000

            if len(data) < 1000:
                break

            time.sleep(0.5)
        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(2)
            continue

    df = pd.DataFrame(
        all_data,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )

    df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms", utc=True)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    df = df[["date", "open", "high", "low", "close", "volume"]]

    return df


event_id = sys.argv[1] if len(sys.argv) > 1 else None

events = config["events"]
if event_id:
    events = [e for e in events if e["id"] == event_id]

for event in events:
    print(f"\n{event['id']}: {event['name']}")

    output_dir = Path(f"./data/{event['id']}/binance")
    output_dir.mkdir(parents=True, exist_ok=True)

    for coin in config["coins"]:
        try:
            print(f"  {coin}...", end=" ", flush=True)

            df = download_binance_klines(coin, event["lookback_start"], event["event_end"])

            pair_file = coin.replace("/", "_")
            feather_path = output_dir / f"{pair_file}-1h.feather"
            df.to_feather(feather_path)

            print(f"✓ {len(df)} rows")
        except Exception as e:
            print(f"✗ {e}")

print("\nDone!")
