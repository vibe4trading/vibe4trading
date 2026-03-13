from __future__ import annotations

from datetime import UTC, datetime, timedelta

from v4t.contracts.payloads import (
    SentimentItemKind,
    SentimentItemPayload,
    SentimentItemSummaryPayload,
)
from v4t.orchestrator.prompt_builder import render_user_prompt
from v4t.orchestrator.run_base import SentimentPromptItem, build_prompt_context


def test_prompt_uses_full_text_with_metadata_when_summary_missing() -> None:
    tick_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    sentiment_item = SentimentPromptItem(
        payload=SentimentItemPayload(
            source="newswire",
            external_id="article-1",
            item_time=tick_time - timedelta(minutes=5),
            item_kind=SentimentItemKind.news,
            text="Full article text about ETF inflows accelerating after the macro print.",
            url="https://example.invalid/articles/etf-inflows",
        ),
        raw_payload={
            "author": "Macro Desk",
            "language": "en",
            "importance": 5,
        },
    )

    context = build_prompt_context(
        market_id="spot:test:BTC",
        tick_time=tick_time,
        mask_offset=timedelta(0),
        timeframe="1h",
        latest_price=None,
        ohlcv_bars=None,
        closes=[],
        features=None,
        sentiment_items=[sentiment_item],
        sentiment_summaries=[],
        portfolio_view={},
        memory=[],
    )

    prompt = render_user_prompt(
        style_text="Trade the tape.",
        context=context,
        include=["sentiment"],
    )

    assert (
        "full_text=Full article text about ETF inflows accelerating after the macro print."
        in prompt
    )
    assert "source=newswire" in prompt
    assert "kind=news" in prompt
    assert "external_id=article-1" in prompt
    assert "url=https://example.invalid/articles/etf-inflows" in prompt
    assert "author=Macro Desk" in prompt
    assert "importance=5" in prompt


def test_prompt_prefers_summary_when_available() -> None:
    tick_time = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    sentiment_item = SentimentPromptItem(
        payload=SentimentItemPayload(
            source="newswire",
            external_id="article-2",
            item_time=tick_time - timedelta(minutes=5),
            item_kind=SentimentItemKind.news,
            text="This full text should not appear when a summary exists.",
            url=None,
        ),
        raw_payload={"author": "Macro Desk"},
    )
    sentiment_summary = SentimentItemSummaryPayload(
        source="newswire",
        external_id="article-2",
        item_time=tick_time - timedelta(minutes=5),
        item_kind=SentimentItemKind.news,
        summary_text="Concise summary for the trading prompt.",
        tags=["macro"],
        sentiment_score="0.4",
    )

    context = build_prompt_context(
        market_id="spot:test:BTC",
        tick_time=tick_time,
        mask_offset=timedelta(0),
        timeframe="1h",
        latest_price=None,
        ohlcv_bars=None,
        closes=[],
        features=None,
        sentiment_items=[sentiment_item],
        sentiment_summaries=[sentiment_summary],
        portfolio_view={},
        memory=[],
    )

    prompt = render_user_prompt(
        style_text="Trade the tape.",
        context=context,
        include=["sentiment"],
    )

    assert "summary=Concise summary for the trading prompt." in prompt
    assert "full_text=This full text should not appear when a summary exists." not in prompt
    assert "score=0.4" in prompt
