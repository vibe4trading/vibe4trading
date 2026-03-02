# Three-Repo TODO (Backend-Internal Pipeline)

This plan intentionally reduces scope from a microservice monorepo to **three separate repos**:

- `first-claw-eater-backend` (Python, `uv`) - **modular monolith**: API + import/replay/orchestrator/sim/LLM/sentiment all in one codebase.
- `first-claw-eater-frontend` (TypeScript, `pnpm`) - Next.js dashboard.
- `first-claw-eater-crawler` (placeholder) - future home for vendor adapters; not required to ship MVP.

Key constraint from you: **all pipeline stages are internal to the backend** (no separate orchestrator/event-store/replay services for now). We still keep the *interfaces and data contracts* so a later split is straightforward.

---

## Repo 1: `first-claw-eater-backend` (Internal Pipeline)

### Target shape (backend repo)

```text
first-claw-eater-backend/
├─ src/fce/
│  ├─ api/                      # FastAPI routers (REST)
│  ├─ auth/                     # OIDC/JWKS validation + user provisioning
│  ├─ contracts/                # Pydantic models (IDs, events, configs, decisions)
│  ├─ db/                       # SQLAlchemy models + session + migrations
│  ├─ jobs/                     # background job runner + job definitions
│  ├─ ingest/                   # live crawlers + importer logic (dataset build)
│  ├─ replay/                   # deterministic replay stream from DB
│  ├─ orchestrator/             # snapshot builder + scheduler + prompt builder
│  ├─ llm/                      # provider routing + audit logging (llm_calls)
│  ├─ sim/                      # rebalance engine + guards + PnL accounting
│  ├─ arena/                    # optional tournament expansion + aggregation
│  └─ observability/            # logging, metrics, tracing helpers
├─ migrations/                  # Alembic
├─ scripts/                     # admin/dev utilities
├─ infra/compose/               # docker compose (postgres, authentik, backend)
├─ pyproject.toml
└─ README.md
```

### Tooling (gold standard defaults)

- Python: 3.12+
- Package manager: `uv`
- Web framework: FastAPI
- Typing/validation: Pydantic v2
- DB: Postgres + SQLAlchemy 2.0 + Alembic
- HTTP: `httpx` (vendor calls)
- Retry/backoff: `tenacity`
- Lint/format: `ruff`
- Type checking: `pyright` (preferred)
- Tests: `pytest` + `pytest-asyncio`
- Observability: `structlog` (or stdlib logging with JSON), Prometheus metrics

---

## Backend Phase 0 - Architecture Lock (Internal Pipeline Edition)

- [ ] Write a short ADR: “Why modular monolith now” (explicitly: hackathon speed + fewer moving parts).
- [x] Keep the *same* core data semantics from `ideas.md`, even without MQ:
  - [x] Canonical IDs: `asset_id`, `market_id` rules
  - [x] Canonical event envelope fields: `event_type`, `source`, `schema_version`, `observed_at`, `event_time`, `dedupe_key`, `dataset_id`, `run_id`, `payload`, `raw_payload`
  - [x] Numeric encoding: canonical event payload numbers as **decimal strings**; REST returns JSON numbers.
- [x] Decide the internal pipeline mechanism (recommended default):
  - [x] Background worker process inside backend repo
  - [x] Job queue choice:
    - [x] Recommended: Postgres-backed job table (no extra infra)
    - [ ] Alternative: Celery + Redis broker (if you want classic distributed queue)

---

## Backend Phase 1 - Bootstrap & Local Dev (Compose)

- [x] Create `infra/compose/docker-compose.yml` with:
  - [x] Postgres (named volume)
  - [ ] Authentik + Redis (optional profile; can be enabled later)
  - [x] Backend API container
  - [x] Backend worker container (same image, different command)
- [x] Define a stable port plan and document it in `README.md`.
- [x] Add `.env.example` (no secrets) with:
  - [x] DB URL
  - [x] OIDC issuer/JWKS URL (or Authentik URLs)
  - [x] LLM provider base URL + API key placeholders
  - [x] vendor API configuration placeholders
- [x] Add repo-level “golden commands” section:
  - [x] `uv sync`
  - [x] `docker compose up`
  - [x] `pytest`
  - [x] `ruff format && ruff check`

---

## Backend Phase 2 - Contracts (Pydantic) + DB Schema

Goal: lock the contracts early so everything else builds on stable types.

- [x] `src/fce/contracts/ids.py`:
  - [x] `AssetRef`, `TokenRef`, `MarketRef`
  - [x] `asset_id` and `market_id` codecs + validation helpers
- [x] `src/fce/contracts/events.py`:
  - [x] event envelope model + JSON serialization rules
  - [x] schema versioning scaffolding (upcasters)
- [x] Canonical payload models (v1):
  - [x] `market.price`, `market.ohlcv` (minimum required for prompts + fills)
  - [x] `sentiment.item`, `sentiment.item_summary`
  - [x] `llm.decision`, `llm.schedule_request`
  - [x] `sim.fill`, `portfolio.snapshot`
  - [x] `run.started`, `run.finished`, `run.failed`
- [x] Run config snapshot schema (match `ideas.md` draft; keep MVP constraint: 1 market + 1 model).

DB (SQLAlchemy + Alembic):

- [x] `events` append-only log table:
  - [x] unique dedupe indexes:
    - [x] `(dataset_id, event_type, dedupe_key)` where `dataset_id IS NOT NULL`
    - [x] `(run_id, event_type, dedupe_key)` where `run_id IS NOT NULL`
- [x] Core metadata tables:
  - [x] `users`
  - [x] `datasets` (status + params)
  - [x] `prompt_templates`
  - [x] `run_config_snapshots`
  - [x] `runs` (+ status timestamps)
  - [x] `run_datasets`
  - [x] `llm_calls` (full prompt/response audit)
- [x] Projection tables for fast UI reads (recommended even in MVP):
  - [x] `portfolio_snapshots` (run_id, observed_at, equity, cash, positions_json)
  - [ ] `sim_trades` (optional)
- [ ] Seed data strategy:
  - [ ] pinned watchlist markets (10 MarketRefs)
  - [ ] curated scenario windows (if Arena)

---

## Backend Phase 3 - Internal Job System (Pipeline Backbone)

Goal: all “pipelines” (dataset import, replay runs, tournament) run as background jobs inside backend.

- [x] Implement job table + worker loop (if Postgres-backed):
  - [x] claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED`
  - [x] heartbeats + timeout recovery
  - [x] concurrency caps (global and per-user) (best-effort; per-user depends on auth)
- [ ] Define job types:
  - [x] `dataset_import` (spot/perps/sentiment)
  - [x] `run_execute_replay`
  - [x] `run_execute_live` (global live run)
  - [ ] `arena_execute_submission` (optional)
- [x] Standardize job logging context:
  - [x] `job_id`, `dataset_id`, `run_id`
  - [ ] `user_id` (after auth / ownership)

---

## Backend Phase 4 - Dataset Import (Historical Backfill)

Goal: create datasets by pulling vendor history and writing canonical events directly to DB.

- [x] Dataset lifecycle:
  - [x] API creates `datasets` row in `pending`
  - [x] enqueue `dataset_import` job
  - [x] worker runs import, writes canonical events (`dataset_id` scoped), updates dataset status to `ready`/`failed`
- [x] Spot importer (MVP, DexScreener-seeded synthetic backfill) v1:
  - [x] `market.price` at 1m cadence (synthetic; for fills + valuation)
  - [x] `market.ohlcv` at 1h timeframe (synthetic; for prompt context)
  - [x] dedupe key rules (stable, time-bucketed)
  - [x] set `observed_at = event_time` for backfilled events
  - [ ] Real historical candle backfill (needs a provider with candles; DexScreener free API lacks it)
- [x] Sentiment importer v1:
  - [x] RSS/news backfill for window
  - [x] allow empty dataset (still create dataset_id)
  - [x] write `sentiment.item`
  - [x] generate `sentiment.item_summary` 1:1 using internal LLM module (store `llm_call_id`)
- [ ] Perps importer (Hyperliquid) (only if MVP includes perps):
  - [ ] backfill `perps.mark` + `perps.funding_rate`

---

## Backend Phase 5 - Replay Engine (Deterministic Stream from DB)

Goal: deterministic ordering + no lookahead.

- [x] Implement replay iterator:
  - [x] query events for dataset_ids within `[start, end]`
  - [x] stable ordering key: `(observed_at, source, event_type, dedupe_key)`
  - [x] stream events to orchestrator in-process (no MQ)
- [x] Add replay correctness tests:
  - [x] same DB contents -> same stream ordering
  - [x] dedupe/idempotency invariants hold on rerun

---

## Backend Phase 6 - Orchestrator (Internal Module)

Goal: consume replay/live events, build snapshots, call LLM, simulate, persist results.

- [x] Snapshot builder (matches `ideas.md` semantics):
  - [x] include only events with `observed_at <= tick_time`
  - [x] only use OHLCV after close (`bar_end <= tick_time`)
  - [x] require fresh price for fill pricing (age <= 60s; configurable)
- [x] Scheduler:
  - [x] base cadence 1h (anchored)
  - [x] early-check requests via `next_check_seconds` (clamped + aligned)
  - [x] always log schedule requests (even ignored)
- [x] Prompt builder:
  - [x] Mustache templates (no code execution)
  - [x] bounded market context + derived features
  - [x] bounded sentiment context (prefer summaries)
  - [x] include last 3 decision steps (memory window)
  - [x] prompt-only time masking option
- [x] Strict decision JSON parsing + validation:
  - [x] decimal parsing (number or string) -> Decimal -> persist as string
  - [x] MVP constraint: exactly 1 selected `market_id`
  - [x] invalid output => reject + hold last targets + record error

Persistence:

- [x] Write run-scoped canonical events directly to `events` (`run_id` scoped):
  - [x] `run.started` / `run.finished` / `run.failed`
  - [x] `llm.decision` / `llm.schedule_request`
  - [x] `sim.fill` / `portfolio.snapshot`
- [x] Maintain projection tables (`portfolio_snapshots`, `sim_trades`) for UI speed.

---

## Backend Phase 7 - Simulation + Guard Chain (Internal)

- [x] Implement rebalance-to-target exposure engine:
  - [x] compute target notional = exposure * equity
  - [x] simulate fills at snapshot price
  - [x] apply fee bps
- [x] Implement guard chain (single place, deterministic):
  - [x] spot long-only
  - [x] gross/net caps
  - [x] missing data policy (skip tick; hold last targets)
  - [x] decision validation failures => hold last targets
- [x] Deterministic tests for fills + portfolio snapshots.

---

## Backend Phase 8 - LLM Module (Gateway-Equivalent, In-Process)

Goal: centralize provider routing and audit logging without a separate service.

- [x] Implement internal `llm.call_chat_completion()`:
  - [x] provider routing (OpenAI-compatible; OpenRouter optional)
  - [x] retries + timeouts
  - [x] record `llm_calls` (prompt, response_raw, response_parsed, usage, latency, error)
  - [x] per-run and per-dataset budgets (hard caps in MVP; env-configured)
    - [x] max decision calls per run
    - [x] max summary calls per run
    - [x] max sentiment item summaries per dataset
    - [ ] per-user budgets (after auth / ownership)
- [x] Model allowlist:
  - [ ] admin-managed list in DB (no secrets in run snapshots)
  - [x] env-based allowlist in MVP (`FCE_LLM_MODEL_ALLOWLIST`)
  - [x] env-based secret storage in MVP

---

## Backend Phase 9 - API Surface (FastAPI)

Goal: the backend is the only public surface; everything else is internal modules/jobs.

- [ ] Auth (OIDC) (recommended to plan now, can ship later):
  - [ ] validate JWT via JWKS
  - [ ] auto-provision user row on `/me`
  - [ ] admin via group claim
- [ ] Endpoints (from `ideas.md`, adjusted for internal pipeline):
  - [x] `GET /me`
  - [x] `POST /datasets` (enqueues import job)
  - [x] `GET /datasets` / `GET /datasets/{id}`
  - [x] `POST /prompt_templates` / `GET /prompt_templates`
  - [x] `POST /runs` (validates config, stores snapshot, enqueues run job)
  - [x] `GET /runs` / `GET /runs/{id}`
  - [x] `POST /runs/{id}/stop` (signals worker via DB flag)
  - [x] `GET /runs/{id}/timeline` (from projections)
  - [x] `GET /runs/{id}/decisions` (paged from events)
  - [x] `GET /runs/{id}/summary`
  - [ ] optional Arena:
    - [ ] `GET /scenario_sets`
    - [ ] `POST /arena/submissions`
    - [ ] `GET /arena/submissions` / `GET /arena/submissions/{id}`
    - [ ] `GET /leaderboards`

---

## Backend Phase 10 - Live Mode (Curated Global Run)

Goal: one always-on live run for the main dashboard.

- [x] Implement live ingestion loop (still inside backend worker):
  - [x] poll vendor prices every `price_tick_seconds`
  - [x] write `market.price` events (run-scoped)
  - [x] build/write `market.ohlcv` bars (run-scoped)
- [x] Live run execution loop:
  - [x] anchored tick schedule + early-check support
  - [ ] optional early sentiment refresh (best effort)
  - [x] write run-scoped events and projections

---

## Backend Phase 11 - Observability, CI, and Guardrails

- [x] Structured JSON logs (worker) (consistent keys): `service`, `job_id`, `run_id`, `dataset_id`.
- [ ] Extend logs to API/orchestrator; include `event_type` when appending events.
- [ ] Prometheus metrics:
  - [ ] job queue depth, job latency, failures
  - [ ] DB write latency
  - [ ] LLM call counts/latency/errors/tokens
- [ ] CI:
  - [ ] `ruff`, typecheck, tests
  - [ ] Docker image build
- [ ] Security:
  - [ ] no secrets committed, `.env.example`
  - [ ] enforce run/dataset ownership
  - [ ] leaderboard only shows allowed fields

---

## Repo 2: `first-claw-eater-frontend` (Dashboard)

### Target shape (frontend repo)

```text
first-claw-eater-frontend/
├─ apps/web/                 # Next.js (App Router)
├─ packages/ui/              # optional shared components
├─ pnpm-workspace.yaml
├─ turbo.json                # optional; or keep it simple with plain scripts
├─ package.json
└─ README.md
```

Tooling:

- Next.js + React + TypeScript
- Data fetching: TanStack Query
- Runtime validation: Zod (optional for critical endpoints)
- OpenAPI TS generation: `openapi-typescript`
- Tests: Vitest + Playwright (optional in MVP)

Frontend TODO:

- [ ] Auth UI: OIDC login flow (Authentik) or dev token mode.
- [ ] Generate typed client from backend OpenAPI.
- [x] Live Dashboard page:
  - [x] price chart (TradingView widget or alternative)
  - [x] equity/PnL chart
  - [x] decisions timeline (rationale/confidence/key_signals)
- [x] Benchmark Lab:
  - [x] dataset import form + status
  - [x] run creation form + run status
  - [x] run timeline + decisions + summary
- [ ] Optional Arena views: submission progress + leaderboard.
- [x] Performance: pagination for decisions + stop polling terminal runs (MVP: polling).
- [ ] (Optional) pagination for raw events.

---

## Repo 3: `first-claw-eater-crawler` (Placeholder)

This repo is a **placeholder** so vendor adapters can be extracted cleanly later. For MVP, backend can own ingestion directly.

Recommended direction:

- Make it a Python package (`uv`) that exposes adapter interfaces + vendor client wrappers.
- Backend depends on it as a git dependency (later: publish to a registry if needed).

Crawler placeholder TODO:

- [x] Repo scaffold + README (“not required for MVP”).
- [ ] Define adapter interfaces that match `ideas.md` contracts:
  - [ ] `get_price`, `get_ohlcv`, optional perps endpoints
- [ ] Add one minimal DexScreener adapter stub (no production hardening yet).
- [ ] Add contract tests using recorded fixtures (so adapters stay deterministic).

---

## Cross-Repo Integration (How the 3 Repos Fit)

- [ ] Backend publishes OpenAPI; frontend generates types from it.
- [ ] Backend is the only runtime “system” in MVP; crawler repo is optional.
- [ ] Local dev recommendation:
  - [ ] run backend `docker compose up` (infra + api + worker)
  - [ ] run frontend `pnpm dev` pointing to backend API base URL

---

## MVP Demo-Ready Definition (Hackathon)

- [x] `docker compose up` in backend repo brings up Postgres + backend API + backend worker (and optionally Authentik).
- [x] User can import a historical dataset and run a replay benchmark (single `market_id`, single `model_key`).
- [x] Backend calls LLM on historical ticks and produces a PnL curve + decision stream + post-run summary.
- [x] Frontend shows Live Dashboard + Benchmark Lab results.
