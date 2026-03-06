#!/usr/bin/env python3
import sys
import requests
from pathlib import Path
from datetime import datetime

BACKEND_URL = "http://localhost:8000"


def import_dataset(feather_path: str, market_id: str, start: str, end: str):
    response = requests.post(
        f"{BACKEND_URL}/datasets",
        json={
            "category": "spot",
            "source": "freqtrade",
            "start": start,
            "end": end,
            "params": {
                "market_id": market_id,
                "feather_path": str(Path(feather_path).absolute()),
            },
        },
    )

    if response.ok:
        dataset = response.json()
        print(f"✓ {market_id}: {dataset['dataset_id']} (status: {dataset['status']})")
        return dataset["dataset_id"]
    else:
        print(f"✗ {market_id}: {response.status_code} - {response.text}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "Usage: python import.py <feather_path> <market_id> <start_date> <end_date>"
        )
        print(
            "Example: python import.py ./data/binance/BTC_USDT-1h.feather spot:binance:BTC/USDT 2024-01-01T00:00:00Z 2024-12-31T23:59:59Z"
        )
        sys.exit(1)

    feather_path = sys.argv[1]
    market_id = sys.argv[2]
    start = sys.argv[3]
    end = sys.argv[4]

    if not Path(feather_path).exists():
        print(f"Error: File not found: {feather_path}")
        sys.exit(1)

    import_dataset(feather_path, market_id, start, end)
