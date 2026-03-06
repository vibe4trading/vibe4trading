## Vibe4Trading Product, Architecture, and Software Stack

### What this product is

Vibe4Trading is an LLM-native crypto strategy benchmarking platform.

Its core job is to let a user pick a market, a model, and a prompt-driven trading style, then evaluate that strategy in a controlled environment before trusting it in the wild. The platform combines historical replay, tournament-style benchmarking, leaderboard ranking, and early live-run infrastructure in one system.

At a product level, it answers a simple question:

"Is this AI trading strategy actually good, or did it just get lucky in one market window?"

### Product thesis

- Crypto trading is becoming agent-driven, not just human-driven.
- There are too many models, prompts, tokens, and market regimes to evaluate manually.
- A useful AI trading platform must test the same strategy across repeatable, comparable windows.
- The winning product is not just an execution bot; it is a benchmarking and decision-quality platform.

### Core value proposition

Vibe4Trading gives users a way to:

- benchmark an AI trading strategy against historical data
- compare strategies across consistent market regimes
- rank models and prompts on a public or internal leaderboard
- understand not only return, but also behavior, drawdown, consistency, and style

### Target users

- retail crypto traders experimenting with AI-driven prompts
- quant-minded builders testing model behavior
- teams comparing multiple LLM providers or prompt variants
- operators who need a safer paper-trading loop before live deployment

## Product surface

### 1. Landing and product framing

The landing experience positions the product as a trial ground for AI trading agents, with strong emphasis on testing, repeated evaluation, and historical scenario coverage.

Evidence:

- `vibe4trading-frontend/src/app/page.tsx`
- `vibe4trading-frontend/src/app/components/landing/LandingPage.tsx`

The landing page messaging centers on:

- picking a model and market
- stress-testing the agent across historical windows
- receiving a verdict
- optimizing and competing on a leaderboard

### 2. Replay runs

Replay runs are the main single-strategy evaluation flow.

Users can create a run by choosing:

- a `market_id`
- a `model_key`
- dataset references for market and sentiment inputs
- prompt text
- optionally a richer decision schema with risk level and holding period

The backend replays historical events, reconstructs context at each tick, calls the LLM, validates the result, runs a paper simulation, and stores decisions, portfolio snapshots, and summary output.

Evidence:

- frontend create/list page: `vibe4trading-frontend/src/app/runs/page.tsx`
- run detail page: `vibe4trading-frontend/src/app/runs/[runId]/page.tsx`
- watch mode: `vibe4trading-frontend/src/app/runs/[runId]/watch/page.tsx`
- API route: `vibe4trading-backend/src/v4t/api/routes/runs.py`
- replay engine: `vibe4trading-backend/src/v4t/orchestrator/replay_run.py`

What users get from a replay run:

- run status and timestamps
- equity curve
- market price series
- decision feed
- final summary text
- watch-mode playback of streaming LLM output and portfolio updates

### 3. Arena / trials / tournament benchmarking

Arena is the product's strongest differentiator.

Instead of judging a strategy on one backtest, the system expands a single submission into multiple scenario windows and aggregates the result into a benchmark-style report.

This means users are not only asking whether a prompt made money once, but whether it survives across multiple market regimes.

Evidence:

- arena page: `vibe4trading-frontend/src/app/arena/page.tsx`
- submission detail page: `vibe4trading-frontend/src/app/arena/submissions/[submissionId]/page.tsx`
- arena API: `vibe4trading-backend/src/v4t/api/routes/arena.py`
- arena runner: `vibe4trading-backend/src/v4t/arena/runner.py`
- arena reporting: `vibe4trading-backend/src/v4t/arena/reporting.py`

Arena does all of the following:

- accepts a single user strategy submission
- maps it to a hardcoded scenario set
- creates one replay run per window
- executes each run
- aggregates returns and behavior
- computes leaderboard-friendly metrics
- generates a structured narrative report

In the current code, the main scenario sets are Python-defined rather than user-configurable:

- `default-v1`: 10 x 12-hour windows for fast demos
- `crypto-benchmark-v1`: 10 x 7-day windows for longer benchmark batches

This is the clearest product story for a pitch:

"We benchmark AI trading agents across fixed historical stress windows, then score, rank, and explain their behavior."

### 4. Leaderboard

The leaderboard turns the system from a private testing tool into a competitive benchmarking platform.

Evidence:

- leaderboard UI: `vibe4trading-frontend/src/app/leaderboard/page.tsx`
- backend endpoint: `vibe4trading-backend/src/v4t/api/routes/arena.py`

It exposes:

- ranking by total return
- filters by model and market
- supporting metrics like Sharpe, drawdown, win rate, profit factor, and trade count
- side-panel inspection of the selected strategy

### 5. Live run infrastructure

The backend supports live runs, but the frontend experience is not yet a full live operations dashboard.

Evidence:

- backend live routes: `vibe4trading-backend/src/v4t/api/routes/live.py`
- backend live orchestrator: `vibe4trading-backend/src/v4t/orchestrator/live_run.py`
- frontend `/live`: `vibe4trading-frontend/src/app/live/page.tsx`

Important product truth:

- live execution infrastructure exists in the backend
- a live worker queue is isolated for long-running jobs
- the current `/live` UI is largely placeholder/styled art, not a full live telemetry console

For pitching, this should be framed as:

- current state: backend-ready live paper-trading engine
- next milestone: fully operational live dashboard and controls

### 6. Admin model governance

The product includes internal controls for model onboarding and per-user model access.

Evidence:

- admin model page: `vibe4trading-frontend/src/app/admin/models/page.tsx`
- admin model routes: `vibe4trading-backend/src/v4t/api/routes/admin_models.py`
- per-user model access: `vibe4trading-backend/src/v4t/api/routes/admin_model_access.py`

This is strategically important because it shows the system is not hardcoded to one model provider. It has the beginnings of a model registry and governance layer.

### 7. Dataset ingestion and operator tooling

The platform includes an operator-facing ingestion pipeline for bringing in historical price and sentiment data.

Evidence:

- import docs: `data-loader/README.md`
- dataset API: `vibe4trading-backend/src/v4t/api/routes/datasets.py`
- import dispatcher: `vibe4trading-backend/src/v4t/ingest/dataset_import.py`

Supported input patterns include:

- spot demo data
- DexScreener-seeded synthetic spot data
- Freqtrade feather files for historical OHLCV
- RSS news feeds for sentiment
- tweets-based sentiment datasets
- empty sentiment datasets for controlled experiments

## Architecture overview

### Architecture style

The backend is a modular monolith deployed as multiple cooperating processes.

This is a strong early-stage architecture choice because it keeps:

- one codebase
- one shared schema and contract set
- one domain model

while still separating:

- synchronous API traffic
- asynchronous heavy jobs
- long-lived live jobs
- periodic maintenance

Evidence:

- `vibe4trading-backend/ARCHITECTURE.md`
- `vibe4trading-backend/src/v4t/api/app.py`
- `vibe4trading-backend/src/v4t/worker/celery_app.py`

### Architecture evolution

The repository notes show that the team originally considered a more distributed architecture with separate services and a message-queue backbone, but the current implementation intentionally simplifies that into an internal pipeline inside the backend.

That distinction matters for both diagrams and pitch talk:

- original concept: more explicit microservice split and MQ-centric flow
- current shipped shape: modular monolith plus Celery/Redis process separation
- strategic takeaway: the codebase is optimized for MVP speed now, while preserving separable module boundaries for later extraction

Evidence:

- original architecture notes: `ideas.md`
- reduced-scope implementation plan: `todo.md`
- shipped backend structure: `vibe4trading-backend/src/v4t`

### Runtime topology

The deployed system is effectively:

1. Next.js frontend
2. FastAPI backend API
3. Celery default worker
4. Celery live worker
5. Celery Beat scheduler
6. PostgreSQL database
7. Redis broker/result backend

Evidence:

- `vibe4trading-backend/infra/compose/docker-compose.yml`
- `vibe4trading-backend/README.md`

### Major layers

#### Frontend layer

Responsibilities:

- user interface
- auth session shell
- backend proxying
- route-based workflows for runs, arena, leaderboard, admin
- WebSocket/poll-based refresh logic

Evidence:

- `vibe4trading-frontend/src/app/layout.tsx`
- `vibe4trading-frontend/src/app/api/v4t/[...path]/route.ts`
- `vibe4trading-frontend/src/app/lib/realtime.ts`

#### API layer

Responsibilities:

- request validation
- auth enforcement
- model eligibility checks
- dataset/run/submission row creation
- job enqueueing
- streaming read endpoints for run progress

Evidence:

- `vibe4trading-backend/src/v4t/api/app.py`
- `vibe4trading-backend/src/v4t/api/routes/runs.py`
- `vibe4trading-backend/src/v4t/api/routes/arena.py`
- `vibe4trading-backend/src/v4t/api/routes/live.py`

#### Job orchestration layer

Responsibilities:

- durable job persistence
- Celery dispatch
- retry semantics
- stale-job recovery
- queue isolation by workload

Evidence:

- `vibe4trading-backend/src/v4t/jobs/repo.py`
- `vibe4trading-backend/src/v4t/worker/tasks.py`
- `vibe4trading-backend/src/v4t/worker/job_executor.py`
- `vibe4trading-backend/src/v4t/worker/reconcile.py`

#### Domain execution layer

Responsibilities:

- historical replay execution
- live run loop execution
- arena fan-out and aggregation
- prompt context construction
- decision validation
- portfolio simulation

Evidence:

- `vibe4trading-backend/src/v4t/orchestrator/replay_run.py`
- `vibe4trading-backend/src/v4t/orchestrator/live_run.py`
- `vibe4trading-backend/src/v4t/orchestrator/run_base.py`
- `vibe4trading-backend/src/v4t/arena/runner.py`

#### Data and event layer

Responsibilities:

- system-of-record persistence
- append-only event logging
- run snapshots
- LLM call audit trail
- arena submission tracking

Evidence:

- `vibe4trading-backend/src/v4t/db/models.py`
- `vibe4trading-backend/src/v4t/db/event_store.py`

### Event-driven backbone

One of the most important architectural traits is that the system stores canonical events, not just final outcomes.

That includes:

- `market.price`
- `market.ohlcv`
- `sentiment.item`
- `sentiment.item_summary`
- `llm.stream_start`
- `llm.stream_delta`
- `llm.stream_end`
- `llm.decision`
- `portfolio.snapshot`
- `run.started`
- `run.finished`
- `run.failed`

This design gives the product strong replayability, auditability, and UI streaming support.

Evidence:

- event schema/table: `vibe4trading-backend/src/v4t/db/models.py`
- append logic: `vibe4trading-backend/src/v4t/db/event_store.py`
- run streaming endpoints: `vibe4trading-backend/src/v4t/api/routes/runs.py`

### Durable job model plus Celery transport

The system does not rely on Celery alone as the source of truth.

Instead:

- the database stores `JobRow`
- Celery is the execution transport
- retries, terminal state, and parent-entity recovery are reflected back into Postgres

This is a strong production-oriented choice because it preserves user-visible state even when workers crash or tasks retry.

Evidence:

- `vibe4trading-backend/ARCHITECTURE.md`
- `vibe4trading-backend/src/v4t/db/models.py`
- `vibe4trading-backend/src/v4t/worker/job_executor.py`

## End-to-end data flow

### Flow A: replay run

1. Frontend posts to `/api/v4t/runs`
2. Next.js proxy forwards to FastAPI
3. API validates user, model, and datasets
4. API creates `RunRow`, `RunConfigSnapshotRow`, and `JobRow`
5. API dispatches Celery task for replay execution
6. Worker loads historical dataset events from Postgres
7. Orchestrator builds prompt context
8. LLM gateway requests a decision from either:
   - stub model, or
   - OpenAI-compatible external model endpoint
9. Decision is validated against risk and leverage caps
10. Simulator rebalances portfolio
11. Events and snapshots are written to Postgres
12. Frontend reads updates through polling, WebSocket, or SSE
13. Summary is generated and run is marked finished

### Flow B: arena submission

1. User submits one strategy to arena
2. API creates `ArenaSubmissionRow` and a job
3. Worker expands that submission into many replay windows
4. Each window runs through the replay engine
5. The system collects per-window returns and behavior metrics
6. Aggregate metrics are computed
7. An arena report is generated
8. Submission is ranked on leaderboard

### Flow C: live run

1. User starts a live run through `/live/run`
2. API creates a live-configured run and enqueues it on the `live` queue
3. Dedicated live worker executes a long-running loop
4. Price source comes from demo mode or DexScreener
5. On scheduled ticks, the orchestrator builds prompt context and requests a decision
6. Simulator updates state and snapshots
7. Run continues until stop is requested

## Product strengths visible in code

### 1. Benchmarking is the real product, not generic chat-on-a-chart

The product is opinionated around repeated evaluation across windows, especially in arena mode. That is much stronger than a basic trading dashboard.

### 2. Strong audit trail

The system stores decisions, model calls, events, snapshots, and job state. That creates a reviewable history instead of opaque bot behavior.

### 3. Model governance exists already

The platform already supports:

- model registry
- enable/disable controls
- env-defined default model
- user-specific access restrictions

That matters if this becomes a multi-tenant or enterprise-facing product.

### 4. Deterministic replay mindset

The architecture is clearly designed around reproducibility and no-lookahead-style context building.

### 5. Separation of live jobs from batch jobs

Putting live execution on its own queue is a good operational decision. It protects batch workloads from being blocked by long-running loops.

### 6. Fairness controls in arena benchmarking

Arena scenario datasets are deterministically derived from the scenario-set key, market, and window timestamps. That means multiple submissions can be judged against the same replay slices instead of silently drifting onto different data.

## Product maturity and caveats

### Implemented and strong

- replay runs
- arena submissions
- leaderboard
- model admin and access controls
- dataset ingestion framework
- event streaming for run progress
- LLM gateway with stub fallback, budgets, retries, and concurrency controls

### Implemented but still maturing

- live trading UX, because backend support is ahead of frontend telemetry polish
- reporting polish, because some narratives are LLM-assisted and some are deterministic fallback
- ops packaging, because docs mention deployment elements that are not fully reflected in the current compose file and DB setup still bootstraps via `init_db` rather than a full migration workflow
- benchmark configurability, because scenario sets are code-defined today rather than fully operator-configurable

### Modeled but not fully surfaced

- prompt templates exist in DB models and frontend types, but there is no active prompt-template API route in `api/app.py` and no live page under the current frontend route tree
- datasets have backend APIs and ingestion paths, but there is no user-facing datasets page in the current frontend route tree
- broader benchmark ambitions such as richer leverage/futures-style evaluation appear in `CRYPTO_BENCHMARK_SPEC.md`, but the shipped engine should still be described as spot-oriented and long-only unless proven otherwise in code

### Documentation inconsistencies worth knowing

- frontend README references prompt-template pages, but those pages are not currently exposed in the route tree I inspected
- frontend README advertises realtime WebSocket support correctly, but some route descriptions overstate productized surfaces such as `/live` and `/prompt-templates`
- backend docs describe a `migrate` service and Alembic-based flow, but current compose does not define that service and `v4t.db.init_db` still relies on `Base.metadata.create_all()` plus targeted `ALTER TABLE` bootstrap steps
- product notes describe a broader MQ and microservice topology, but the current implementation is an internal-pipeline modular monolith with Celery and Redis

These are not fatal issues, but they should not be pitched as finished product capabilities.

## Software stack

### Frontend stack

- Next.js 16
- React 19
- TypeScript
- NextAuth 5 beta
- Tailwind CSS 4
- ESLint 9
- Vitest
- Playwright

Evidence:

- `vibe4trading-frontend/package.json`
- `vibe4trading-frontend/vitest.config.ts`
- `vibe4trading-frontend/playwright.config.ts`
- `vibe4trading-frontend/eslint.config.mjs`

### Backend stack

- Python 3.12
- FastAPI
- Uvicorn
- Celery with Redis
- SQLAlchemy 2
- Pydantic 2
- pydantic-settings
- psycopg 3
- structlog
- httpx
- tenacity
- Nautilus Trader
- pandas for Freqtrade import
- uv for dependency and environment management

Evidence:

- `vibe4trading-backend/pyproject.toml`
- `vibe4trading-backend/Dockerfile`

### Persistence and infrastructure

- PostgreSQL 16
- Redis 7
- Docker Compose

Evidence:

- `vibe4trading-backend/infra/compose/docker-compose.yml`

### Authentication and identity

- Authentik OIDC on the frontend via NextAuth
- backend JWT validation through configured OIDC issuer and JWKS
- backend-issued API tokens for automation

Evidence:

- `vibe4trading-frontend/src/auth.ts`
- `vibe4trading-backend/src/v4t/auth/deps.py`
- `vibe4trading-backend/src/v4t/api/routes/me.py`

### Data vendors and integrations

- OpenAI-compatible LLM providers
- DexScreener
- RSS feeds
- Freqtrade-generated OHLCV data
- tweets-based sentiment input

Evidence:

- `vibe4trading-backend/src/v4t/llm/gateway.py`
- `vibe4trading-backend/src/v4t/ingest/dexscreener.py`
- `vibe4trading-backend/src/v4t/ingest/rss.py`
- `vibe4trading-backend/src/v4t/ingest/freqtrade.py`
- `vibe4trading-backend/src/v4t/ingest/tweets.py`

### Quality and testing stack

- backend uses pytest, Ruff, and strict Pyright
- frontend uses ESLint, Vitest, and Playwright
- backend test suite includes unit, API, worker, ingestion, and end-to-end scenarios

Evidence:

- `vibe4trading-backend/pyproject.toml`
- `vibe4trading-backend/pyrightconfig.json`
- `vibe4trading-backend/tests/`
- `vibe4trading-frontend/e2e/`

## Architecture diagram ingredients

If you are generating an architecture diagram, the main boxes should be:

1. User / Browser
2. Next.js Web App
3. Next.js Auth + API Proxy
4. FastAPI Backend API
5. Postgres
6. Redis
7. Celery Default Worker
8. Celery Live Worker
9. Celery Beat
10. LLM Provider Gateway
11. DexScreener
12. RSS / Tweets / Freqtrade data sources

Key arrows:

- browser -> Next.js
- Next.js -> FastAPI
- FastAPI -> Postgres
- FastAPI -> Redis/Celery dispatch
- Celery workers -> Postgres
- workers -> LLM provider
- live worker -> DexScreener
- ingestion -> Freqtrade files / RSS / tweets
- frontend realtime views <- FastAPI via WebSocket/SSE/polling

## Pitch narrative

### One-line pitch

Vibe4Trading is a benchmarking platform for AI crypto trading agents, designed to test prompts and models across repeatable market regimes before they go live.

### Short pitch

Most AI trading products focus on generating signals. Vibe4Trading focuses on proving whether those signals hold up. It lets a user pick a model, prompt, and market, replay that strategy across historical windows, aggregate the result into a benchmark report, and compare performance on a leaderboard. Under the hood, it combines event-sourced replay, LLM decision orchestration, paper simulation, and tournament-style evaluation.

### Strong differentiators for a talk track

- benchmark-first instead of signal-first
- repeatable historical trial windows
- model and prompt comparison in one platform
- event-level auditability
- path from replay to live infrastructure

### Honest roadmap framing

What exists now:

- replay lab
- arena benchmarking
- leaderboard
- model governance
- ingestion pipeline
- backend live-run engine

What is next:

- full live dashboard experience
- stronger prompt-template productization
- more polished operator workflows and deployment packaging
