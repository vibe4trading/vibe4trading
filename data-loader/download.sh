#!/bin/bash
# Download market data using Freqtrade

set -e

EXCHANGE=${1:-binance}
PAIRS=${2:-"BTC/USDT ETH/USDT"}
TIMEFRAME=${3:-1h}
DAYS=${4:-365}
DATADIR=${5:-./data}

echo "Downloading data from $EXCHANGE..."
echo "Pairs: $PAIRS"
echo "Timeframe: $TIMEFRAME"
echo "Days: $DAYS"

freqtrade download-data \
  --exchange "$EXCHANGE" \
  --pairs $PAIRS \
  --timeframe "$TIMEFRAME" \
  --days "$DAYS" \
  --datadir "$DATADIR"

echo ""
echo "Converting to feather format..."

for pair in $PAIRS; do
  freqtrade convert-data \
    --format-from json \
    --format-to feather \
    --datadir "$DATADIR" \
    --pairs "$pair"
  
  pair_file=$(echo "$pair" | tr '/' '_')
  feather_path="$DATADIR/$EXCHANGE/${pair_file}-${TIMEFRAME}.feather"
  
  if [ -f "$feather_path" ]; then
    echo "✓ $pair -> $feather_path"
  else
    echo "✗ $pair conversion failed"
  fi
done

echo ""
echo "Done! Files saved in: $DATADIR/$EXCHANGE/"
