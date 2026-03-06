"""E2E test: verify the LLM receives correct data during a replay run.

Runs a full replay with the stub model against a small synthetic dataset,
then inspects the recorded llm_calls rows to assert that prompts contain
the expected market data, sentiment, portfolio state, and decision memory.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from v4t.contracts.events import make_event
from v4t.contracts.payloads import (
    MarketOHLCVPayload,
    MarketPricePayload,
    SentimentItemSummaryPayload,
)
from v4t.contracts.run_config import (
    DatasetRefs,
    ExecutionConfig,
    ModelConfig,
    PromptConfig,
    PromptMasking,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.event_store import append_event
from v4t.db.models import DatasetRow, LlmCallRow, RunConfigSnapshotRow, RunRow
from v4t.orchestrator.replay_run import execute_replay_run

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

T0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
MARKET_ID = "spot:test:BTC"


def _make_ohlcv(market_id: str, bar_start: datetime, bar_end: datetime, c: str) -> dict:
    return MarketOHLCVPayload(
        market_id=market_id,
        timeframe="1h",
        bar_start=bar_start,
        bar_end=bar_end,
        o=c,
        h=str(Decimal(c) + 1),
        l=str(Decimal(c) - 1),
        c=c,
    ).model_dump(mode="json")


def _make_price(market_id: str, price: str) -> dict:
    return MarketPricePayload(market_id=market_id, price=price).model_dump(mode="json")


def _make_sentiment_summary(
    item_time: datetime,
    summary_text: str,
    source: str = "test_rss",
) -> dict:
    return SentimentItemSummaryPayload(
        source=source,
        external_id=str(uuid4()),
        item_time=item_time,
        item_kind="news",
        summary_text=summary_text,
        tags=["btc", "bullish"],
        sentiment_score="0.7",
    ).model_dump(mode="json")


def _seed_dataset_events(
    session,
    *,
    market_dataset_id,
    sentiment_dataset_id,
    n_hours: int = 4,
):
    """Create n_hours of price + OHLCV events and a few sentiment summaries."""
    base_price = Decimal("50000")

    for i in range(n_hours):
        bar_start = T0 + timedelta(hours=i)
        bar_end = T0 + timedelta(hours=i + 1)
        price = str(base_price + i * 100)

        append_event(
            session,
            ev=make_event(
                event_type="market.ohlcv",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"ohlcv:{bar_start.isoformat()}",
                dataset_id=market_dataset_id,
                payload=_make_ohlcv(MARKET_ID, bar_start, bar_end, price),
            ),
            dedupe_scope="dataset",
        )

        append_event(
            session,
            ev=make_event(
                event_type="market.price",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"price:{bar_end.isoformat()}",
                dataset_id=market_dataset_id,
                payload=_make_price(MARKET_ID, price),
            ),
            dedupe_scope="dataset",
        )

    # Sentiment summaries at hours 1 and 2.
    for hour, text in [(1, "BTC breaking above resistance."), (2, "Whale accumulation detected.")]:
        append_event(
            session,
            ev=make_event(
                event_type="sentiment.item_summary",
                source="test",
                observed_at=T0 + timedelta(hours=hour, minutes=30),
                dedupe_key=f"sent:{hour}",
                dataset_id=sentiment_dataset_id,
                payload=_make_sentiment_summary(T0 + timedelta(hours=hour, minutes=30), text),
            ),
            dedupe_scope="dataset",
        )

    session.commit()


def _create_run(session, *, market_dataset_id, sentiment_dataset_id):
    """Create a run with stub model pointing at the test datasets."""
    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id=MARKET_ID,
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(
            market_dataset_id=market_dataset_id,
            sentiment_dataset_id=sentiment_dataset_id,
        ),
        prompt=PromptConfig(
            prompt_text="Analyze the market and decide exposure.",
            lookback_bars=72,
            timeframe="1h",
            include=[
                "closes",
                "ohlcv",
                "latest_price",
                "portfolio",
                "memory",
                "sentiment",
                "features",
            ],
            masking=PromptMasking(time_offset_seconds=0),
        ),
        scheduler=SchedulerConfig(
            base_interval_seconds=3600,
            min_interval_seconds=60,
            price_tick_seconds=60,
        ),
        execution=ExecutionConfig(
            fee_bps=10.0,
            initial_equity_quote=10000.0,
        ),
    )

    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"))
    session.add(cfg_row)
    session.flush()

    run = RunRow(
        market_id=MARKET_ID,
        model_key="stub",
        config_id=cfg_row.config_id,
        kind="single_window",
        status="pending",
    )
    session.add(run)
    session.flush()
    session.commit()
    return run.run_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_e2e_replay_llm_receives_correct_data(db_session) -> None:
    """Full replay run with stub model; verify prompts sent to LLM."""
    session = db_session

    # 1. Create datasets.
    market_ds = DatasetRow(
        category="market",
        source="test",
        start=T0,
        end=T0 + timedelta(hours=4),
        params={"market_id": MARKET_ID},
        status="ready",
    )
    sentiment_ds = DatasetRow(
        category="sentiment",
        source="test",
        start=T0,
        end=T0 + timedelta(hours=4),
        params={"market_id": MARKET_ID},
        status="ready",
    )
    session.add_all([market_ds, sentiment_ds])
    session.flush()

    # 2. Seed events.
    _seed_dataset_events(
        session,
        market_dataset_id=market_ds.dataset_id,
        sentiment_dataset_id=sentiment_ds.dataset_id,
        n_hours=4,
    )

    # 3. Create and execute the run.
    run_id = _create_run(
        session,
        market_dataset_id=market_ds.dataset_id,
        sentiment_dataset_id=sentiment_ds.dataset_id,
    )
    execute_replay_run(session, run_id=run_id)

    # 4. Load all decision LLM calls.
    calls = list(
        session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id == run_id, LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )

    # With 4 hours of data and base_interval=1h, expect multiple decision ticks.
    assert len(calls) >= 2, f"Expected at least 2 decision calls, got {len(calls)}"

    # --- Verify each decision call's prompt structure ---
    for idx, call in enumerate(calls):
        prompt = call.prompt
        assert prompt is not None, f"Call {idx} has no prompt"

        messages = prompt.get("messages", [])
        assert len(messages) == 2, f"Call {idx}: expected 2 messages, got {len(messages)}"

        system_msg = messages[0]["content"]
        user_msg = messages[1]["content"]

        # System prompt must instruct JSON output and trading.
        assert "trading decision engine" in system_msg.lower()
        assert "json" in system_msg.lower()

        # User prompt must contain market_id.
        assert MARKET_ID in user_msg, f"Call {idx}: market_id not in user prompt"

        # User prompt must contain instruction text.
        assert "Analyze the market" in user_msg, f"Call {idx}: instruction text missing"

        # User prompt must reference closes.
        assert "closes" in user_msg.lower(), f"Call {idx}: closes section missing"

        # User prompt must reference portfolio.
        assert "portfolio" in user_msg.lower(), f"Call {idx}: portfolio section missing"

        # User prompt must contain the JSON example template.
        assert "schema_version" in user_msg, f"Call {idx}: JSON example missing"

        # Stub features must be present.
        stub_features = prompt.get("stub_features", {})
        assert stub_features.get("market_id") == MARKET_ID
        assert isinstance(stub_features.get("closes"), list)

    # --- Verify first call has initial portfolio state ---
    first_user_msg = calls[0].prompt["messages"][1]["content"]
    assert "10000" in first_user_msg, "First call should show initial equity ~10000"

    # --- Verify closes contain correct prices ---
    first_closes = calls[0].prompt["stub_features"]["closes"]
    assert any("50000" in c for c in first_closes), (
        f"First call closes should include base price 50000, got {first_closes}"
    )

    # --- Verify later calls accumulate more bars ---
    if len(calls) >= 2:
        second_closes = calls[1].prompt["stub_features"]["closes"]
        assert len(second_closes) >= len(first_closes), (
            "Later calls should have at least as many closes"
        )

    # --- Verify OHLCV data appears in the prompt ---
    for idx, call in enumerate(calls):
        user_msg = call.prompt["messages"][1]["content"]
        assert "ohlcv" in user_msg.lower(), f"Call {idx}: OHLCV section missing"
        assert "O=" in user_msg or "o=" in user_msg.lower(), f"Call {idx}: OHLCV bar data missing"

    # --- Verify sentiment appears after it's available ---
    # SQLite returns naive datetimes, so strip tzinfo for comparison.
    t2 = (T0 + timedelta(hours=2)).replace(tzinfo=None)
    late_calls = [c for c in calls if c.observed_at >= t2]
    if late_calls:
        late_msg = late_calls[0].prompt["messages"][1]["content"]
        assert "sentiment" in late_msg.lower(), (
            "Calls after sentiment events should include sentiment section"
        )
        assert "resistance" in late_msg.lower() or "accumulation" in late_msg.lower(), (
            "Sentiment summary text should appear in prompt"
        )

    # --- Verify features (momentum/return_pct) appear in later calls ---
    if len(calls) >= 2:
        later_msg = calls[-1].prompt["messages"][1]["content"]
        assert "features" in later_msg.lower(), "Later calls should include features section"
        assert "momentum" in later_msg.lower() or "return_pct" in later_msg.lower(), (
            "Features should include momentum or return_pct"
        )

    # --- Verify decision memory appears in later calls ---
    if len(calls) >= 2:
        later_msg = calls[-1].prompt["messages"][1]["content"]
        assert "recent decisions" in later_msg.lower(), (
            "Later calls should include decision memory section"
        )

    # --- Verify latest price section ---
    for idx, call in enumerate(calls):
        user_msg = call.prompt["messages"][1]["content"]
        assert "latest price" in user_msg.lower(), f"Call {idx}: latest price section missing"
        assert "price=" in user_msg.lower(), f"Call {idx}: price value missing"

    # --- Verify the LLM responded correctly (stub produces valid decisions) ---
    for idx, call in enumerate(calls):
        assert call.error is None, f"Call {idx} has error: {call.error}"
        parsed = call.response_parsed
        assert parsed is not None, f"Call {idx} has no parsed response"
        assert parsed.get("schema_version") == 1
        assert MARKET_ID in parsed.get("targets", {}), f"Call {idx}: target missing for market"

    # --- Verify run completed successfully ---
    run = session.get(RunRow, run_id)
    assert run.status == "finished", f"Run should be finished, got {run.status}"
    assert run.summary_text is not None, "Run should have a summary"

    # --- Verify summary call was also recorded ---
    summary_calls = list(
        session.execute(
            select(LlmCallRow).where(
                LlmCallRow.run_id == run_id, LlmCallRow.purpose == "run_summary"
            )
        )
        .scalars()
        .all()
    )
    assert len(summary_calls) == 1, "Should have exactly 1 summary call"
    summary_prompt = summary_calls[0].prompt["messages"][1]["content"]
    assert "10000" in summary_prompt or "return_pct" in summary_prompt


def test_e2e_replay_no_sentiment_dataset(db_session) -> None:
    """Replay run without sentiment data still sends correct market data to LLM."""
    session = db_session

    market_ds = DatasetRow(
        category="market",
        source="test",
        start=T0,
        end=T0 + timedelta(hours=3),
        params={"market_id": MARKET_ID},
        status="ready",
    )
    session.add(market_ds)
    session.flush()

    base_price = Decimal("50000")
    for i in range(3):
        bar_start = T0 + timedelta(hours=i)
        bar_end = T0 + timedelta(hours=i + 1)
        price = str(base_price + i * 100)
        append_event(
            session,
            ev=make_event(
                event_type="market.ohlcv",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"ohlcv:{bar_start.isoformat()}",
                dataset_id=market_ds.dataset_id,
                payload=_make_ohlcv(MARKET_ID, bar_start, bar_end, price),
            ),
            dedupe_scope="dataset",
        )
        append_event(
            session,
            ev=make_event(
                event_type="market.price",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"price:{bar_end.isoformat()}",
                dataset_id=market_ds.dataset_id,
                payload=_make_price(MARKET_ID, price),
            ),
            dedupe_scope="dataset",
        )
    session.commit()

    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id=MARKET_ID,
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(market_dataset_id=market_ds.dataset_id),
        prompt=PromptConfig(
            prompt_text="Trade based on price action only.",
            lookback_bars=72,
            timeframe="1h",
            include=["closes", "ohlcv", "latest_price", "portfolio", "memory", "features"],
        ),
        scheduler=SchedulerConfig(
            base_interval_seconds=3600,
            min_interval_seconds=60,
            price_tick_seconds=60,
        ),
        execution=ExecutionConfig(initial_equity_quote=5000.0),
    )
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"))
    session.add(cfg_row)
    session.flush()

    run = RunRow(
        market_id=MARKET_ID,
        model_key="stub",
        config_id=cfg_row.config_id,
        kind="single_window",
        status="pending",
    )
    session.add(run)
    session.flush()
    session.commit()

    execute_replay_run(session, run_id=run.run_id)

    calls = list(
        session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id == run.run_id, LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert len(calls) >= 1

    for idx, call in enumerate(calls):
        user_msg = call.prompt["messages"][1]["content"]
        assert MARKET_ID in user_msg
        assert "5000" in user_msg, f"Call {idx}: initial equity 5000 not found"
        assert call.error is None
        assert call.response_parsed is not None


def test_e2e_replay_prices_accumulate_correctly(db_session) -> None:
    """Verify closes list grows as more bars become available."""
    session = db_session

    market_ds = DatasetRow(
        category="market",
        source="test",
        start=T0,
        end=T0 + timedelta(hours=6),
        params={"market_id": MARKET_ID},
        status="ready",
    )
    session.add(market_ds)
    session.flush()

    prices = ["50000", "50100", "50200", "50300", "50400", "50500"]
    for i in range(6):
        bar_start = T0 + timedelta(hours=i)
        bar_end = T0 + timedelta(hours=i + 1)
        append_event(
            session,
            ev=make_event(
                event_type="market.ohlcv",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"ohlcv:{bar_start.isoformat()}",
                dataset_id=market_ds.dataset_id,
                payload=_make_ohlcv(MARKET_ID, bar_start, bar_end, prices[i]),
            ),
            dedupe_scope="dataset",
        )
        append_event(
            session,
            ev=make_event(
                event_type="market.price",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"price:{bar_end.isoformat()}",
                dataset_id=market_ds.dataset_id,
                payload=_make_price(MARKET_ID, prices[i]),
            ),
            dedupe_scope="dataset",
        )
    session.commit()

    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id=MARKET_ID,
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(market_dataset_id=market_ds.dataset_id),
        prompt=PromptConfig(
            prompt_text="Trade.",
            lookback_bars=72,
            timeframe="1h",
            include=["closes", "ohlcv", "latest_price", "portfolio"],
        ),
        scheduler=SchedulerConfig(
            base_interval_seconds=3600,
            min_interval_seconds=60,
            price_tick_seconds=60,
        ),
    )
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"))
    session.add(cfg_row)
    session.flush()

    run = RunRow(
        market_id=MARKET_ID,
        model_key="stub",
        config_id=cfg_row.config_id,
        kind="single_window",
        status="pending",
    )
    session.add(run)
    session.flush()
    session.commit()

    execute_replay_run(session, run_id=run.run_id)

    calls = list(
        session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id == run.run_id, LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert len(calls) >= 3, f"Expected at least 3 calls for 6h window, got {len(calls)}"

    # Closes should grow monotonically.
    prev_count = 0
    for idx, call in enumerate(calls):
        closes = call.prompt["stub_features"]["closes"]
        assert len(closes) >= prev_count, (
            f"Call {idx}: closes count {len(closes)} < previous {prev_count}"
        )
        prev_count = len(closes)

        # Each close should be one of our known prices.
        for c in closes:
            assert c in prices, f"Call {idx}: unexpected close value {c}"

    # Last call should have multiple closes.
    last_closes = calls[-1].prompt["stub_features"]["closes"]
    assert len(last_closes) >= 3, f"Last call should have many closes, got {len(last_closes)}"
