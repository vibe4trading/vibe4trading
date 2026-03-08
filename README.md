# Vibe4Trading

**LLM-native crypto strategy benchmarking platform.**

### [Try it live at vibe4trading.ai](https://vibe4trading.ai)

Test AI trading strategies across repeatable historical market regimes before trusting them with real capital. Pick a model, a prompt, and a market — the platform replays that strategy across fixed historical windows, aggregates results, and ranks performance on a leaderboard.

> *"Is this AI trading strategy actually good, or did it just get lucky in one market window?"*

---

## Architecture

Modular monolith — one Python codebase deployed as multiple cooperating processes. Celery + Redis handles job dispatch; PostgreSQL is the system of record for everything. The LLM gateway routes decision calls to the user's chosen model, while arena report generation and run summaries are handled by **GLM-5** — selected for its strong creative writing and evaluative judging capabilities.

```
                          ┌──────────────────────┐
                          │       Browser         │
                          └──────────┬───────────┘
                                     │
                          ┌──────────┴───────────┐
                          │   Vite + React SPA    │
                          │  (React Router, TW4)  │
                          │                       │
                          │  /arena  /leaderboard │
                          │  /runs   /live  /admin│
                          └──────────┬───────────┘
                                     │ REST + WebSocket + SSE
                          ┌──────────┴───────────┐
                          │   FastAPI API Server  │
                          │                       │
                          │  • Auth (OIDC / JWT)  │
                          │  • Run / Dataset CRUD │
                          │  • Job dispatch       │
                          │  • Streaming reads    │
                          └──────┬────────┬──────┘
                                 │        │
                    ┌────────────┘        └────────────┐
                    │                                  │
             ┌──────┴──────┐                    ┌──────┴──────┐
             │  PostgreSQL │                    │    Redis     │
             │    (v16)    │                    │    (v7)      │
             │             │                    │              │
             │ • Events    │                    │ Celery broker│
             │ • Runs      │                    │ + result     │
             │ • Datasets  │                    │   backend    │
             │ • LLM calls │                    └──────┬──────┘
             │ • Portfolios│                           │
             │ • Arena     │              ┌────────────┼────────────┐
             └──────┬──────┘              │            │            │
                    │              ┌──────┴──┐  ┌──────┴──┐  ┌─────┴────┐
                    │              │ Worker  │  │ Worker  │  │  Beat    │
                    │              │(default)│  │ (live)  │  │ Schedul. │
                    │              │         │  │         │  │          │
                    │              │• Replay │  │• Live   │  │• Stale   │
                    │              │  runs   │  │  run    │  │  job     │
                    │              │• Arena  │  │  loop   │  │  recov.  │
                    │              │• Import │  │         │  │          │
                    │              └────┬────┘  └────┬────┘  └──────────┘
                    │                   └──────┬─────┘
                    │                          │
                    │                   ┌──────┴──────┐
                    │                   │ Orchestrator │
                    │                   │              │
                    │                   │• Snapshot    │
                    │                   │  builder     │
                    │                   │• Prompt      │
                    │                   │  builder     │
                    │                   │• Guard chain │
                    │                   │• Simulator   │
                    │                   └──────┬──────┘
                    │                          │
                    │                   ┌──────┴──────┐
                    │                   │ LLM Gateway  │
                    │                   │              │
                    │                   │• OpenAI API  │
                    │                   │• Retries     │
                    │                   │• Budgets     │
                    │                   │• Audit log   │
                    │                   └──────┬──────┘
                    │                          │
                    │              ┌────────────┴────────────┐
                    │              │                         │
                    │       ┌──────┴──────┐          ┌──────┴──────┐
                    │       │  Decision   │          │  Report /   │
                    │       │  Models     │          │  Summary    │
                    │       │             │          │             │
                    │       │ (per-run    │          │  GLM-5      │
                    │       │  model_key) │          │ (creative   │
                    │       │             │          │  writing +  │
                    │       │             │          │  judging)   │
                    │       └─────────────┘          └─────────────┘
                    │
             ┌──────┴──────────────────┐
             │     Data Ingestion      │
             │                         │
             │  ┌──────────┐ ┌───────┐ │
             │  │Freqtrade │ │Tweets/│ │
             │  │ Feather  │ │Sentim.│ │
             │  │ (OHLCV)  │ │Import │ │
             │  └──────────┘ └───────┘ │
             └─────────────────────────┘
```

---

## Product Surfaces

### Benchmark Lab

Create replay runs: pick a coin, an LLM model, and a prompt. The engine replays historical market data tick-by-tick, calls the model at each interval, validates decisions, simulates paper trades, and produces equity curves, decision feeds, and AI-generated summaries.

### Strategy Arena

Submit a single strategy configuration. The platform expands it across 10 fixed historical scenario windows (bull runs, crashes, consolidation, narrative-driven events), executes each as an independent replay run, and aggregates results into a benchmark report with composite scoring.

### Leaderboard

Rank arena submissions by total return, Sharpe ratio, max drawdown, win rate, profit factor, and trade count. Filter by model and market. Public by default — prompt text stays private.

### Live Mode

Backend-ready paper-trading engine with real-time price ingestion. Dedicated Celery queue for long-running live jobs. Frontend dashboard is a styled placeholder pending full telemetry buildout.

### Admin / Model Governance

Model registry with enable/disable controls, per-user model access overrides, and environment-defined defaults. Admin access controlled via OIDC group claims or email allowlist.

---

## Repository Structure

```
vibe4trading/
├── vibe4trading-backend/          # Python — FastAPI + Celery modular monolith
│   ├── src/v4t/
│   │   ├── api/                   # FastAPI routers + request schemas
│   │   │   └── routes/            # me, runs, datasets, arena, live, admin
│   │   ├── arena/                 # Tournament expansion + reporting
│   │   ├── auth/                  # OIDC/JWT validation + session cookies
│   │   ├── benchmark/             # Benchmark spec + scenario definitions
│   │   ├── contracts/             # Pydantic models (IDs, events, configs)
│   │   ├── db/                    # SQLAlchemy models + event store + engine
│   │   ├── ingest/                # Dataset import (Freqtrade feather, tweets)
│   │   ├── jobs/                  # Job type registry + handler dispatch
│   │   ├── llm/                   # LLM gateway, budgets, retries, concurrency
│   │   ├── observability/         # Structured logging helpers
│   │   ├── orchestrator/          # Replay + live execution engines
│   │   ├── replay/                # Deterministic event stream from DB
│   │   ├── sim/                   # Rebalance engine + guard chain + P&L
│   │   ├── utils/                 # Shared utilities
│   │   ├── worker/                # Celery app, tasks, Beat schedule
│   │   └── settings.py            # All V4T_ env config (pydantic-settings)
│   ├── tests/                     # pytest suite (unit, API, worker, e2e)
│   ├── scripts/                   # Admin/dev utilities
│   ├── infra/compose/             # docker-compose.yml
│   ├── pyproject.toml
│   └── ARCHITECTURE.md
│
├── vibe4trading-frontend/         # TypeScript — Vite + React SPA
│   ├── src/
│   │   ├── app/                   # Route pages + components
│   │   │   ├── arena/             # Arena submission views
│   │   │   ├── leaderboard/       # Leaderboard ranking page
│   │   │   ├── runs/              # Run list, detail, watch mode
│   │   │   ├── live/              # Live trading view
│   │   │   ├── admin/             # Model management
│   │   │   ├── components/        # Shared UI components
│   │   │   ├── hooks/             # Custom React hooks
│   │   │   └── lib/               # API client, realtime helpers
│   │   ├── auth.tsx               # Auth context
│   │   └── types/                 # TypeScript type definitions
│   ├── e2e/                       # Playwright E2E tests
│   ├── tests/                     # Vitest unit tests
│   └── package.json
│
├── vibe4trading-crawler/          # Placeholder — future vendor adapter extraction
├── data-loader/                   # Freqtrade download + import guide
├── VIBE4TRADING_PRODUCT_ARCH_STACK.md
├── CRYPTO_BENCHMARK_SPEC.md
└── ideas.md                       # Original design decisions + contracts
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Vite, React 19, React Router 7, TypeScript, Tailwind CSS 4, Vitest, Playwright |
| **Backend** | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Celery + Redis, structlog, httpx, tenacity |
| **LLM** | OpenAI-compatible providers (OpenRouter, etc.), budget controls, concurrency limits, full audit trail |
| **Database** | PostgreSQL 16 (append-only event store + relational metadata + projection tables) |
| **Broker** | Redis 7 (Celery broker + result backend) |
| **Auth** | Authentik OIDC, JWT validation via JWKS, httpOnly session cookies, backend-issued API tokens |
| **Quality** | Ruff + Pyright (backend), ESLint (frontend), pytest, Vitest, Playwright |
| **Infra** | Docker Compose, uv (Python), pnpm (frontend) |

---

## Getting Started

### Prerequisites

- Docker + Docker Compose
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with pnpm
- (Optional) An OpenAI-compatible LLM API key — without one, the backend uses a deterministic stub model

### 1. Clone

```bash
git clone <repo-url> vibe4trading
cd vibe4trading
```

### 2. Backend Setup

```bash
cd vibe4trading-backend

# Copy and configure environment
cp .env.example .env
# Edit .env — set V4T_LLM_BASE_URL and V4T_LLM_API_KEY for real LLM calls
```

#### Option A: Docker Compose (recommended)

Starts PostgreSQL, Redis, API server, default worker, live worker, and Beat scheduler:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

The API is available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

#### Option B: Manual (for development)

```bash
uv sync

# Terminal 1: API server
uv run uvicorn v4t.api.app:app --reload --port 8000

# Terminal 2: Default worker (replay runs, arena, dataset imports)
uv run celery -A v4t.worker.celery_app:celery_app worker --loglevel=info --queues=default --concurrency=2

# Terminal 3: Live worker (long-running live jobs)
uv run celery -A v4t.worker.celery_app:celery_app worker --loglevel=info --queues=live --concurrency=1

# Terminal 4: Beat scheduler (stale job recovery)
uv run celery -A v4t.worker.celery_app:celery_app beat --loglevel=info
```

Requires PostgreSQL on `localhost:5433` and Redis on `localhost:6379`. Use Docker Compose for just the infra services, or run them separately.

### 3. Frontend Setup

```bash
cd vibe4trading-frontend
pnpm install

# Create .env.local
cat > .env.local << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_V4T_WS_BASE_URL=ws://localhost:8000
EOF

pnpm dev
```

Frontend is available at `http://localhost:5173`.

### 4. Import Data

See the [Data Loader Guide](data-loader/README.md) for downloading OHLCV data via Freqtrade and importing it. Quick start with the API:

```bash
# Create a spot dataset from a Freqtrade feather file
curl -X POST http://localhost:8000/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "category": "spot",
    "source": "freqtrade",
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-06-30T23:59:59Z",
    "params": {
      "market_id": "spot:binance:BTC/USDT",
      "feather_path": "/absolute/path/to/BTC_USDT-1h.feather"
    }
  }'
```

### 5. Run a Benchmark

```bash
# Create a replay run
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "spot:binance:BTC/USDT",
    "model_key": "stub",
    "market_dataset_id": "<dataset-uuid>",
    "sentiment_dataset_id": "<sentiment-dataset-uuid>"
  }'
```

Or use the frontend at `http://localhost:5173/runs` to create and monitor runs through the UI.

---

## API Endpoints

All endpoints are served from the FastAPI backend at `http://localhost:8000`. Interactive docs at `/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/me` | Current authenticated user |
| `POST` | `/api/datasets` | Create / import a dataset (async) |
| `GET` | `/api/datasets` | List datasets |
| `GET` | `/api/datasets/{id}` | Dataset status + metadata |
| `POST` | `/api/runs` | Create a replay run (async) |
| `GET` | `/api/runs` | List runs |
| `GET` | `/api/runs/{id}` | Run status + config + metrics |
| `POST` | `/api/runs/{id}/stop` | Stop a running job |
| `GET` | `/api/runs/{id}/timeline` | Equity / P&L time series |
| `GET` | `/api/runs/{id}/decisions` | Decision stream (paged) |
| `GET` | `/api/runs/{id}/summary` | AI-generated run summary |
| `GET` | `/api/runs/{id}/events` | Run event stream (SSE) |
| `POST` | `/api/arena/submissions` | Submit to arena |
| `GET` | `/api/arena/submissions` | List arena submissions |
| `GET` | `/api/arena/submissions/{id}` | Submission detail + results |
| `GET` | `/api/arena/leaderboard` | Leaderboard rankings |
| `POST` | `/api/live/run` | Start a live run |
| `GET` | `/api/models` | List available models |
| `GET` | `/api/admin/models` | Admin: manage model registry |
| `POST` | `/api/admin/models` | Admin: create / update models |

---

## Core Concepts

### Runs

A **run** evaluates exactly one model over one market for a single replay window. The orchestrator loads historical events, builds context at each tick, calls the LLM, validates the decision, simulates portfolio rebalancing, and persists every step as canonical events.

### Arena Submissions

An **arena submission** expands a single strategy into multiple replay runs across fixed scenario windows. Currently supports two scenario sets:

- `default-v1`: 10 x 12-hour windows (fast demos)
- `crypto-benchmark-v1`: 10 x 7-day windows (full benchmark)

After all windows complete, aggregate metrics are computed and an AI report is generated.

### Datasets

A **dataset** is a time-bounded collection of canonical events imported from an external source. Categories:

- `spot` — OHLCV candles + price ticks (from Freqtrade feather files or demo generator)
- `sentiment` — Tweets / social media posts + per-item AI summaries

### Events

The platform is built on an append-only event log. Every market tick, LLM call, decision, fill, and portfolio state is persisted as a canonical event with:

- `event_type` — e.g. `market.price`, `llm.decision`, `portfolio.snapshot`
- `observed_at` — when the platform knew about this event (no lookahead)
- `dedupe_key` — stable key for idempotent replay
- `dataset_id` or `run_id` — scoping for deduplication

### Guard Chain

Before executing any LLM decision, the system applies deterministic guards:

- Spot long-only enforcement (exposure 0.0–1.0)
- Gross leverage cap
- Net exposure cap
- Missing data policy (skip tick, hold last targets)
- Decision validation (reject malformed JSON, hold last targets)

---

## Data Flow: Replay Run

```
1. User → POST /api/runs (market + model + prompt + dataset refs)
2. API validates config, creates RunRow + RunConfigSnapshot + JobRow
3. API dispatches Celery task to default queue
4. Worker loads historical dataset events from PostgreSQL
5. Replay iterator streams events in deterministic order
6. At each scheduled tick (default: 4h):
   a. Snapshot builder: select events where observed_at ≤ tick_time
   b. Prompt builder: assemble market bars + sentiment + last 3 decisions
   c. LLM gateway: call model, log to llm_calls table
   d. Decision validator: parse JSON, enforce constraints
   e. Guard chain: check exposure limits, reject if invalid
   f. Simulator: rebalance portfolio, compute fills at snapshot price
   g. Persist: write events + portfolio snapshots to PostgreSQL
7. After final tick: generate AI summary via LLM
8. Mark run as finished
9. Frontend reads results via polling / SSE
```

---

## Environment Variables

All backend settings use the `V4T_` prefix. See [`.env.example`](vibe4trading-backend/.env.example) for the full list. Key variables:

| Variable | Default | Description |
|---|---|---|
| `V4T_DATABASE_URL` | `postgresql+psycopg://...` | SQLAlchemy database URL |
| `V4T_REDIS_URL` | `redis://localhost:6379/0` | Celery broker + result backend |
| `V4T_LLM_BASE_URL` | (none) | OpenAI-compatible API base URL |
| `V4T_LLM_API_KEY` | (none) | LLM provider API key |
| `V4T_LLM_MODEL` | `stub` | Default model key |
| `V4T_LLM_MODEL_ALLOWLIST` | (none) | Comma-separated allowed model keys |
| `V4T_BYPASS_AUTH` | `false` | Skip auth for local development |
| `V4T_OIDC_ISSUER` | (none) | Authentik OIDC issuer URL |
| `V4T_OIDC_CLIENT_ID` | (none) | OIDC client ID |
| `V4T_OIDC_CLIENT_SECRET` | (none) | OIDC client secret |
| `V4T_REPLAY_BASE_INTERVAL_SECONDS` | `14400` | Replay tick cadence (4h) |
| `V4T_EXECUTION_FEE_BPS` | `10` | Trading fee in basis points |
| `V4T_EXECUTION_INITIAL_EQUITY_QUOTE` | `10000` | Starting paper balance |
| `V4T_DAILY_RUN_LIMIT` | `3` | Max runs per user per day |
| `V4T_ARENA_DATASET_IDS` | (none) | Pre-populated datasets for arena |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend → backend API URL |
| `VITE_V4T_WS_BASE_URL` | `ws://localhost:8000` | Frontend → backend WebSocket URL |

---

## Development

### Backend

```bash
cd vibe4trading-backend
uv sync

# Run tests
uv run pytest

# Lint + format
uv run ruff format .
uv run ruff check .

# Type check
uv run pyright
```

### Frontend

```bash
cd vibe4trading-frontend
pnpm install

# Dev server
pnpm dev

# Lint
pnpm lint

# Unit tests
pnpm test

# E2E tests (requires running backend)
pnpm test:e2e
```

### Docker Compose

From the backend directory:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

This starts all services: `db` (Postgres), `redis`, `api` (FastAPI), `worker` (default queue), `worker_live` (live queue), `beat` (scheduler), and `frontend`.

| Service | Port | Description |
|---|---|---|
| `frontend` | 3000 | Vite + React SPA (production build) |
| `api` | 8000 | FastAPI backend |
| `db` | 5433 → 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |

---

## Design Principles

1. **Benchmark-first** — Not a trading bot. A strategy evaluation and comparison platform with tournament-style scoring.
2. **Event-sourced** — Append-only event log. Every market tick, LLM call, decision, fill, and portfolio state is a canonical event with deduplication guarantees.
3. **Deterministic replay** — No lookahead bias. Snapshots built from `observed_at ≤ tick_time`. Same event stream + same config → same execution path.
4. **Durable jobs** — PostgreSQL is the system of record for job state. Celery is just the transport. Workers can crash and jobs recover via heartbeat timeout.
5. **Model-agnostic** — Admin-managed model registry. Any OpenAI-compatible provider. Config snapshotted per run for full reproducibility.
6. **Arena fairness** — Fixed scenario windows with deterministic dataset slicing. Multiple submissions scored against identical market data.
7. **Strong typing** — Pydantic models define all contracts. Strict Pyright type checking. Decimal strings in events, JSON numbers in REST responses.
8. **Historical-first** — The system is designed around stored data and replay. Live mode is replay with a real-time data source.

---

## Ports

| Service | URL |
|---|---|
| Frontend (dev) | `http://localhost:5173` |
| Frontend (Docker) | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| API Docs (Swagger) | `http://localhost:8000/docs` |
| API Docs (ReDoc) | `http://localhost:8000/redoc` |
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |

---

## License

Private repository. All rights reserved.
