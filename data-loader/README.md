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

## Restoring from a Database Backup

Pre-made backups live in `backups/`. Each backup folder contains:

- `datasets.jsonl` — one JSON object per line, one row per dataset
- `events.jsonl` — one JSON object per line, one row per event
- `arena_dataset_ids.txt` — comma-separated UUIDs of spot datasets used by Arena
- `manifest.json` — metadata (row counts, categories, timestamp)

### Prerequisites

- Postgres running and the `v4t` database created (tables must exist)
- `psql` available on your PATH
- Backend DB connection: `postgresql://postgres:postgres@localhost:5433/v4t`

### Step 1: Pick a backup

```bash
ls backups/
# e.g. db-reset-20260306T170621Z
BACKUP=backups/db-reset-20260306T170621Z
```

### Step 2: Clear existing data (optional)

If you want a clean slate, truncate the tables first:

```sql
psql "postgresql://postgres:postgres@localhost:5433/v4t" -c "
  TRUNCATE events, run_datasets, runs, datasets CASCADE;
"
```

### Step 3: Load datasets

```bash
cat "$BACKUP/datasets.jsonl" | psql "postgresql://postgres:postgres@localhost:5433/v4t" -c "
  CREATE TEMP TABLE _ds (data jsonb);
  COPY _ds(data) FROM STDIN;
  INSERT INTO datasets
    SELECT (data->>'dataset_id')::uuid,
           data->>'category',
           data->>'source',
           (data->>'start')::timestamptz,
           (data->>'end')::timestamptz,
           (data->'params')::jsonb,
           data->>'status',
           data->>'error',
           (data->>'created_at')::timestamptz,
           (data->>'updated_at')::timestamptz
    FROM _ds
  ON CONFLICT DO NOTHING;
"
```

### Step 4: Load events

```bash
cat "$BACKUP/events.jsonl" | psql "postgresql://postgres:postgres@localhost:5433/v4t" -c "
  CREATE TEMP TABLE _ev (data jsonb);
  COPY _ev(data) FROM STDIN;
  INSERT INTO events
    SELECT (data->>'event_id')::uuid,
           data->>'event_type',
           data->>'source',
           (data->>'schema_version')::int,
           (data->>'observed_at')::timestamptz,
           (data->>'event_time')::timestamptz,
           data->>'dedupe_key',
           (data->>'dataset_id')::uuid,
           (data->>'run_id')::uuid,
           (data->'payload')::jsonb,
           (data->'raw_payload')::jsonb,
           (data->>'ingested_at')::timestamptz
    FROM _ev
  ON CONFLICT DO NOTHING;
"
```

### Step 5: Set arena dataset IDs

Copy the contents of `arena_dataset_ids.txt` into your `.env`:

```bash
echo "V4T_ARENA_DATASET_IDS=$(cat $BACKUP/arena_dataset_ids.txt)" >> ../vibe4trading-backend/.env
```

### Step 6: Verify

```bash
psql "postgresql://postgres:postgres@localhost:5433/v4t" -c "
  SELECT category, count(*) FROM datasets GROUP BY category;
  SELECT event_type, count(*) FROM events GROUP BY event_type;
"
```

## See Also

- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- Backend API: `http://localhost:8000/docs`
- Architecture: `ARCHITECTURE.md`
