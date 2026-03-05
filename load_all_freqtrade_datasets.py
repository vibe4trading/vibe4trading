#!/usr/bin/env python3
"""Clear all datasets and load Freqtrade data for all pairs."""

import requests
from pathlib import Path

API_URL = "http://localhost:8000"
FREQTRADE_DATA_DIR = Path.home() / ".freqtrade/data/binance"

PAIRS = [
    ("BTC/USDT", "BTC_USDT-1h.feather"),
    ("ETH/USDT", "ETH_USDT-1h.feather"),
    ("SOL/USDT", "SOL_USDT-1h.feather"),
    ("TRX/USDT", "TRX_USDT-1h.feather"),
    ("BNB/USDT", "BNB_USDT-1h.feather"),
    ("DOGE/USDT", "DOGE_USDT-1h.feather"),
    ("PEPE/USDT", "PEPE_USDT-1h.feather"),
    ("ADA/USDT", "ADA_USDT-1h.feather"),
    ("XRP/USDT", "XRP_USDT-1h.feather"),
    ("LINK/USDT", "LINK_USDT-1h.feather"),
]

START = "2025-02-21T00:00:00Z"
END = "2026-03-02T23:59:59Z"

print("=" * 60)
print("Step 1: Deleting all existing datasets...")
print("=" * 60)

response = requests.get(f"{API_URL}/datasets")
if response.status_code == 200:
    datasets = response.json()
    print(f"Found {len(datasets)} existing datasets")

    for ds in datasets:
        dataset_id = ds["dataset_id"]
        print(f"Deleting {dataset_id}...", end=" ")
        del_response = requests.delete(f"{API_URL}/datasets/{dataset_id}")
        if del_response.status_code == 200:
            print("✓")
        else:
            print(f"✗ ({del_response.status_code})")
else:
    print(f"Failed to list datasets: {response.status_code}")

print()
print("=" * 60)
print("Step 2: Loading Freqtrade datasets...")
print("=" * 60)

created_datasets = []

for pair_name, filename in PAIRS:
    feather_path = FREQTRADE_DATA_DIR / filename

    if not feather_path.exists():
        print(f"✗ {pair_name}: File not found - {feather_path}")
        continue

    payload = {
        "category": "spot",
        "source": "freqtrade",
        "start": START,
        "end": END,
        "params": {
            "market_id": f"spot:binance:{pair_name}",
            "feather_path": str(feather_path),
        },
    }

    print(f"Creating dataset for {pair_name}...", end=" ")
    response = requests.post(f"{API_URL}/datasets", json=payload)

    if response.status_code == 200:
        dataset_id = response.json()["dataset_id"]
        created_datasets.append((pair_name, dataset_id))
        print(f"✓ {dataset_id}")
    else:
        print(f"✗ ({response.status_code})")
        print(f"   Error: {response.text}")

print()
print("=" * 60)
print("Summary")
print("=" * 60)
print(f"Created {len(created_datasets)} datasets:")
for pair_name, dataset_id in created_datasets:
    print(f"  {pair_name}: {dataset_id}")
