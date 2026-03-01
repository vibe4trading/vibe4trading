# First Claw Eater - Decisions & Notes

## Context

- **Event**: OpenClaw Hackathon (blockchain/crypto), ~600 participants, Mar 1-7
- **Team**: 6 people
  - **Grider** — Software architect, main technical lead
  - **Tiannan** — Product designer, product owner, AI product & startup experience
  - **Fiona** — Product lead, research/narrative, sponsor research, LSE
  - **Jerry** — Product and planning, LSE
  - **Jacky** — Hackathon veteran, code assist, sponsor framework integration
  - **Aaron** — CS + cybersec, crawler/scraping expert, indie dev experience, UI/product assist
- **Product name**: TBD (team name "First Claw Eater" is separate)

---

## Product Vision

A **dynamic LLM trading analysis / benchmarking platform** that:
1. Pits multiple LLM models against each other making crypto trading decisions
2. Runs on a paper account (simulated execution, no real money)
3. Stores all historical data so any time period can be replayed
4. Benchmarks model performance over identical historical data
5. Displays decision reasoning, P&L curves, and trade annotations on a dashboard

NOT just a live trading bot — it's a **benchmarking and analysis platform** with live capability.

Terminology (execution):
- **Live mode**: ingest current data from vendor APIs and run models in real time.
- **Replay mode**: run the benchmark over a selected historical time window by playing historical data forward as if it were live.
  - Replay mode does *not* reuse past LLM decisions; it calls models on historical snapshots.

Product modes (UX):
- **Live Dashboard (main page)**: a curated, global live run with fixed prompt/settings for always-on visualization.
- **Benchmark Lab**: user-created replay benchmarks (prompt template + model set + historical window + market subset from the pinned universe).
- **Strategy Arena (Leaderboard)**: user submits `model_key` + prompt + metrics spec only; platform runs it over fixed scenario windows with fixed universe/scheduler/execution knobs; leaderboard ranks by total return %.

Non-goals (MVP):
- No billing/subscriptions.
- No real-money execution (paper/sim only).
- No arbitrary user-uploaded code execution in the backend (custom metrics aggregators must be a safe JSON/DSL).
- No enterprise multi-tenant features (orgs, complex RBAC); only per-user ownership + basic admin.

---

## Core Decisions

### Architecture
| Decision | Choice | Notes |
|----------|--------|-------|
| Pattern | Orchestrator Pipeline | Code calls LLM at intervals, feeds data, parses output. Not MCP. |
| Service boundaries | Microservices + MQ | Independent services (crawlers, orchestrator, API). RabbitMQ is the backbone. |
| Backend | Python (FastAPI) | Pydantic-first, auto OpenAPI generation |
| Frontend | TypeScript (Next.js) | Dashboard, TradingView Widget for charts |
| Message Queue | RabbitMQ | Simpler than Kafka. Used for inter-service communication between crawlers, orchestrator, etc. |
| Event persistence | Event-store service | Dedicated consumer persists canonical events from RabbitMQ into Postgres with idempotent dedupe. |
| Output persistence | Publish events only | Orchestrator publishes `llm.*` / `sim.*` / `portfolio.*` events; event-store persists canonical events (no direct DB writes required for correctness). Prompts/responses are stored separately in `llm_calls` (written by `llm_gateway`) and referenced from events. |
| Run concurrency | Global live + queued replay jobs | Live Dashboard is one global live run; Benchmark Lab/Arena runs execute async with bounded concurrency (MVP: 1 replay worker). |
| Database | Postgres | Start with plain Postgres + good indexes (time-series friendly schema). Timescale can be added later if needed. |
| Entity typing | Pydantic (Python) + Zod (TypeScript) | Shared via generated OpenAPI spec |
| API layer | REST + OpenAPI | Auto-generated from Pydantic models |
| Control plane | API + MQ commands | API server is source of truth for run/dataset lifecycle; it writes DB state then publishes `run.*` / `dataset.*` commands on `ex.control`. |
| LLM integration | Gateway service | Central service handles provider routing, retries, rate limits, and audit logging (`llm_calls`). OpenAI-compatible facade (OpenRouter likely). Provider endpoints/keys are admin-managed server-side secrets. |
| Uniform API scope | Internal + external | Internal provider interfaces + stable external REST/OpenAPI for dashboard/clients. |
| Config | DB-backed + snapshotted | Runtime-editable, but every run stores an immutable config snapshot for reproducibility. |
| Auth | OIDC (Authentik) | Authentik as OIDC provider (bridges Google/GitHub/etc). Backend validates JWTs via JWKS; user owns their benchmarks. |
| Tenancy | Per-user ownership | Benchmarks private by default; leaderboard is public but redacted (metrics-only, no prompt text). |
| Deployment | Docker Compose | One command to run everything: API, crawlers, MQ, DB, frontend |

### Data & Markets
| Decision | Choice | Notes |
|----------|--------|-------|
| Spot data source | DexScreener | DEX aggregator, Solana tokens primarily |
| Futures data source | Hyperliquid (v1) | Not CEX futures. dYdX is a likely follow-on adapter. |
| Trading universe | Fixed watchlist ~20 markets | Universe is defined as explicit `MarketRef`s (pool/contract ids) for deterministic replay, not LLM-discovered. Benchmark Lab selects a subset; Arena uses the pinned list. |
| Instruments | Spot + perpetual futures | Futures adds shorting capability, more complex simulation |
| Chain focus | Solana primarily | Most meme/sentiment-driven tokens, best fit for LLM alpha |
| Data source strategy | Vendor-only | Rely on vendor APIs; invest in caching/backoff and store enough history ourselves for replay. |
| Source resolution | Single adapter per category | A run selects exactly one adapter per data category (e.g. spot prices). For sentiment, that adapter may aggregate multiple feeds (X KOL list + RSS) but still emits one canonical stream. Avoids cross-vendor reconciliation complexity; compare vendors by running separate datasets. |
| Canonical identity | AssetRef + MarketRef | Use `AssetRef` for cross-venue identity. Keep `TokenRef` for on-chain addresses. `MarketRef` binds venue+instrument id to (base, quote) assets. |
| Vendor payload retention | Raw + normalized | Store raw vendor payloads alongside normalized canonical payloads for debugging and adapter evolution. For very large/list payloads, retain only an aggregated/top-X subset (configurable) to avoid unbounded growth. |
| Historical importer | Required | Backfill a selected time window from vendor APIs into the event log so benchmarks can run on past periods. |

### LLM & Trading Logic
| Decision | Choice | Notes |
|----------|--------|-------|
| Model selection | Configurable allowlist | Admin manages available models/providers; users select from an allowlist for runs/leaderboard (avoid arbitrary endpoints/keys in MVP). |
| Provider routing | OpenAI-compatible | All model calls go through the gateway using OpenAI-format requests (OpenRouter preferred). |
| Prompt strategy | Same prompt within a benchmark run | Benchmark runs compare models apples-to-apples; prompts are user-configurable per run (Benchmark Lab) and stored/snapshotted. |
| Prompt authoring | Freeform + templating | Prompt text supports a constrained template engine (no code execution) so users can parameterize prompts safely. |
| Prompt visibility | Private by default | Store full prompts for audit/repro, but public leaderboard views show only summary metrics/score (no prompt text). |
| Prompt payload | Raw + features | Include compact raw context (latest prices/bars) plus derived features/alerts and the shared sentiment summary to keep prompts stable and small. |
| Feature computation | On-the-fly | Compute derived indicators/features in the orchestrator at prompt time (no `feature.*` event stream in v1). |
| Decision format | Strict JSON schema | Require valid JSON matching Pydantic schema. Decimal fields accept JSON numbers or quoted decimal strings; parsed values are normalized and persisted canonically as decimal strings. Invalid output => error event + hold last targets. |
| Decision output | Target exposures (% equity) | Models output target exposure as a fraction of current equity per `market_id` (resolved to `MarketRef`) (e.g. `-0.25` = 25% short, `+0.40` = 40% long), not discrete orders. |
| Decision sparsity | Sparse allowed | Targets are a map keyed by `market_id`. Model may omit markets; omitted markets default to previous targets (configurable). |
| Decision analysis fields | Rationale + confidence | Decision schema includes optional `rationale` string, `confidence` (0-1), and `key_signals` list for dashboard analysis. |
| Exposure constraints | Gross/Net limits | Enforce gross leverage + net exposure caps across the whole portfolio; cash is implicit residual. |
| Instrument constraints | Spot long-only, perps long/short | Spot exposures must be `>= 0`. Perps exposures may be positive or negative. Violations => decision rejected (hold last targets). |
| Scheduling | Wall-clock baseline + early checks | Models are called on a wall-clock base cadence for comparability/progress. Model may request earlier re-checks via `next_check_seconds`; we only honor earlier-than-base requests, clamp to `[min_interval_seconds, base_interval_seconds]`, align to the next price tick, and log all requests (even ignored ones) for cost/accounting. |
| Default interval | 1 hour | Base cadence; models may request earlier re-checks; store every schedule request for analysis/cost accounting. |
| Budgeting | Track + throttle (MVP) | Track calls/tokens/cost per user/run; enforce concurrency + rate limits (no billing; avoid runaway leaderboard submissions). |
| Backtesting | MQ historical playback | Backfill/ingest historical market events into the DB, then publish a chosen time window into RabbitMQ to mimic live ingestion (LLMs are called live on historical snapshots). |
| Prompt time masking | Prompt-only offset | Allow shifting timestamps shown to the model (and derived time features) by a user-defined offset to test memorization/leakage. Internal `observed_at`/`event_time` in the replay stream and outputs remain unshifted. |
| Replay speed | As fast as possible | Advance clock event-to-event; bound by `max_concurrent_llm_requests` and provider rate limits. |
| LLM benchmarking | Parallel replay | Run N models over same historical period, same data snapshots, compare decisions and P&L |
| Prompt storage | Store full | Persist full prompt + raw response in `llm_calls`. Keep `llm.decision` payloads bounded by storing parsed decisions + references (e.g., `call_id`) instead of embedding full prompts/responses in events. |
| LLM failure policy | Hold last targets | On timeout/parse/validation error, keep last target exposures; emit an error event; retry next tick. |

LLM decision JSON (v1) (draft):

Decimal fields may be JSON numbers or quoted decimal strings; example uses numbers for readability.
When persisted into canonical events (e.g. `llm.decision`), decimals are stored as decimal strings per Numeric encoding.

```json
{
  "schema_version": 1,
  "targets": {
    "spot:raydium:<pool>": 0.25,
    "perps:hyperliquid:BTC-PERP": -0.10
  },
  "next_check_seconds": 600,
  "confidence": 0.62,
  "key_signals": ["momentum_up", "funding_positive"],
  "rationale": "Short BTC perps due to funding + trend reversal; long spot TOKEN on breakout."
}
```

Validation rules (v1):
- `targets` keys must be known `market_id`s from the run universe.
- `targets` values must be parseable decimals (either JSON numbers or quoted decimal strings).
- If present, `confidence` must be a parseable decimal in `[0, 1]`.
- Spot markets must have exposure `>= 0`.
- Any validation failure rejects the whole decision (hold last targets).

### Simulation & Execution
| Decision | Choice | Notes |
|----------|--------|-------|
| Execution style | Rebalance to target | Given target exposure fractions, compute target notional per market (`target = exposure * equity`) and simulate trades to reach the implied target positions (paper account). |
| Fill pricing | Current snapshot price | Execute at the latest known snapshot price at decision time (spot uses pool/mid `market.price`; perps use `perps.mark`) with no lookahead beyond observed data. |
| Data freshness | Fresh-only | Require `market.price` / `perps.mark` with `observed_at <= tick_time` and age `<= 60s` (configurable; typically equals `price_tick_seconds`) at each decision tick (no carry-forward). Missing required data => skip LLM call, emit an error event, and hold last targets. |
| Fees | Simple bps model | Apply configurable fee rates per venue/instrument; track fees separately in P&L. |
| Perps PnL | Mark-to-market | Value perps positions using mark price snapshots; unrealized P&L updates each tick. |
| Funding | Apply funding | Apply funding payments/receipts using perps funding rate events. |
| Liquidation | Not simulated (v1) | Enforce gross/net risk caps; do not model liquidation/margin calls initially. |

### Crawlers & Protocols
| Decision | Choice | Notes |
|----------|--------|-------|
| Crawler architecture | Independent microservices | Each crawler (price, sentiment, on-chain) is its own service, communicates via RabbitMQ |
| Exchange abstraction | CCXT-style unified API | Abstract base with `get_price()`, `get_ohlcv()`, `get_trades()`, `get_liquidity()`, plus perps methods (`get_mark_price()`, `get_funding_rate()`). Leverage CCXT for CEX if needed. |
| Sentiment source | Scraper + per-tick summarizer | Scrape a curated X/Twitter KOL list + RSS/news into `sentiment.item`. At each tick, run a shared (per-tick) sentiment summarization step (fixed summarizer config for comparability; 1h lookback; cap inputs to 20 posts + 10 news) to emit a global-text `sentiment.summary` (emit empty summaries when no items). Free but risk of blocking. |
| Adapter packaging | In-repo modules | Keep adapters in the repo with explicit registration (no dynamic plugin loading). |

### Stretch Goals (if time permits)
| Item | Notes |
|------|-------|
| Polymarket module | Binary prediction markets. Share sentiment engine. Separate execution module. Tiannan suggested — real money-making potential (e.g. weather markets). Different liquidity curve, needs its own system. |
| Per-market sentiment (upgrade) | Upgrade from global-text summaries to per-market summaries + structured scores/signals + better anti-bot resilience. |

---

## Key Design Principles

1. **Modularity** — Every component (crawler, orchestrator, LLM adapter, execution engine) is a separate service communicating via MQ. Can be developed, tested, and deployed independently.
2. **Replayability** — All market data, signals, and LLM decisions are persisted as an append-only event log with timestamps. Any imported/collected time period can be replayed by re-publishing events through the same MQ pipeline.
3. **Strong typing** — Pydantic models define all entities. These are the source of truth. Frontend Zod schemas mirror them via OpenAPI.
4. **Model-agnostic** — No hardcoded LLM providers. Users choose from an allowlisted set of models; provider endpoints + API keys are admin-managed server-side secrets; every run snapshots the resolved model config (excluding secrets).
5. **Historical-first** — The system is designed around stored data and replay. Live mode is just "replay with real-time data source."

6. **Uniform contracts** — All third-party integrations sit behind typed adapter interfaces and emit canonical events.

7. **Query-first adapters** — Adapters present a CCXT-style, uniform query interface (e.g. `get_price`, `get_ohlcv`). Crawlers/importers use adapters to fetch third-party data and then publish canonical events. The orchestrator consumes canonical events only.

8. **Deterministic replay** — Input data streams are repeatable: given the same event stream ordering + config snapshot, the orchestrator should rebuild identical snapshots. (Model outputs may still vary unless provider settings are deterministic.)

9. **Bounded payloads** — Canonical event payloads must stay bounded. For high-volume/list data (e.g. trades), store aggregates and/or a reasonable top-X subset so storage, replay, and prompt-building stay tractable.

## Uniform Contracts (Draft)

Canonical IDs (used everywhere: events, DB, API):
- `AssetRef`: `{namespace, id, symbol?}` (cross-venue identity; supports on-chain tokens, perps underlyings, fiat)
- `TokenRef`: `{chain, address, symbol?}` (on-chain identity only)
- `MarketRef`: `{venue, market_type, base: AssetRef, quote: AssetRef, instrument_id}` (tradable market identity; `instrument_id` is pool address for spot, contract symbol/id for perps)

`AssetRef` conventions (v1):
- On-chain token: `namespace=<chain>`, `id=<address>` (mirrors `TokenRef`)
- Fiat: `namespace="fiat"`, `id="USD"`
- Perps underlying without an on-chain address mapping: `namespace="symbol"`, `id=<TICKER>`

Canonical string IDs (v1):
- `asset_id`: `{namespace}:{id}` (e.g. `solana:So111...`, `fiat:USD`)
- `market_id`: `{market_type}:{venue}:{instrument_id}` (e.g. `spot:raydium:<pool>`, `perps:hyperliquid:BTC-PERP`)

`market_id` is used in prompts and LLM decision output to keep JSON small and avoid brittle nested structures.

Canonical event envelope (every message on RabbitMQ and every stored event row):
- `event_id` (UUID)
- `event_type` (string)
- `source` (service + adapter name)
- `schema_version` (int)
- `observed_at` (when we saw it)
- `event_time` (when it happened on the venue, if available)
- `dedupe_key` (stable key for idempotency)
- `dataset_id` (optional; present for imported/live market data events)
- `run_id` (optional; present for run-generated events like `llm.*` / `sim.*`)
- `payload` (canonical JSON)
- `raw_payload` (optional; vendor-specific JSON as received; may be truncated/aggregated)

Time semantics:
- `observed_at` is the platform clock for snapshot building and LLM scheduling ("what we knew when")
- `event_time` is optional venue time used for market semantics (bars/trades) and pricing alignment
- For imported/backfilled historical events, set `observed_at = event_time` (the time the information became knowable, e.g. bar close)

Numeric encoding (v1):
- Canonical event payload numbers (prices, quantities, volumes, rates) are encoded as decimal strings (e.g. `"0.1234"`) to avoid float drift.
- LLM decisions may provide decimals as JSON numbers or quoted decimal strings; after parsing/validation, canonical stored values are persisted as decimal strings.
- Units must be explicit in field naming (e.g. `volume_base`, `volume_quote`, `fee_bps`).

Replay determinism contract (goal):
- Replay publishes a single, totally ordered stream into RabbitMQ (e.g., order by `(observed_at, source, event_type, dedupe_key)`)
- Orchestrator applies events idempotently using `(event_type, dedupe_key)` (at-least-once delivery is expected)

Schema evolution:
- All event payloads are versioned via `schema_version`
- Read/replay paths upcast older payloads to the latest canonical shape

Benchmark run model:
- A "benchmark run" groups N model-runs over the same replay window + config snapshot (apples-to-apples prompt).
- A "strategy arena submission" expands into K scenario-runs (same model + prompt + metrics spec) over a curated set of replay windows, then aggregates into one score for the leaderboard.

Event stream categories (initial):
- Market data: `market.*` (price, ohlcv, trades, liquidity)
- Perps: `perps.*` (funding, open interest, mark/index)
- Sentiment: `sentiment.*`
- Decisions: `llm.decision`, `llm.schedule_request`
- Execution: `sim.fill`, `portfolio.snapshot`

### Canonical Event Types (v1) (Draft)

Market data:
- `market.ohlcv` — OHLCV bars per `MarketRef` + timeframe.
  - Payload (suggested): `{market, timeframe, bar_start, bar_end, o, h, l, c, volume_base?, volume_quote?}`
  - Dedupe key (suggested): `{market_id}:{timeframe}:{bar_start}`
- `market.price` — Latest price snapshot used for fills + valuation (1m cadence in v1).
  - Payload (suggested): `{market, price, price_type}` where `price_type in {"last","mid","mark"}`. In v1, spot uses `price_type="mid"` (pool-implied mid); perps valuation uses `perps.mark`.
  - Dedupe key (suggested): `{market_id}:{event_time_or_observed_at}`
- `market.liquidity` — Pool/orderbook liquidity snapshot (used for slippage/risk heuristics).
  - Payload (suggested): `{market, liquidity_usd?, reserves?, depth?}` (bounded)
  - Dedupe key (suggested): `{market_id}:{event_time_or_observed_at}`
- `market.trades` — Bucketed trade summary (1m) + top-20 trades by notional (bounded).
  - Payload (suggested): `{market, bucket_start, bucket_end, stats, top_trades: [...]}` (cap `top_trades` at 20)
  - Dedupe key (suggested): `{market_id}:{bucket_start}:60`

Perps (minimum for sim + prompts):
- `perps.mark` — Mark price snapshot (1m cadence in v1).
- `perps.funding_rate` — Funding rate (interval + next funding timestamp).
- `perps.open_interest` — Optional; used for context/filters.

Sentiment (raw ingestion + per-tick summary):
- `sentiment.item` — Raw scraped item (X post or news item), bounded payload (text/title/snippet + URL + timestamps + basic engagement).
  - Dedupe key (suggested): `{source}:{external_id}` (e.g. `x:tweet:123`, `rss:url:<hash>`)
- `sentiment.summary` — Global per-tick summary text (1h lookback) produced before trading LLM calls; shared across models for apples-to-apples benchmarking. Emit one per tick even if empty.
  - Payload (suggested): `{tick_time, lookback_start, lookback_end, input_counts, summary_text, llm_call_id?}`
  - Dedupe key (suggested): `{tick_time}`

Decisions/execution:
- `llm.decision` — Parsed decision payload (targets keyed by `market_id`, plus rationale/confidence) + references to prompt/response (e.g., `llm_calls.call_id`).
- `llm.schedule_request` — Optional earlier re-check request derived from `next_check_seconds` in decision JSON (logged for cost + analysis).
- `sim.fill` — Simulated trade/fill event.
- `portfolio.snapshot` — Portfolio state projection (equity/cash/positions) at a point in time.

### Snapshot Semantics (Draft)

- Snapshot at time T is built from canonical events with `observed_at <= T`.
- OHLCV bars are only considered usable after they close: `bar_end <= T` (avoid lookahead bias).
- Fill pricing requires a fresh `market.price` / `perps.mark` point for the tick: latest point with `observed_at <= T` and age `<= 60s` (no carry-forward). If missing, treat the snapshot as incomplete.
- If snapshot is incomplete at a scheduled tick, skip the LLM call, emit an error event, and hold last targets.

### Dedupe Key Conventions (v1) (Draft)

Dataset-scoped (market/perps) events:
- Prefer keys based on `market_id` + a time bucket boundary (bar start/bucket start/tick time) so retries are idempotent.

Dataset-scoped (sentiment) events:
- `sentiment.item`: `{source}:{external_id}`

Run-scoped events (unique under `(run_id, event_type, dedupe_key)`):
- `sentiment.summary`: `{tick_time}` (one per tick per run; shared across model-runs)
- `llm.decision`: `{model_run_id}:{tick_time}`
- `llm.schedule_request`: `{model_run_id}:{tick_time}`
- `portfolio.snapshot`: `{model_run_id}:{snapshot_time}`
- `sim.fill` (rebalance model): `{model_run_id}:{tick_time}:{market_id}` (at most one fill per market per tick)

## Run Config Schema (Draft)

Core idea: everything that affects a run (benchmark or arena scenario-run) is captured in a config snapshot and stored with the run.

Suggested top-level objects:
- `Dataset`: imported historical data window per category (spot/perps/sentiment), referenced by id
- `Run`: execution of N models over a set of datasets (typically one per category)
- `ModelRun`: one model evaluated within a run
- `RunConfigSnapshot`: immutable JSON blob referenced by `Run`
- `PromptTemplate`: user-authored prompt text + variables + engine (snapshotted into the run config)
- `ScenarioSet`: curated list of replay windows used for arena/leaderboard
- `ArenaSubmission`: a user's leaderboard entry (model + prompt + metrics spec + scenario set)

Draft config shape:

```json
{
  "mode": "replay",
  "run_kind": "benchmark",
  "visibility": "private",
  "datasets": {
    "spot_dataset_id": "...",
    "perps_dataset_id": "...",
    "sentiment_dataset_id": "..."
  },
  "sentiment": {
    "lookback_seconds": 3600,
    "max_x_posts": 20,
    "max_news_items": 10,
    "summary_kind": "global_text",
    "empty_policy": "emit_empty_summary"
  },
  "replay": {
    "advance_mode": "as_fast_as_possible",
    "max_concurrent_llm_requests": 8
  },
  "universe": {
    "markets": [
      {
        "venue": "raydium",
        "market_type": "spot",
        "base": {"namespace": "solana", "id": "...", "symbol": "TOKEN"},
        "quote": {"namespace": "solana", "id": "...", "symbol": "USDC"},
        "instrument_id": "..."
      },
      {
        "venue": "hyperliquid",
        "market_type": "perps",
        "base": {"namespace": "symbol", "id": "BTC", "symbol": "BTC"},
        "quote": {"namespace": "fiat", "id": "USD", "symbol": "USD"},
        "instrument_id": "BTC-PERP"
      }
    ]
  },
  "scheduler": {
    "base_interval_seconds": 3600,
    "min_interval_seconds": 60,
    "price_tick_seconds": 60,
    "early_check_alignment": "ceil_to_price_tick"
  },
  "decision": {
    "missing_market_policy": "hold_previous"
  },
  "prompt": {
    "template": {
      "engine": "mustache",
      "system": "...",
      "user": "...",
      "vars": {
        "risk_style": "balanced"
      }
    },
    "lookback": {"kind": "fixed", "bars": 24, "timeframe": "1h"},
    "include": ["raw", "features", "sentiment_summary"],
    "masking": {"time_offset_seconds": 0}
  },
  "execution": {
    "fill_pricing": "snapshot_price",
    "gross_leverage_cap": 1.0,
    "net_exposure_cap": 1.0
  },
  "models": [
    {
      "key": "gpt-4o-mini",
      "label": "OpenRouter gpt-4o-mini",
      "temperature": 0,
      "max_output_tokens": 800
    }
  ]
}
```

Dataset alignment (v1):
- All non-null referenced dataset ids must have identical `start`/`end` windows. If they do not match exactly, run creation fails.
- `sentiment_dataset_id` may be omitted; in that case the orchestrator still emits an empty `sentiment.summary` per tick for determinism.

Arena / leaderboard submission (v1):
- A submission references `model_key`, prompt template (freeform + templated), `metrics_aggregator_spec` (JSON/DSL), and `scenario_set_id`.
- For comparability, universe + scheduler + execution/risk knobs are fixed by the platform; user-controlled knobs are prompt + model + metrics spec.
- The system expands a submission into K replay runs (one per scenario window) and aggregates results into one score (default: total return %).
- Leaderboard is public, but details are redacted by default (show score + key metrics only; keep prompt text private).

## External REST API (Draft)

Minimal API surface for a dashboard + CLI:
- `GET /me` current user (OIDC-backed)
- `POST /datasets` create/import a dataset (async) from parameters (spot/perps/sentiment)
- `GET /datasets` list datasets
- `GET /datasets/{dataset_id}` dataset status + metadata
- `POST /prompt_templates` create/update a prompt template (freeform + templating)
- `GET /prompt_templates` list prompt templates (mine + built-ins)
- `POST /runs` create a run (async) from config (or config ref)
- `GET /runs` list runs
- `GET /runs/{run_id}` run status + config snapshot + high-level metrics
- `POST /runs/{run_id}/stop` stop a running job
- `GET /runs/{run_id}/models` list model-runs
- `GET /runs/{run_id}/models/{model_run_id}` per-model metrics + metadata
- `GET /runs/{run_id}/timeline` time series for equity/PnL + positions
- `GET /runs/{run_id}/decisions` decision stream (parsed + raw reasoning)
- `GET /scenario_sets` list curated arena scenario sets
- `POST /arena/submissions` create a leaderboard submission (async)
- `GET /arena/submissions` list my submissions + status
- `GET /arena/submissions/{submission_id}` submission results (per-scenario + aggregate)
- `GET /leaderboards` leaderboard overview (overall + per-model)

## MQ Topology (Draft)

Exchanges:
- `ex.events` (topic): canonical persisted events from crawlers/importers + orchestrator outputs (`sentiment.summary`, `llm.*`, `sim.*`, `portfolio.*`)
- `ex.replay` (topic): replay streaming events feeding replay/orchestrator workers (not persisted; derived from the DB event log)
- `ex.control` (topic): run + dataset control commands

Queues (initial):
- `q.event_store.events` binds `ex.events` with `#` (persist all canonical events to Postgres)
- `q.orchestrator.live.events` binds `ex.events` with `market.*`, `perps.*`, `sentiment.*` (Live Dashboard inputs)
- `q.orchestrator.replay.events` binds `ex.replay` with `market.*`, `perps.*`, `sentiment.*` (Benchmark Lab/Arena inputs)
- `q.orchestrator.control` binds `ex.control` with `run.*`
- `q.importers.control` binds `ex.control` with `dataset.*`

Replay mode behavior (Benchmark Lab / Arena):
- Live crawlers continue to feed Live Dashboard.
- Replay publisher reads the selected dataset window from Postgres and publishes the ordered stream into `ex.replay` for the orchestrator worker.
- Orchestrator publishes outputs into `ex.events` tagged with `run_id`; event-store persists these outputs.

## DB Schema Outline (Draft)

Event log (append-only Postgres table; can become a Timescale hypertable later):
- `events`: `(event_id, event_type, source, schema_version, observed_at, event_time, dedupe_key, payload_jsonb, raw_payload_jsonb, dataset_id, run_id, ingested_at)`

Idempotency / dedupe (v1):
- Unique index on `(dataset_id, event_type, dedupe_key)` where `dataset_id IS NOT NULL`
- Unique index on `(run_id, event_type, dedupe_key)` where `run_id IS NOT NULL`

Run metadata:
- `users`: `(user_id, oidc_issuer, oidc_sub, email, display_name, created_at)`
- `datasets`: `(dataset_id, category, source, start, end, params_jsonb, created_by_user_id, created_at)`
- `prompt_templates`: `(template_id, owner_user_id, name, engine, system_template, user_template, vars_schema_jsonb, created_at, updated_at)`
- `run_config_snapshots`: `(config_id, config_jsonb, created_at)`
- `runs`: `(run_id, owner_user_id, kind, visibility, config_id, status, started_at, ended_at, created_at)`
- `run_datasets`: `(run_id, category, dataset_id)`
- `model_runs`: `(model_run_id, run_id, model_key, status, started_at, ended_at, metrics_jsonb)`

Arena / leaderboard:
- `scenario_sets`: `(scenario_set_id, name, description, created_at)`
- `scenario_windows`: `(window_id, scenario_set_id, label, start, end)`
- `arena_submissions`: `(submission_id, owner_user_id, model_key, prompt_template_id, prompt_snapshot_jsonb, metrics_aggregator_spec_jsonb, scenario_set_id, status, created_at)`
- `arena_results`: `(submission_id, score_return_pct, key_metrics_jsonb, computed_at)`
- `arena_scenario_results`: `(submission_id, window_id, run_id, return_pct, key_metrics_jsonb)`

LLM audit:
- `llm_calls`: `(call_id, run_id, model_run_id?, purpose, observed_at, prompt, response_raw, response_parsed, usage_jsonb, latency_ms, error)` (written by `llm_gateway`; referenced by `llm.decision` / `sentiment.summary`)

Projections for fast reads:
- `portfolio_snapshots`: `(model_run_id, observed_at, equity, cash, positions_jsonb)`
- `sim_trades`: `(trade_id, model_run_id, observed_at, market_ref, qty, price, fees, metadata_jsonb)`

## Adapter Interfaces (Draft)

Implementation bias: adapters expose a uniform *query* surface; crawlers/importers own scheduling/pagination/deduping and emit canonical events.

Contract boundary (important for replayability):
- Only ingestion services (crawlers/importers/replay) talk to third-party services.
- The orchestrator builds snapshots strictly from canonical events (live == replay with realtime ingestion).

Minimal Python-ish contracts:

```python
class SpotMarketDataAdapter(Protocol):
    name: str

    def get_price(self, market: MarketRef, now: datetime) -> "PricePoint":
        ...

    def get_ohlcv(
        self,
        market: MarketRef,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> list["OHLCVBar"]:
        ...

    def get_liquidity(self, market: MarketRef, now: datetime) -> "LiquiditySnapshot":
        ...

    def get_trades(
        self,
        market: MarketRef,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list["Trade"]:
        ...


class HistoricalSpotMarketDataAdapter(SpotMarketDataAdapter, Protocol):
    def backfill_ohlcv(
        self,
        market: MarketRef,
        start: datetime,
        end: datetime,
        timeframe: str,
    ) -> Iterable["OHLCVBar"]:
        ...


class PerpsMarketDataAdapter(Protocol):
    name: str

    def get_mark_price(self, market: MarketRef, now: datetime) -> "PricePoint":
        ...

    def get_funding_rate(self, market: MarketRef, now: datetime) -> "FundingRatePoint":
        ...

    def get_open_interest(self, market: MarketRef, now: datetime) -> "OpenInterestPoint":
        ...


class HistoricalPerpsMarketDataAdapter(PerpsMarketDataAdapter, Protocol):
    def backfill_funding_rates(
        self,
        market: MarketRef,
        start: datetime,
        end: datetime,
    ) -> Iterable["FundingRatePoint"]:
        ...
```

Adapter categories:
- Spot market data adapters (DexScreener, etc.)
- Perps market data adapters (Hyperliquid first)
- Sentiment adapters

---

## Rough System Shape

```
                    ┌─────────────┐
                    │  Next.js    │
                    │  Dashboard  │
                    │ (TradingView│
                    │  + P&L)     │
                    └──────┬──────┘
                           │ REST/OpenAPI
                    ┌──────┴──────┐
                    │  FastAPI    │
                    │  API Server │
                    │  + Config   │
                    └──────┬──────┘
                            │
               ┌────────────┼────────────┐
               │            │            │
         ┌─────┴─────┐ ┌───┴────┐ ┌─────┴──────┐
         │ Orchestr-  │ │ Postgres │ │  RabbitMQ  │
         │ ator       │ │(all data)│ │  (events)  │
         │ (scheduler │ └───┬────┘ └─────┬──────┘
          │  + LLM     │     │            │
          │  calls)    │     │     ┌──────┼──────┐
        └─────┬──────┘     │     │      │      │
              │            │  ┌──┴──┐┌──┴──┐┌──┴──┐
              │            │  │Price ││Sent-││On-  │
              └────────────┘  │Crawl ││iment││Chain│
                               │(Dex- ││(X/  ││(perps│
                                │Scr.) ││RSS)   ││data)│
                               └─────┘└─────┘└─────┘
```

### Services (v1) (Draft)

- `api` — REST/OpenAPI surface for dashboard + CLI; stores configs/snapshots; run/dataset lifecycle.
- `orchestrator` — Snapshot builder + scheduler; computes shared per-tick `sentiment.summary`; calls LLM gateway; publishes `sentiment.summary` / `llm.*` / `sim.*` / `portfolio.*` events.
- `event_store` — Single writer for the canonical `events` table (idempotent dedupe); optionally maintains simple projections.
- `replay` — Reads canonical events for selected dataset ids/time window and publishes them into `ex.replay` with deterministic ordering.
- `importers` — Backfill per category (spot/perps/sentiment) producing dataset ids.
- `live crawlers` — Continuous ingestion in live mode (always-on for Live Dashboard; replay runs do not require disabling live feeds).
- `llm_gateway` — Provider routing, retries, rate limits, usage/cost accounting, and audit logging to `llm_calls` (returns `call_id` for event references); OpenAI-compatible facade.
- `arena` (optional) — Expands leaderboard submissions into scenario-runs, aggregates return % + key metrics, and serves leaderboard views.

### Data Flow (Live Mode)
1. Crawlers independently fetch data on their own schedules → publish to RabbitMQ
2. Orchestrator consumes from MQ, aggregates into a market snapshot
3. On each scheduled tick, orchestrator builds a tick snapshot and computes a shared sentiment summary for the lookback window (bounded inputs; emit empty summary if no items)
4. Orchestrator builds prompts from the same snapshot + shared sentiment summary → calls each scheduled model
5. Each LLM returns target exposures (+ optional next-check request)
6. Simulated execution engine processes decisions, updates paper portfolio, and publishes `llm.decision` / `sim.fill` / `portfolio.snapshot` events
7. Event-store service consumes canonical events from RabbitMQ and persists them to Postgres (append-only event log + projection tables for fast dashboard queries)
8. Dashboard polls API for latest state, renders charts

### Data Flow (Backtest/Replay Mode)
1. Importers/backfill jobs run per category (spot/perps/sentiment). Each importer fetches vendor data and publishes canonical events to RabbitMQ (tagged with its `dataset_id`); event-store persists them to Postgres
2. A replay service reads the chosen time window for the run's dataset ids (spot/perps/sentiment) from the DB event log and merges them into a single ordered stream
3. It republishes that merged stream into RabbitMQ (via `ex.replay`) preserving stored `observed_at` values (for backfilled data, typically `observed_at = event_time`) with deterministic ordering rules
4. The orchestrator consumes the same message types as live mode (but from `ex.replay`) and rebuilds snapshots
5. On each scheduled tick, orchestrator computes the shared sentiment summary for the lookback window (emit empty summary if no items), then calls each scheduled model using the same snapshot + shared sentiment summary
6. Decisions and simulated P&L are stored as a "benchmark run" (multi-model) or as scenario-runs that roll up into an arena submission score
7. Dashboard shows side-by-side model comparison and arena leaderboard views for any historical period

---

## Open Questions for Deep Research

1. **DexScreener API limits** — Rate limits, historical data depth, WebSocket availability?
2. **Hyperliquid historical data** — Mark/index history, funding rate history, rate limits, and how cleanly it supports backfill for replay. (dYdX is a follow-on adapter.)
3. **RabbitMQ replay patterns** — Deterministic ordering + idempotency: what is the replay contract (exactly-once not guaranteed), and how do we avoid double-applying events?
4. **Solana watchlist** — Which ~20 tokens/markets have the most sentiment-driven price action (and which specific pools/markets should be pinned as `MarketRef`s)? Need high volume + high social media correlation.
5. **LLM cost estimation** — At 1h intervals, 20 tokens, 3-5 models, what's the daily API cost? Context window considerations for market data.
6. **Simulation fidelity** — Slippage model for DEX trades (AMM curve)? How to simulate perps funding rates?
7. **X/Twitter scraping** — Current state of anti-bot measures? Which KOLs move Solana token prices?
8. **Hackathon sponsor frameworks** — Which sponsors have agent frameworks we should wrap our logic in? Check Discord for track prizes.
9. **TradingView Widget limitations** — Can it render custom trade annotations (buy/sell markers)? Or do we need Lightweight Charts for that?
10. **Canonical event payload shapes** — For each `market.*` / `perps.*` event type, what is the minimal canonical payload that stays stable across vendors while still being useful for prompt building + sim?
11. **High-volume events policy** — For `market.trades` (1m buckets + top-20) and other potentially large payloads, what are the exact bucket stats + top-20 selection rule, and what do we keep as raw vs normalized?
12. **AssetRef conventions** — How do we map on-chain `TokenRef`s, fiat (USD), and perps underlyings into a stable `AssetRef` namespace/id scheme (e.g., chain address vs symbol vs Coingecko id)?
13. **OIDC integration** — Which claims/groups define admin vs user? Token lifetimes/refresh? Do we accept only Authentik-issued tokens on the API (JWKS pinning + issuer checks)?
14. **Prompt templating contract** — Exactly which variables are available (snapshot JSON, derived features, shared sentiment summary, risk limits), and how do we keep templates deterministic + bounded in size?
15. **Leaderboard fairness** — Scenario window definitions, return % aggregation across windows, and which fixed risk constraints to enforce for comparability.
16. **Metrics DSL** — What safe JSON/DSL operations are allowed, how to validate it, and how to ensure runtime determinism/performance.

---

## Reference Repo Learnings: OpenAlice (MIT)

We reviewed `TraderAlice/OpenAlice` (local checkout: `/home/grider/build/OpenAlice`). It's a file-driven, extension-based trading agent engine. Even though our target architecture is **microservices + RabbitMQ + Postgres**, several patterns are worth copying/adapting.

### License / Copying Notes

- OpenAlice is **MIT licensed** (`OpenAlice/LICENSE`). We can copy code, but must retain the copyright + license notice in any copied/substantial portions.
- Decision: copy **ideas/patterns** and re-implement in our stack (Python/FastAPI + MQ). Do not vendor/copy OpenAlice modules directly unless we explicitly choose to later.

### Concepts Worth Borrowing

1. **Composition root (clean wiring)**
   - OpenAlice keeps nearly all runtime wiring in one place (`OpenAlice/src/main.ts`): config load, dependency construction, background tasks, connector startup, provider wiring.
   - Copy idea: keep orchestration wiring (MQ clients, DB clients, LLM gateway client, scheduler, adapters) in a single, explicit composition root per service.

2. **File-driven config with schema validation + seeded defaults**
   - Pattern: configs live as JSON files; on first run they are auto-created with defaults; Zod validates and migrates (`OpenAlice/src/core/config.ts`).
   - Copy idea (even with DB-first config): keep config schemas explicit, versioned, and migratable; seed sensible defaults; and snapshot the exact config used for each run for reproducibility.

3. **Default + user override files for prompts/persona**
   - Pattern: git-tracked defaults + gitignored user overrides (`data/default/*.default.md` -> `data/brain/*.md`) with a helper that copies defaults on first run (`readWithDefault` in `OpenAlice/src/main.ts`).
   - Copy idea: prompt templates (and any prompt "policy" text) should follow the same default/override split so we can iterate quickly without editing code.

4. **Append-only JSONL EventLog with in-memory tail cache + subscriptions**
   - Pattern: disk append (JSONL) + in-memory ring buffer + `subscribeType()` for real-time reactions (`OpenAlice/src/core/event-log.ts`).
   - Copy idea (our DB/MQ version): keep the event store append-only, and add a small in-memory "tail cache" + typed subscription hooks in services that need fast recent-event access or real-time reactions.

5. **Guard pipeline (pre-execution safety checks) as a chain**
   - Pattern: one place assembles a context (positions + account + operation), then runs a guard chain; guards are pluggable via a registry resolved from config (`OpenAlice/src/extension/crypto-trading/guards/*`).
   - Copy idea: implement constraints as first-class "guards" (gross/net caps, per-market caps, spot long-only, turnover limits, cooldowns, missing-data policies) before applying LLM targets.

6. **Git-like Wallet workflow for trading operations (stage/commit/push)**
   - Pattern: stage operations, commit with a message (the "why"), then push to execute; persistent commit history with short hashes (`OpenAlice/src/extension/crypto-trading/wallet/Wallet.ts`, `OpenAlice/src/extension/crypto-trading/wallet/adapter.ts`).
   - Copy idea (decision: audit-only commits in sim): treat each tick as an immutable "commit" record (diff from last targets/portfolio, LLM rationale/confidence, guard results). Execution stays automatic in the simulator; no manual staging/push loop required for replay mode.

7. **Hot-reloadable provider routing**
   - Pattern: ProviderRouter reads runtime config on each call so provider/model can change without restart (`OpenAlice/src/core/ai-provider.ts`, hot-read helpers in `OpenAlice/src/core/config.ts`).
   - Copy idea: our LLM gateway can support "runtime switch" per model-run (provider, base URL, rate limits) while still snapshotting the exact config used for reproducibility.

8. **Unified session/event persistence formats**
   - Pattern: a single JSONL session format that both providers can read/write; converts to provider-specific message formats (`OpenAlice/src/core/session.ts`).
   - Copy idea: define one canonical "LLM call record" format (prompt, response, usage, latency, errors) that is provider-agnostic. Store it once, render it anywhere.

9. **Context compaction (microtruncate + full summary)**
   - Pattern: first truncate large tool results, then optionally summarize older history into a boundary + summary entry (`OpenAlice/src/core/compaction.ts`).
   - Copy idea: if we ever add multi-turn agent loops (e.g., sentiment research agent), we should plan compaction early so runs don't die when context grows.

10. **Connector abstraction + "last interaction" routing**
   - Pattern: connectors register with a ConnectorCenter; outbound notifications go to the last-interacted channel (`OpenAlice/src/core/connector-center.ts`).
   - Copy idea: if we add Telegram/Discord/webhook notifications (run finished, errors, big drawdown), route to the last active operator channel automatically.

11. **Separation of "tool exposure" vs "agent conversation" surfaces to avoid circular calls**
   - Pattern: the Ask connector runs on a separate port and is not registered in ToolCenter, preventing the agent from discovering and calling itself (`OpenAlice/docs/mcp-ask-connector.md`).
   - Copy idea: if we expose our platform via MCP or similar, keep "internal tools" and "external conversation" clearly separated so models can't accidentally create loops.

### What We Should NOT Copy (Mismatch)

- OpenAlice is intentionally **single-tenant + file-first** (no DB, no MQ). Our benchmark/replay requirements benefit from Postgres + durable MQ; use JSONL/eventlog ideas as conceptual inspiration only (decision: no JSONL fallback implementation).
- Wallet operations are **order-centric**. Our v1 decision format is **target exposures**; copy the UX metaphor, but adapt the data model (diff exposures -> implied fills).

### Decisions From This Review

- Code reuse: re-implement OpenAlice patterns (no direct module vendoring).
- Execution audit: wallet-style commit log metaphor, audit-only (sim stays automatic).
- Config: DB-first source of truth, snapshot per run for reproducibility.
- Event store: RabbitMQ + Postgres only (no JSONL fallback).
