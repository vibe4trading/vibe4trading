#!/usr/bin/env python3
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import ccxt
import pandas as pd

events_file = Path(__file__).parent / "events.json"

with open(events_file) as f:
    config = json.load(f)

exchange = ccxt.binance()


def download_ohlcv(symbol, start_date, end_date):
    start_ts = int(datetime.fromisoformat(start_date.replace("Z", "+00:00")).timestamp() * 1000)
    end_ts = int(datetime.fromisoformat(end_date.replace("Z", "+00:00")).timestamp() * 1000)

    all_ohlcv = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, "1h", since=current_ts, limit=1000)
            if not ohlcv:
                break

            all_ohlcv.extend(ohlcv)
            current_ts = ohlcv[-1][0] + 3600000

            if len(ohlcv) < 1000:
                break

            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)
            continue

    all_ohlcv = [o for o in all_ohlcv if start_ts <= o[0] <= end_ts]

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df[["date", "open", "high", "low", "close", "volume"]]

    return df


event_id = None

if len(sys.argv) > 1:
    event_id = sys.argv[1]

events = config["events"]
if event_id:
    events = [e for e in events if e["id"] == event_id]

for event in events:
    print(f"\n{event['id']}: {event['name']}")

    output_dir = Path(f"./data/{event['id']}/binance")
    output_dir.mkdir(parents=True, exist_ok=True)

    for coin in config["coins"]:
        try:
            print(f"  Downloading {coin}...", end=" ", flush=True)

            df = download_ohlcv(coin, event["lookback_start"], event["event_end"])

            pair_file = coin.replace("/", "_")
            feather_path = output_dir / f"{pair_file}-1h.feather"
            df.to_feather(feather_path)

            print(f"✓ ({len(df)} rows)")
        except Exception as e:
            print(f"✗ {e}")

print("\nDone!")
