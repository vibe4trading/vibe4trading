from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class HoldingPeriod(StrEnum):
    intraday = "intraday"
    swing = "swing"
    position = "position"


class PositionMode(StrEnum):
    spot = "spot"
    futures = "futures"


class PositionDirection(StrEnum):
    long = "long"
    short = "short"
    flat = "flat"


@dataclass(frozen=True)
class RiskProfile:
    risk_level: int
    max_leverage: int
    short_allowed: bool
    max_abs_exposure: Decimal
    mode_allowed: tuple[PositionMode, ...]


BENCHMARK_SYSTEM_PROMPT = """You are a crypto trading decision engine for a strategy benchmark.

RULES:
1. You manage exactly ONE position: {{TOKEN}}/USDT on your exchange.
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
- The confidence field (0.0 to 1.0) reflects how sure you are. Low confidence means smaller position changes.

EXPOSURE RULES:
- mode=spot: target value must be 0.0 to 1.0. No leverage. Long only.
- mode=futures: target value can be negative for shorts. abs(value) must not exceed leverage.
- Positive value means long. Negative value means short. Zero means flat.
- Move gradually unless there is an extreme signal.

RISK MANAGEMENT:
- stop_loss_pct: if price moves this percent against you, position auto-closes.
- take_profit_pct: if price moves this percent in your favor, position auto-closes.
- Both are optional but strongly recommended.
- If leveraged and price hits liquidation (entry +/- 100 percent divided by leverage), you lose all margin.

OUTPUT FORMAT - return ONLY this JSON:
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
}"""


RISK_PROFILES: dict[int, RiskProfile] = {
    1: RiskProfile(
        risk_level=1,
        max_leverage=1,
        short_allowed=False,
        max_abs_exposure=Decimal("0.5"),
        mode_allowed=(PositionMode.spot,),
    ),
    2: RiskProfile(
        risk_level=2,
        max_leverage=1,
        short_allowed=False,
        max_abs_exposure=Decimal("0.7"),
        mode_allowed=(PositionMode.spot,),
    ),
    3: RiskProfile(
        risk_level=3,
        max_leverage=5,
        short_allowed=True,
        max_abs_exposure=Decimal("5.0"),
        mode_allowed=(PositionMode.spot, PositionMode.futures),
    ),
    4: RiskProfile(
        risk_level=4,
        max_leverage=20,
        short_allowed=True,
        max_abs_exposure=Decimal("20.0"),
        mode_allowed=(PositionMode.spot, PositionMode.futures),
    ),
    5: RiskProfile(
        risk_level=5,
        max_leverage=100,
        short_allowed=True,
        max_abs_exposure=Decimal("100.0"),
        mode_allowed=(PositionMode.spot, PositionMode.futures),
    ),
}


RISK_LEVEL_PROMPTS: dict[int, str] = {
    1: (
        "You are a conservative crypto trader. Prioritize capital preservation above all else. "
        "SPOT ONLY - no leverage, no shorting. Only increase exposure when momentum is clearly "
        "positive and sentiment is bullish for multiple hours. Reduce exposure immediately at any "
        "negative signal. Prefer staying in cash. Maximum exposure: 0.5. Move in small increments "
        "(0.1-0.2 steps). Use tight stop-loss (2%)."
    ),
    2: (
        "You are a conservative crypto trader. Prioritize capital preservation. SPOT ONLY - no "
        "leverage, no shorting. Increase exposure gradually when momentum and sentiment align "
        "positively. Reduce on negative signals. Maximum exposure: 0.7. Move in 0.15-0.25 steps. "
        "Use stop-loss at 3%."
    ),
    3: (
        "You are a balanced crypto trader. You can use FUTURES with leverage up to 5x. Shorting "
        "is allowed. Go long when momentum is positive and sentiment is supportive. Short when "
        "momentum is negative and sentiment is bearish. Prefer gradual position changes. Maximum "
        "exposure: 5.0 (with leverage). Move in 0.5-1.0 steps. Use stop-loss at 5%. Take-profit "
        "at 2:1 ratio."
    ),
    4: (
        "You are an aggressive crypto trader. You can use FUTURES with leverage up to 20x. "
        "Shorting is allowed. Take large positions when momentum and sentiment are favorable. Hold "
        "through minor dips if trend is intact. Short aggressively during clear downtrends. Only "
        "reduce on strong reversal signals. Maximum exposure: 20.0 (with leverage). Move in "
        "1.0-5.0 steps. Use stop-loss at 8%."
    ),
    5: (
        "You are a maximum aggression crypto trader. You can use FUTURES with leverage up to 100x. "
        "Shorting is allowed. Go max long on any positive signal. Go max short on any negative "
        "signal. Hold through volatility. Your goal is maximum returns, not capital preservation. "
        "Maximum exposure: 100.0 (with leverage). Move in 5.0-20.0 steps. Stop-loss at 15% or "
        "none if conviction is extreme."
    ),
}


HOLDING_PERIOD_PROMPTS: dict[HoldingPeriod, str] = {
    HoldingPeriod.intraday: (
        "Trading style: intraday. React quickly to price changes. If a position is not working "
        "within 2-4 hours, reduce or exit."
    ),
    HoldingPeriod.swing: (
        "Trading style: swing. Hold positions for 4-24 hours if thesis is intact. Do not "
        "overreact to hourly noise."
    ),
    HoldingPeriod.position: (
        "Trading style: position. Hold through multi-day moves. Only adjust on significant trend "
        "changes or major sentiment shifts."
    ),
}


def get_risk_profile(risk_level: int | None) -> RiskProfile | None:
    if risk_level is None:
        return None
    return RISK_PROFILES.get(int(risk_level))


def build_strategy_prompt(
    *,
    base_prompt: str,
    risk_level: int | None,
    holding_period: HoldingPeriod | None,
) -> str:
    base = (base_prompt or "").strip()
    if base:
        return base

    return "Analyze the market data and decide target exposure."


def benchmark_system_prompt(system_prompt_override: str | None, market_id: str) -> str:
    override = (system_prompt_override or "").strip()
    if override:
        return override

    # Extract token from market_id (e.g., "spot:binance:BTCUSDT" -> "BTC")
    token = "TOKEN"
    try:
        parts = market_id.split(":")
        if len(parts) >= 3:
            pair = parts[2]  # e.g., "BTCUSDT" or "BTC/USDT"
            # Handle both formats: "BTCUSDT" and "BTC/USDT"
            if "/" in pair:
                token = pair.split("/")[0]
            else:
                # Extract base token from pair like "BTCUSDT"
                for quote in ["USDT", "USDC", "USD", "BTC", "ETH"]:
                    if pair.endswith(quote):
                        token = pair[: -len(quote)]
                        break
    except Exception:
        pass

    return BENCHMARK_SYSTEM_PROMPT.replace("{{TOKEN}}", token)
