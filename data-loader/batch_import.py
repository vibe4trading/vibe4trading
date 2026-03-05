#!/usr/bin/env python3
import sys
import requests
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
DATA_DIR = Path("./data/binance")

pairs = [
    ("BTC/USDT", "spot:binance:BTC/USDT"),
    ("ETH/USDT", "spot:binance:ETH/USDT"),
    ("SOL/USDT", "spot:binance:SOL/USDT"),
]

start = "2024-01-01T00:00:00Z"
end = "2024-12-31T23:59:59Z"
timeframe = "1h"

for pair, market_id in pairs:
    feather_file = DATA_DIR / f"{pair.replace('/', '_')}-{timeframe}.feather"

    if not feather_file.exists():
        print(f"⊘ {pair}: file not found")
        continue

    response = requests.post(
        f"{BACKEND_URL}/api/datasets",
        json={
            "category": "spot",
            "source": "freqtrade",
            "start": start,
            "end": end,
            "params": {"market_id": market_id, "feather_path": str(feather_file.absolute())},
        },
    )

    if response.ok:
        dataset = response.json()
        print(f"✓ {pair}: {dataset['dataset_id']}")
    else:
        print(f"✗ {pair}: {response.status_code}")
