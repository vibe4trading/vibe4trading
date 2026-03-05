from __future__ import annotations

from datetime import UTC, datetime

from v4t.orchestrator.prompt_builder import build_default_prompt_context


def test_build_default_prompt_context_shape() -> None:
    now = datetime.now(UTC)
    ctx = build_default_prompt_context(
        market_id="spot:demo:BTC",
        tick_time=now,
        closes=["100.0", "101.0", "102.0"],
        features={"sma_5": "101.0"},
        sentiment_summaries=[{"summary": "Bullish sentiment"}],
        portfolio={"equity": "1000.0", "cash": "500.0"},
        memory=[{"action": "hold", "rationale": "waiting"}],
    )

    assert ctx["market_id"] == "spot:demo:BTC"
    assert ctx["tick_time"] == now.isoformat()
    assert len(ctx["closes"]) == 3
    assert ctx["features"]["sma_5"] == "101.0"
    assert len(ctx["sentiment_summaries"]) == 1
    assert ctx["portfolio"]["equity"] == "1000.0"
    assert len(ctx["memory"]) == 1


def test_build_default_prompt_context_no_features() -> None:
    now = datetime.now(UTC)
    ctx = build_default_prompt_context(
        market_id="spot:demo:BTC",
        tick_time=now,
        closes=[],
        features=None,
        sentiment_summaries=[],
        portfolio={},
        memory=[],
    )
    assert ctx["features"] is None
    assert ctx["closes"] == []
    assert ctx["sentiment_summaries"] == []
    assert ctx["memory"] == []
