#!/usr/bin/env python3
"""Test script to create a Freqtrade dataset via API."""

import requests
from pathlib import Path

API_URL = "http://localhost:8000"

feather_file = Path.home() / ".freqtrade/data/binance/BTC_USDT-1h.feather"

payload = {
    "category": "spot",
    "source": "freqtrade",
    "start": "2025-02-21T00:00:00Z",
    "end": "2025-02-28T23:59:59Z",
    "params": {"market_id": "spot:binance:BTC/USDT", "feather_path": str(feather_file)},
}

print(f"Creating dataset from: {feather_file}")
print(f"Payload: {payload}")
print()

response = requests.post(f"{API_URL}/datasets", json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    dataset_id = response.json()["dataset_id"]
    print(f"\n✓ Dataset created: {dataset_id}")
    print(f"\nCheck status: GET {API_URL}/datasets/{dataset_id}")
