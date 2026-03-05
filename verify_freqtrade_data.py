#!/usr/bin/env python3
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed. Run: pip install pandas pyarrow")
    sys.exit(1)

FREQTRADE_DATA_DIR = Path.home() / ".freqtrade/data/binance"
PAIRS = [
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "TRX_USDT",
    "BNB_USDT",
    "DOGE_USDT",
    "PEPE_USDT",
    "XRP_USDT",
    "LINK_USDT",
]
TIMEFRAME = "1h"

EXPECTED_PERIODS = [
    ("2025-02-21", "2025-02-28", "W01 Extreme-Down"),
    ("2025-03-07", "2025-03-14", "W02 Medium"),
    ("2025-04-09", "2025-04-16", "W03 Medium"),
    ("2025-04-19", "2025-04-26", "W04 Extreme-Up"),
    ("2025-05-18", "2025-05-25", "W05 Stable"),
    ("2025-09-25", "2025-10-02", "W06 Stable"),
    ("2025-10-10", "2025-10-17", "W07 Extreme-Down"),
    ("2025-11-12", "2025-11-19", "W08 Medium"),
    ("2026-01-09", "2026-01-16", "W09 Stable"),
    ("2026-01-30", "2026-02-06", "W10 Extreme-Down"),
]


def check_pair_data(pair: str) -> dict:
    filename = f"{pair}-{TIMEFRAME}.feather"
    filepath = FREQTRADE_DATA_DIR / filename

    if not filepath.exists():
        return {"status": "missing", "file": filename}

    try:
        df = pd.read_feather(filepath)
    except Exception as e:
        return {"status": "error", "file": filename, "error": str(e)}

    if df.empty:
        return {"status": "empty", "file": filename}

    df["date"] = pd.to_datetime(df["date"])
    min_date = df["date"].min().strftime("%Y-%m-%d")
    max_date = df["date"].max().strftime("%Y-%m-%d")
    total_rows = len(df)

    covered_periods = []
    for start, end, label in EXPECTED_PERIODS:
        period_data = df[(df["date"] >= start) & (df["date"] <= end)]
        if len(period_data) > 0:
            covered_periods.append(label)

    return {
        "status": "ok",
        "file": filename,
        "min_date": min_date,
        "max_date": max_date,
        "total_rows": total_rows,
        "covered_periods": covered_periods,
        "missing_periods": len(EXPECTED_PERIODS) - len(covered_periods),
    }


print("Checking Freqtrade downloaded data...")
print(f"Data directory: {FREQTRADE_DATA_DIR}")
print()

all_ok = True
for pair in PAIRS:
    result = check_pair_data(pair)
    status = result["status"]

    if status == "ok":
        print(
            f"✓ {pair}: {result['min_date']} -> {result['max_date']} ({result['total_rows']} rows)"
        )
        print(f"  Covered: {len(result['covered_periods'])}/10 periods")
        if result["missing_periods"] > 0:
            print(f"  ⚠ Missing {result['missing_periods']} periods")
            all_ok = False
    elif status == "missing":
        print(f"✗ {pair}: File not found")
        all_ok = False
    elif status == "empty":
        print(f"✗ {pair}: File is empty")
        all_ok = False
    else:
        print(f"✗ {pair}: Error - {result.get('error', 'unknown')}")
        all_ok = False
    print()

if all_ok:
    print("✓ All data downloaded and merged successfully!")
else:
    print("⚠ Some data is missing or incomplete")
