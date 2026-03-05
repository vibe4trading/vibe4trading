#!/bin/bash

EXCHANGE="binance"
TIMEFRAME="1h"

PAIRS=(
  "BTC/USDT"
  "ETH/USDT"
  "SOL/USDT"
  "TRX/USDT"
  "BNB/USDT"
  "DOGE/USDT"
  "PEPE/USDT"
  "XRP/USDT"
  "LINK/USDT"
)

# Time periods (format: YYYYMMDD-YYYYMMDD)
PERIODS=(
  "20250221-20250228"  # W01 Extreme-Down
  "20250307-20250314"  # W02 Medium
  "20250409-20250416"  # W03 Medium
  "20250419-20250426"  # W04 Extreme-Up
  "20250518-20250525"  # W05 Stable
  "20250925-20251002"  # W06 Stable
  "20251010-20251017"  # W07 Extreme-Down
  "20251112-20251119"  # W08 Medium
  "20260109-20260116"  # W09 Stable
  "20260130-20260206"  # W10 Extreme-Down
)

echo "Starting Freqtrade data download..."
echo "Exchange: $EXCHANGE"
echo "Timeframe: $TIMEFRAME"
echo "Pairs: ${PAIRS[@]}"
echo ""

# Download data for each period
for period in "${PERIODS[@]}"; do
  echo "================================================"
  echo "Downloading period: $period"
  echo "================================================"
  
  freqtrade download-data \
    --exchange "$EXCHANGE" \
    --pairs "${PAIRS[@]}" \
    --timerange "$period" \
    --timeframes "$TIMEFRAME"
  
  if [ $? -eq 0 ]; then
    echo "✓ Successfully downloaded $period"
  else
    echo "✗ Failed to download $period"
  fi
  echo ""
done

echo "================================================"
echo "Download complete!"
echo "================================================"
echo ""
echo "Data location: ~/.freqtrade/user_data/data/$EXCHANGE/"
echo ""
echo "To list downloaded data:"
echo "  freqtrade list-data --show-timerange"
echo ""
echo "To convert to JSON:"
echo "  freqtrade convert-data --format-from feather --format-to json --exchange $EXCHANGE"
