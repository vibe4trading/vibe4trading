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
- [ ] Keep the *same* core data semantics from `ideas.md`, even without MQ:
  - [ ] Canonical IDs: `asset_id`, `market_id` rules
  - [ ] Canonical event envelope fields: `event_type`, `source`, `schema_version`, `observed_at`, `event_time`, `dedupe_key`, `dataset_id`, `run_id`, `payload`, `raw_payload`
  - [ ] Numeric encoding: canonical event payload numbers as **decimal strings**; REST returns JSON numbers.
- [ ] Decide the internal pipeline mechanism (recommended default):
  - [ ] Background worker process inside backend repo
  - [ ] Job queue choice:
    - [ ] Recommended: Postgres-backed job table (no extra infra)
    - [ ] Alternative: Celery + Redis broker (if you want classic distributed queue)

---

## Backend Phase 1 - Bootstrap & Local Dev (Compose)

- [ ] Create `infra/compose/docker-compose.yml` with:
  - [ ] Postgres (named volume)
  - [ ] Authentik + Redis (optional profile; can be enabled later)
  - [ ] Backend API container
  - [ ] Backend worker container (same image, different command)
- [ ] Define a stable port plan and document it in `README.md`.
- [ ] Add `.env.example` (no secrets) with:
  - [ ] DB URL
  - [ ] OIDC issuer/JWKS URL (or Authentik URLs)
  - [ ] LLM provider base URL + API key placeholders
  - [ ] vendor API configuration placeholders
- [ ] Add repo-level “golden commands” section:
  - [ ] `uv sync`
  - [ ] `docker compose up`
  - [ ] `pytest`
  - [ ] `ruff format && ruff check`

---

## Backend Phase 2 - Contracts (Pydantic) + DB Schema

Goal: lock the contracts early so everything else builds on stable types.

- [ ] `src/fce/contracts/ids.py`:
  - [ ] `AssetRef`, `TokenRef`, `MarketRef`
  - [ ] `asset_id` and `market_id` codecs + validation helpers
- [ ] `src/fce/contracts/events.py`:
  - [ ] event envelope model + JSON serialization rules
  - [ ] schema versioning scaffolding (upcasters)
- [ ] Canonical payload models (v1):
  - [ ] `market.price`, `market.ohlcv` (minimum required for prompts + fills)
  - [ ] `sentiment.item`, `sentiment.item_summary`
  - [ ] `llm.decision`, `llm.schedule_request`
  - [ ] `sim.fill`, `portfolio.snapshot`
  - [ ] `run.started`, `run.finished`, `run.failed`
- [ ] Run config snapshot schema (match `ideas.md` draft; keep MVP constraint: 1 market + 1 model).

DB (SQLAlchemy + Alembic):

- [ ] `events` append-only log table:
  - [ ] unique dedupe indexes:
    - [ ] `(dataset_id, event_type, dedupe_key)` where `dataset_id IS NOT NULL`
    - [ ] `(run_id, event_type, dedupe_key)` where `run_id IS NOT NULL`
- [ ] Core metadata tables:
  - [ ] `users`
  - [ ] `datasets` (status + params)
  - [ ] `prompt_templates`
  - [ ] `run_config_snapshots`
  - [ ] `runs` (+ status timestamps)
  - [ ] `run_datasets`
  - [ ] `llm_calls` (full prompt/response audit)
- [ ] Projection tables for fast UI reads (recommended even in MVP):
  - [ ] `portfolio_snapshots` (run_id, observed_at, equity, cash, positions_json)
  - [ ] `sim_trades` (optional)
- [ ] Seed data strategy:
  - [ ] pinned watchlist markets (10 MarketRefs)
  - [ ] curated scenario windows (if Arena)

---

## Backend Phase 3 - Internal Job System (Pipeline Backbone)

Goal: all “pipelines” (dataset import, replay runs, tournament) run as background jobs inside backend.

- [ ] Implement job table + worker loop (if Postgres-backed):
  - [ ] claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED`
  - [ ] heartbeats + timeout recovery
  - [ ] concurrency caps (global and per-user)
- [ ] Define job types:
  - [ ] `dataset_import` (spot/perps/sentiment)
  - [ ] `run_execute_replay`
  - [ ] `run_execute_live` (global live run)
  - [ ] `arena_execute_submission` (optional)
- [ ] Standardize job logging context: `job_id`, `dataset_id`, `run_id`, `user_id`.

---

## Backend Phase 4 - Dataset Import (Historical Backfill)

Goal: create datasets by pulling vendor history and writing canonical events directly to DB.

- [ ] Dataset lifecycle:
  - [ ] API creates `datasets` row in `pending`
  - [ ] enqueue `dataset_import` job
  - [ ] worker runs import, writes canonical events (`dataset_id` scoped), updates dataset status to `ready`/`failed`
- [ ] Spot importer (DexScreener) v1:
  - [ ] decide minimal needed data for MVP:
    - [ ] `market.price` at 1m cadence (for fills + valuation)
    - [ ] `market.ohlcv` at 1h timeframe (for prompt context)
  - [ ] dedupe key rules (stable, time-bucketed)
  - [ ] set `observed_at = event_time` for backfilled events
- [ ] Sentiment importer v1:
  - [ ] RSS/news backfill for window
  - [ ] allow empty dataset (still create dataset_id)
  - [ ] write `sentiment.item`
  - [ ] generate `sentiment.item_summary` 1:1 using internal LLM module (store `llm_call_id`)
- [ ] Perps importer (Hyperliquid) (only if MVP includes perps):
  - [ ] backfill `perps.mark` + `perps.funding_rate`

---

## Backend Phase 5 - Replay Engine (Deterministic Stream from DB)

Goal: deterministic ordering + no lookahead.

- [ ] Implement replay iterator:
  - [ ] query events for dataset_ids within `[start, end]`
  - [ ] stable ordering key: `(observed_at, source, event_type, dedupe_key)`
  - [ ] stream events to orchestrator in-process (no MQ)
- [ ] Add replay correctness tests:
  - [ ] same DB contents -> same stream ordering
  - [ ] dedupe/idempotency invariants hold on rerun

---

## Backend Phase 6 - Orchestrator (Internal Module)

Goal: consume replay/live events, build snapshots, call LLM, simulate, persist results.

- [ ] Snapshot builder (matches `ideas.md` semantics):
  - [ ] include only events with `observed_at <= tick_time`
  - [ ] only use OHLCV after close (`bar_end <= tick_time`)
  - [ ] require fresh price for fill pricing (age <= 60s; configurable)
- [ ] Scheduler:
  - [ ] base cadence 1h (anchored)
  - [ ] early-check requests via `next_check_seconds` (clamped + aligned)
  - [ ] always log schedule requests (even ignored)
- [ ] Prompt builder:
  - [ ] Mustache templates (no code execution)
  - [ ] bounded market context + derived features
  - [ ] bounded sentiment context (prefer summaries)
  - [ ] include last 3 decision steps (memory window)
  - [ ] prompt-only time masking option
- [ ] Strict decision JSON parsing + validation:
  - [ ] decimal parsing (number or string) -> Decimal -> persist as string
  - [ ] MVP constraint: exactly 1 selected `market_id`
  - [ ] invalid output => reject + hold last targets + record error

Persistence:

- [ ] Write run-scoped canonical events directly to `events` (`run_id` scoped):
  - [ ] `run.started` / `run.finished` / `run.failed`
  - [ ] `llm.decision` / `llm.schedule_request`
  - [ ] `sim.fill` / `portfolio.snapshot`
- [ ] Maintain projection tables (`portfolio_snapshots`, `sim_trades`) for UI speed.

---

## Backend Phase 7 - Simulation + Guard Chain (Internal)

- [ ] Implement rebalance-to-target exposure engine:
  - [ ] compute target notional = exposure * equity
  - [ ] simulate fills at snapshot price
  - [ ] apply fee bps
- [ ] Implement guard chain (single place, deterministic):
  - [ ] spot long-only
  - [ ] gross/net caps
  - [ ] missing data policy (skip tick; hold last targets)
  - [ ] decision validation failures => hold last targets
- [ ] Deterministic tests for fills + portfolio snapshots.

---

## Backend Phase 8 - LLM Module (Gateway-Equivalent, In-Process)

Goal: centralize provider routing and audit logging without a separate service.

- [ ] Implement internal `llm.call_chat_completion()`:
  - [ ] provider routing (OpenAI-compatible; OpenRouter optional)
  - [ ] retries + timeouts
  - [ ] record `llm_calls` (prompt, response_raw, response_parsed, usage, latency, error)
  - [ ] per-run and per-user budgets (hard caps in MVP)
- [ ] Model allowlist:
  - [ ] admin-managed list in DB (no secrets in run snapshots)
  - [ ] env-based secret storage in MVP

---

## Backend Phase 9 - API Surface (FastAPI)

Goal: the backend is the only public surface; everything else is internal modules/jobs.

- [ ] Auth (OIDC) (recommended to plan now, can ship later):
  - [ ] validate JWT via JWKS
  - [ ] auto-provision user row on `/me`
  - [ ] admin via group claim
- [ ] Endpoints (from `ideas.md`, adjusted for internal pipeline):
  - [ ] `GET /me`
  - [ ] `POST /datasets` (enqueues import job)
  - [ ] `GET /datasets` / `GET /datasets/{id}`
  - [ ] `POST /prompt_templates` / `GET /prompt_templates`
  - [ ] `POST /runs` (validates config, stores snapshot, enqueues run job)
  - [ ] `GET /runs` / `GET /runs/{id}`
  - [ ] `POST /runs/{id}/stop` (signals worker via DB flag)
  - [ ] `GET /runs/{id}/timeline` (from projections)
  - [ ] `GET /runs/{id}/decisions` (paged from events)
  - [ ] `GET /runs/{id}/summary`
  - [ ] optional Arena:
    - [ ] `GET /scenario_sets`
    - [ ] `POST /arena/submissions`
    - [ ] `GET /arena/submissions` / `GET /arena/submissions/{id}`
    - [ ] `GET /leaderboards`

---

## Backend Phase 10 - Live Mode (Curated Global Run)

Goal: one always-on live run for the main dashboard.

- [ ] Implement live ingestion loop (still inside backend worker):
  - [ ] poll vendor prices every 60s
  - [ ] write `market.price` events (dataset_id = live dataset)
- [ ] Live run execution loop:
  - [ ] anchored tick schedule
  - [ ] optional early sentiment refresh (best effort)
  - [ ] write run-scoped events and projections

---

## Backend Phase 11 - Observability, CI, and Guardrails

- [ ] Structured JSON logs (consistent keys): `service`, `job_id`, `run_id`, `dataset_id`, `event_type`.
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
- [ ] Live Dashboard page:
  - [ ] price chart (TradingView widget or alternative)
  - [ ] equity/PnL chart
  - [ ] decisions timeline (rationale/confidence/key_signals)
- [ ] Benchmark Lab:
  - [ ] dataset import form + status
  - [ ] run creation form + run status
  - [ ] run timeline + decisions + summary
- [ ] Optional Arena views: submission progress + leaderboard.
- [ ] Performance: pagination for decisions/events; polling strategy (MVP: polling).

---

## Repo 3: `first-claw-eater-crawler` (Placeholder)

This repo is a **placeholder** so vendor adapters can be extracted cleanly later. For MVP, backend can own ingestion directly.

Recommended direction:

- Make it a Python package (`uv`) that exposes adapter interfaces + vendor client wrappers.
- Backend depends on it as a git dependency (later: publish to a registry if needed).

Crawler placeholder TODO:

- [ ] Repo scaffold + README (“not required for MVP”).
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

- [ ] `docker compose up` in backend repo brings up Postgres + backend API + backend worker (and optionally Authentik).
- [ ] User can import a historical dataset and run a replay benchmark (single `market_id`, single `model_key`).
- [ ] Backend calls LLM on historical ticks and produces a PnL curve + decision stream + post-run summary.
- [ ] Frontend shows Live Dashboard + Benchmark Lab results.
