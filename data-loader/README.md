# Data Download and Import Guide

This guide covers downloading market data using Freqtrade and importing it into the Vibe4Trading system.

## Prerequisites

- Python environment with `vibe4trading` conda environment activated
- Freqtrade installed (see Installation section)
- Backend services running (Postgres, Redis)

## Installation

### 1. Install Freqtrade

```bash
# Activate your conda environment
conda activate vibe4trading

# Install freqtrade
pip install freqtrade
```

### 2. Verify Installation

```bash
freqtrade --version
```

## Data Download Process

### Step 1: Download OHLCV Data with Freqtrade

Freqtrade provides a `download-data` command to fetch historical market data from exchanges.

```bash
# Basic download command
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT ETH/USDT \
  --timeframe 1h \
  --days 365 \
  --datadir ./data
```

**Parameters:**
- `--exchange`: Exchange name (binance, kraken, coinbase, etc.)
- `--pairs`: Trading pairs to download (space-separated)
- `--timeframe`: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
- `--days`: Number of days of historical data
- `--datadir`: Output directory for downloaded data

**Example: Download multiple pairs**
```bash
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT ETH/USDT SOL/USDT \
  --timeframe 1h \
  --days 180 \
  --datadir ./market_data
```

### Step 2: Convert JSON to Feather Format

Freqtrade downloads data as JSON by default. The Vibe4Trading system expects Feather format for efficient processing.

```bash
# Convert downloaded data to feather format
freqtrade convert-data \
  --format-from json \
  --format-to feather \
  --datadir ./data \
  --pairs BTC/USDT
```

**Output location:**
- Feather files are saved in: `./data/<exchange>/BTC_USDT-1h.feather`

## Data Import Process

### Step 3: Import Data into Vibe4Trading

Once you have the Feather file, import it into the system using the API.

#### Option A: Using the API Directly

```bash
# Create a dataset with freqtrade source
curl -X POST http://localhost:8000/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "category": "spot",
    "source": "freqtrade",
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z",
    "params": {
      "market_id": "spot:binance:BTC/USDT",
      "feather_path": "/absolute/path/to/data/binance/BTC_USDT-1h.feather"
    }
  }'
```

**Required params:**
- `market_id`: Unique identifier for the market (format: `spot:<exchange>:<pair>`)
- `feather_path`: Absolute path to the feather file

**Response:**
```json
{
  "dataset_id": "uuid-here",
  "status": "pending",
  ...
}
```

#### Option B: Using Python Script

```python
import requests
from datetime import datetime

response = requests.post(
    "http://localhost:8000/api/datasets",
    json={
        "category": "spot",
        "source": "freqtrade",
        "start": datetime(2024, 1, 1).isoformat() + "Z",
        "end": datetime(2024, 12, 31, 23, 59, 59).isoformat() + "Z",
        "params": {
            "market_id": "spot:binance:BTC/USDT",
            "feather_path": "/absolute/path/to/BTC_USDT-1h.feather"
        }
    }
)

dataset = response.json()
print(f"Dataset ID: {dataset['dataset_id']}")
print(f"Status: {dataset['status']}")
```

### Step 4: Monitor Import Status

```bash
# Check dataset status
curl http://localhost:8000/api/datasets/{dataset_id}
```

**Status values:**
- `pending`: Queued for import
- `running`: Currently importing
- `ready`: Import complete, data available
- `failed`: Import failed (check `error` field)

## Complete Example Workflow

### Download and Import BTC/USDT Data

```bash
# 1. Download data from Binance
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT \
  --timeframe 1h \
  --days 365 \
  --datadir ./market_data

# 2. Convert to feather format
freqtrade convert-data \
  --format-from json \
  --format-to feather \
  --datadir ./market_data \
  --pairs BTC/USDT

# 3. Get absolute path
FEATHER_PATH=$(realpath ./market_data/binance/BTC_USDT-1h.feather)
echo "Feather file: $FEATHER_PATH"

# 4. Import into system
curl -X POST http://localhost:8000/api/datasets \
  -H "Content-Type: application/json" \
  -d "{
    \"category\": \"spot\",
    \"source\": \"freqtrade\",
    \"start\": \"2024-01-01T00:00:00Z\",
    \"end\": \"2024-12-31T23:59:59Z\",
    \"params\": {
      \"market_id\": \"spot:binance:BTC/USDT\",
      \"feather_path\": \"$FEATHER_PATH\"
    }
  }"
```

## Troubleshooting

### Common Issues

**1. Feather file not found**
```
ValueError: Feather file not found: /path/to/file.feather
```
- Ensure you use absolute paths, not relative paths
- Verify the file exists: `ls -la /path/to/file.feather`

**2. Import fails with "dataset_id not found"**
- Check that the backend services are running
- Verify database connection in `.env` file

**3. No data in date range**
- Ensure downloaded data covers the `start` and `end` dates in your import request
- Check the feather file contents with pandas:
  ```python
  import pandas as pd
  df = pd.read_feather("path/to/file.feather")
  print(df.head())
  print(f"Date range: {df['date'].min()} to {df['date'].max()}")
  ```

**4. Freqtrade download fails**
- Check exchange API limits (some exchanges require API keys)
- Verify internet connection
- Try a different exchange or fewer pairs

## Data Format Reference

### Feather File Schema

The system expects feather files with these columns:
- `date`: Timestamp (datetime)
- `open`: Opening price (float)
- `high`: Highest price (float)
- `low`: Lowest price (float)
- `close`: Closing price (float)
- `volume`: Trading volume (float)

### Market ID Format

Market IDs follow the pattern: `spot:<exchange>:<pair>`

Examples:
- `spot:binance:BTC/USDT`
- `spot:kraken:ETH/USD`
- `spot:coinbase:SOL/USDT`

## Advanced Usage

### Downloading Multiple Timeframes

```bash
# Download 1h and 4h data
for tf in 1h 4h; do
  freqtrade download-data \
    --exchange binance \
    --pairs BTC/USDT \
    --timeframe $tf \
    --days 365 \
    --datadir ./market_data
  
  freqtrade convert-data \
    --format-from json \
    --format-to feather \
    --datadir ./market_data \
    --pairs BTC/USDT \
    --timeframe $tf
done
```

### Batch Import Script

```python
import requests
from pathlib import Path
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
DATA_DIR = Path("./market_data/binance")

pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

for pair in pairs:
    feather_file = DATA_DIR / f"{pair.replace('/', '_')}-1h.feather"
    
    if not feather_file.exists():
        print(f"Skipping {pair}: file not found")
        continue
    
    response = requests.post(
        f"{BACKEND_URL}/api/datasets",
        json={
            "category": "spot",
            "source": "freqtrade",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-12-31T23:59:59Z",
            "params": {
                "market_id": f"spot:binance:{pair}",
                "feather_path": str(feather_file.absolute())
            }
        }
    )
    
    if response.ok:
        dataset = response.json()
        print(f"✓ {pair}: {dataset['dataset_id']}")
    else:
        print(f"✗ {pair}: {response.status_code} - {response.text}")
```

## See Also

- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- Backend API: `http://localhost:8000/docs`
- Architecture: `ARCHITECTURE.md`
