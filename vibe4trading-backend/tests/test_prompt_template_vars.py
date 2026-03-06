from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from v4t.contracts.run_config import (
    DatasetRefs,
    ModelConfig,
    PromptConfig,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.models import DatasetRow, LlmCallRow, RunConfigSnapshotRow, RunRow
from v4t.ingest.dataset_import import import_dataset
from v4t.orchestrator.replay_run import execute_replay_run


def test_prompt_text_passed_to_llm_call(db_session) -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=6)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    spot = DatasetRow(
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO", "base_price": 1.0},
        status="pending",
        created_at=now,
        updated_at=now,
    )
    sent = DatasetRow(
        category="sentiment",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([spot, sent])
    db_session.commit()

    import_dataset(db_session, dataset_id=spot.dataset_id)
    import_dataset(db_session, dataset_id=sent.dataset_id)

    custom_prompt = "Analyze the market with a balanced risk approach."
    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id="spot:demo:DEMO",
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(
            market_dataset_id=spot.dataset_id, sentiment_dataset_id=sent.dataset_id
        ),
        scheduler=SchedulerConfig(base_interval_seconds=3600, price_tick_seconds=60),
        prompt=PromptConfig(
            prompt_text=custom_prompt,
            lookback_bars=72,
            timeframe="1h",
        ),
    )
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=now)
    db_session.add(cfg_row)
    db_session.flush()

    run = RunRow(
        market_id=cfg.market_id,
        model_key=cfg.model.key,
        config_id=cfg_row.config_id,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.commit()

    execute_replay_run(db_session, run_id=run.run_id)

    calls = list(
        db_session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id == run.run_id, LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert calls
    user_prompt = calls[0].prompt["messages"][1]["content"]
    assert custom_prompt in user_prompt
    assert "Market:" in user_prompt
    assert "market_id=spot:demo:DEMO" in user_prompt
    assert "Recent OHLCV bars" in user_prompt
    assert "Recent sentiment summaries" in user_prompt
    assert "Recent decisions" in user_prompt
    assert "Return ONLY a JSON object like:" in user_prompt
