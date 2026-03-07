# Crypto Trading Benchmark System - Implementation Spec

## Context

The vibe4trading backend currently supports:
- **Replay mode**: Historical backtesting with spot-only, long-only positions
- **Live mode**: Real-time paper trading with demo price feeds
- **Decision schema v1**: Simple spot exposure targets (0.0-1.0), no leverage, no shorts
- **Fixed tick scheduling**: 4-hour base cadence, no LLM-controlled tick scheduling
- **Sentiment integration**: Works in replay, empty in live

The system uses:
- Nautilus Trader for simulation (cash account model)
- PostgreSQL event store for all market/sentiment/decision data
- Celery workers for async job execution
- FastAPI for REST + SSE streaming

## Goal

Extend the engine to support a **crypto trading benchmark** where:
1. Multiple LLMs compete across 10 tokens × 10 event windows (100 runs per user config)
2. Each run lasts 168 hours (7 days) with 4-hour base ticks
3. LLMs can trade SPOT (long-only) or FUTURES (long/short with leverage up to 100x)
4. LLMs specify stop-loss and take-profit levels that execute automatically
5. Risk levels 1-5 control max leverage, shorting permissions, and exposure caps
6. Holding periods (intraday/swing/position) influence trading style

## Target Schema

### System Prompt (injected by engine)

```
You are a crypto trading decision engine for a strategy benchmark.

RULES:
1. You manage exactly ONE position: {TOKEN}/USDT on Binance.
2. You can trade SPOT (long only, exposure 0.0 to 1.0) or FUTURES (long/short with leverage).
3. You receive market data, sentiment signals, portfolio state, and your recent decisions.
4. You must return ONLY a valid JSON object matching schema_version=2.
5. Do not explain. Do not add markdown. Do not add text outside the JSON.

DECISION FRAMEWORK:
- Read the user's strategy instructions carefully. They define your risk tolerance, leverage limits, and whether shorting is allowed.
- Use price data (OHLCV, momentum, returns) for technical signals.
- Use sentiment summaries (KOL tweets, news, on-chain signals) for narrative context.
- Use portfolio state to understand current exposure and P&L.
- Use your recent decisions to maintain consistency and avoid flip-flopping.
- The "confidence" field (0.0 to 1.0) reflects how sure you are. Low confidence = smaller position changes.

EXPOSURE RULES:
- mode="spot": target value must be 0.0 to 1.0. No leverage. Long only.
- mode="futures": target value can be negative (short). abs(value) must not exceed leverage.
- Positive value = long. Negative value = short. Zero = flat/close all.
- Move gradually unless there is an extreme signal.

EXAMPLES:
- Go 50% long spot: {"target":0.5,"mode":"spot","leverage":1,...}
- Go 3x leveraged long: {"target":3.0,"mode":"futures","leverage":3,...}
- Go 2x short: {"target":-2.0,"mode":"futures","leverage":2,...}
- Close everything: {"target":0.0,"mode":"spot","leverage":1,...}

RISK MANAGEMENT:
- stop_loss_pct: if price moves this % against you, position auto-closes.
- take_profit_pct: if price moves this % in your favor, position auto-closes.
- Both are optional but strongly recommended.
- If leveraged and price hits liquidation (entry ± 100%/leverage), you lose all margin.

OUTPUT FORMAT — return ONLY this JSON:
{
  "schema_version": 2,
  "target": <float>,
  "mode": "spot" | "futures",
  "leverage": <int 1-100>,
  "stop_loss_pct": <float or null>,
  "take_profit_pct": <float or null>,
  "confidence": <float 0.0-1.0>,
  "key_signals": ["signal_1", "signal_2"],
  "rationale": "<1-2 sentence explanation, under 50 words>"
}
```

### User Prompt Template (assembled by engine each tick)

```
{USER_STRATEGY_PROMPT}

Market:
market_id={TOKEN}/USDT
tick_time={CURRENT_TIMESTAMP}

Latest price:
- observed_at={TIMESTAMP}
- price={PRICE}

Recent OHLCV bars (timeframe=1h) (oldest->newest):
{OHLCV_BARS}

Recent closes (oldest->newest):
{CLOSE_PRICES}

Features:
- momentum={MOMENTUM_VALUE}
- return_pct={RETURN_PCT}

Portfolio:
- equity_quote={TOTAL_EQUITY}
- cash_quote={AVAILABLE_CASH}
- position_mode={spot|futures|none}
- position_direction={long|short|flat}
- position_qty_base={POSITION_SIZE}
- position_leverage={LEVERAGE}
- entry_price={ENTRY_PRICE}
- current_price={CURRENT_PRICE}
- liquidation_price={LIQ_PRICE_OR_NA}
- unrealized_pnl={UNREALIZED_PNL}
- unrealized_pnl_pct={UNREALIZED_PNL_PCT}%
- funding_cost_accumulated={FUNDING_COST}
- stop_loss_price={SL_PRICE_OR_NA}
- take_profit_price={TP_PRICE_OR_NA}

Recent sentiment summaries:
{SENTIMENT_ITEMS}

Recent decisions:
{PAST_DECISIONS}

Return ONLY a JSON object like:
{"schema_version":2,"target":0.5,"mode":"spot","leverage":1,"stop_loss_pct":5.0,"take_profit_pct":10.0,"confidence":0.6,"key_signals":["..."],"rationale":"..."}
```

### Decision Output Schema v2

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["schema_version", "target", "mode", "confidence", "key_signals", "rationale"],
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 2
    },
    "target": {
      "type": "number",
      "minimum": -100.0,
      "maximum": 100.0
    },
    "mode": {
      "type": "string",
      "enum": ["spot", "futures"]
    },
    "leverage": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 1
    },
    "stop_loss_pct": {
      "type": ["number", "null"],
      "minimum": 0.0,
      "maximum": 50.0
    },
    "take_profit_pct": {
      "type": ["number", "null"],
      "minimum": 0.0,
      "maximum": 200.0
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "key_signals": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "maxItems": 5
    },
    "rationale": {
      "type": "string",
      "maxLength": 300
    }
  },
  "additionalProperties": false
}
```

### Risk Level Constraints (enforced by engine)

| Risk Level | Mode allowed | Max leverage | Short allowed | Max abs(exposure) |
|------------|--------------|--------------|---------------|-------------------|
| 1          | spot only    | 1            | NO            | 0.5               |
| 2          | spot only    | 1            | NO            | 0.7               |
| 3          | spot+futures | 5            | YES           | 5.0               |
| 4          | spot+futures | 20           | YES           | 20.0              |
| 5          | spot+futures | 100          | YES           | 100.0             |

### User Strategy Prompts (beginner mode templates)

**Risk Level 1 — Ultra Conservative:**
```
You are a conservative crypto trader. Prioritize capital preservation above all else. SPOT ONLY — no leverage, no shorting. Only increase exposure when momentum is clearly positive AND sentiment is bullish for multiple hours. Reduce exposure immediately at any negative signal. Prefer staying in cash. Maximum exposure: 0.5. Move in small increments (0.1-0.2 steps). Use tight stop-loss (2%).
```

**Risk Level 2 — Conservative:**
```
You are a conservative crypto trader. Prioritize capital preservation. SPOT ONLY — no leverage, no shorting. Increase exposure gradually when momentum and sentiment align positively. Reduce on negative signals. Maximum exposure: 0.7. Move in 0.15-0.25 steps. Use stop-loss at 3%.
```

**Risk Level 3 — Moderate:**
```
You are a balanced crypto trader. You can use FUTURES with leverage up to 5x. Shorting is allowed. Go long when momentum is positive and sentiment is supportive. Short when momentum is negative and sentiment is bearish. Prefer gradual position changes. Maximum exposure: 5.0 (with leverage). Move in 0.5-1.0 steps. Use stop-loss at 5%. Take-profit at 2:1 ratio.
```

**Risk Level 4 — Aggressive:**
```
You are an aggressive crypto trader. You can use FUTURES with leverage up to 20x. Shorting is allowed. Take large positions when momentum and sentiment are favorable. Hold through minor dips if trend is intact. Short aggressively during clear downtrends. Only reduce on strong reversal signals. Maximum exposure: 20.0 (with leverage). Move in 1.0-5.0 steps. Use stop-loss at 8%.
```

**Risk Level 5 — Full Degen:**
```
You are a maximum aggression crypto trader. You can use FUTURES with leverage up to 100x. Shorting is allowed. Go max long on any positive signal. Go max short on any negative signal. Hold through volatility. Your goal is maximum returns, not capital preservation. Maximum exposure: 100.0 (with leverage). Move in 5.0-20.0 steps. Stop-loss at 15% or none if conviction is extreme.
```

### Holding Period Modifiers (appended to strategy prompt)

**INTRADAY (1-4H):**
```
Trading style: intraday. React quickly to price changes. If a position isn't working within 2-4 hours, reduce or exit.
```

**SWING (4-24H):**
```
Trading style: swing. Hold positions for 4-24 hours if thesis is intact. Don't overreact to hourly noise.
```

**POSITION (1-7D):**
```
Trading style: position. Hold through multi-day moves. Only adjust on significant trend changes or major sentiment shifts.
```

## Implementation Roadmap

### Phase 1: Schema v2 Support (1 day)
- [ ] Add `LlmDecisionOutputV2` to `src/v4t/contracts/payloads.py`
- [ ] Add `mode`, `leverage`, `stop_loss_pct`, `take_profit_pct` fields
- [ ] Update `validate_decision_targets()` in `src/v4t/orchestrator/run_base.py` to enforce risk level constraints
- [ ] Add schema version detection in `src/v4t/llm/gateway.py`
- [ ] Update system prompt constant to v2 format

### Phase 2: Futures/Margin Simulation (2 days)
- [ ] Create `NautilusFuturesSim` class extending margin account model
- [ ] Track `entry_price`, `position_direction`, `position_leverage` per position
- [ ] Compute `liquidation_price = entry_price * (1 ± 1/leverage)`
- [ ] Handle negative `targets` values as short positions
- [ ] Add margin requirement validation before opening positions
- [ ] Emit liquidation events when price crosses liquidation threshold

### Phase 3: Stop-Loss/Take-Profit Execution (1 day)
- [ ] Store `stop_loss_pct`, `take_profit_pct` from LLM decision in run state
- [ ] Compute trigger prices: `stop_loss_price`, `take_profit_price` based on entry and direction
- [ ] Add intra-tick price monitoring in replay loop (check every price event)
- [ ] Add intra-tick price monitoring in live loop (check every price tick)
- [ ] Force-close position when trigger hit, emit `sim.fill` with `reason` field
- [ ] Clear triggers after position closes

### Phase 4: Portfolio State Enrichment (0.5 days)
- [ ] Add `entry_price` tracking to position state
- [ ] Compute `unrealized_pnl = (current_price - entry_price) * position_qty` (flip for shorts)
- [ ] Compute `unrealized_pnl_pct = unrealized_pnl / margin_used * 100`
- [ ] Add `position_mode`, `position_direction`, `liquidation_price` to prompt context
- [ ] Add `stop_loss_price`, `take_profit_price` to prompt context

### Phase 5: Funding Rate Integration (1 day)
- [ ] Ingest Binance funding rates via API (every 8h)
- [ ] Store funding rate history in `events` table as `funding.rate` events
- [ ] Compute `funding_cost = position_notional * funding_rate` every 8h for open positions
- [ ] Accumulate `funding_cost_accumulated` in position state
- [ ] Deduct funding costs from cash balance

### Phase 6: Live Sentiment Pipeline (0.5 days)
- [ ] Wire existing sentiment crawler output into live mode
- [ ] Populate `sentiment_summaries` in `src/v4t/orchestrator/live_run.py`
- [ ] Query recent `sentiment.item_summary` events from event store
- [ ] Match replay sentiment format exactly

### Phase 7: API Extensions (0.5 days)
- [ ] Add `risk_level` (1-5) to `RunCreateRequest` and `ArenaSubmissionCreateRequest`
- [ ] Add `holding_period` ("intraday"|"swing"|"position") to requests
- [ ] Auto-generate user strategy prompt from risk level + holding period
- [ ] Allow optional `system_prompt` override for pro users
- [ ] Validate risk level constraints before run creation

### Phase 8: Arena Tournament Mode (1 day)
- [ ] Create 10 token × 10 event window scenario set
- [ ] Batch-create 100 runs per submission
- [ ] Track completion progress (windows_completed / windows_total)
- [ ] Compute aggregate metrics: total_return_pct (compounded), avg_return_pct, sharpe_ratio
- [ ] Add leaderboard endpoint sorted by total_return_pct

## Data Requirements

### Already Available
- ✅ Price data (Binance)
- ✅ OHLCV bars (1h timeframe)
- ✅ Sentiment summaries (Twitter crawler)
- ✅ Decision memory (last 3 decisions)

### Need to Add
- ⚠️ Funding rates (Binance API: `/fapi/v1/fundingRate`)
- ⚠️ Liquidation events (computed from position + price)
- ⚠️ Entry price tracking (add to position state)
- ⚠️ Stop-loss/take-profit triggers (add to run state)

## Testing Strategy

1. **Unit tests**: Schema validation, risk constraint enforcement, liquidation price calculation
2. **Integration tests**: Replay run with futures positions, SL/TP triggers, funding costs
3. **Smoke tests**: 100-run tournament with stub model, verify all windows complete
4. **Live tests**: Demo mode with real LLM, verify sentiment + SL/TP work in production

## Rollout Plan

1. Deploy schema v2 support (backward compatible with v1)
2. Test futures simulation in replay mode only
3. Add SL/TP execution and verify with historical data
4. Wire live sentiment pipeline
5. Enable tournament mode for beta users
6. Monitor API costs and adjust rate limits
7. Public launch with leaderboard

## Cost Estimates

- **Per run**: ~42 LLM calls (1 per 4 hours) × $0.01 = $0.42
- **Per tournament**: 100 runs × $0.42 = $42
- **Per user per day**: Assume 3 tournaments = $126
- **100 users**: $12,600/day

Mitigation:
- Use cheaper models for lower risk levels (GPT-4o-mini, Gemini Flash)
- Cache sentiment summaries across runs
- Limit free tier to 1 tournament/day
- Charge $10/month for unlimited tournaments
