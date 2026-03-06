from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from v4t.contracts.run_config import (
    DatasetRefs,
    ExecutionConfig,
    ModelConfig,
    PromptConfig,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.models import DatasetRow, EventRow, LlmCallRow, RunConfigSnapshotRow, RunRow
from v4t.ingest.dataset_import import import_dataset
from v4t.orchestrator.replay_run import execute_replay_run


def test_execute_replay_run_schema_v2_enriches_prompt_and_events(db_session) -> None:
    now_ts = datetime.now(UTC)
    start = (now_ts - timedelta(hours=8)).replace(minute=0, second=0, microsecond=0)
    end = now_ts.replace(minute=0, second=0, microsecond=0)

    spot = DatasetRow(
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO", "base_price": 100.0},
        status="pending",
        created_at=now_ts,
        updated_at=now_ts,
    )
    sent = DatasetRow(
        category="sentiment",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
        status="pending",
        created_at=now_ts,
        updated_at=now_ts,
    )
    db_session.add_all([spot, sent])
    db_session.commit()

    import_dataset(db_session, dataset_id=spot.dataset_id)
    import_dataset(db_session, dataset_id=sent.dataset_id)

    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        decision_schema_version=2,
        market_id="spot:demo:DEMO",
        risk_level=3,
        holding_period="swing",
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(
            market_dataset_id=spot.dataset_id,
            sentiment_dataset_id=sent.dataset_id,
        ),
        scheduler=SchedulerConfig(
            base_interval_seconds=3600,
            min_interval_seconds=300,
            price_tick_seconds=60,
        ),
        prompt=PromptConfig(
            prompt_text="Trade the strongest opportunity.",
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
        ),
        execution=ExecutionConfig(
            fee_bps=10.0,
            initial_equity_quote=1000.0,
            gross_leverage_cap=5.0,
            net_exposure_cap=5.0,
        ),
    )
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=now_ts)
    db_session.add(cfg_row)
    db_session.flush()

    run = RunRow(
        market_id=cfg.market_id,
        model_key=cfg.model.key,
        config_id=cfg_row.config_id,
        status="pending",
        created_at=now_ts,
        updated_at=now_ts,
    )
    db_session.add(run)
    db_session.commit()

    execute_replay_run(db_session, run_id=run.run_id)

    call = db_session.execute(
        select(LlmCallRow)
        .where(LlmCallRow.run_id == run.run_id, LlmCallRow.purpose == "decision")
        .order_by(LlmCallRow.observed_at)
        .limit(1)
    ).scalar_one()
    user_prompt = call.prompt["messages"][1]["content"]
    assert '"schema_version":2' in user_prompt
    assert "position_mode=" in user_prompt
    assert "position_direction=" in user_prompt

    decision_event = db_session.execute(
        select(EventRow)
        .where(EventRow.run_id == run.run_id, EventRow.event_type == "llm.decision")
        .order_by(EventRow.observed_at)
        .limit(1)
    ).scalar_one()
    assert decision_event.payload["decision_schema_version"] == 2
    assert decision_event.payload["mode"] in {"spot", "futures"}

    snapshot_event = db_session.execute(
        select(EventRow)
        .where(EventRow.run_id == run.run_id, EventRow.event_type == "portfolio.snapshot")
        .order_by(EventRow.observed_at)
        .limit(1)
    ).scalar_one()
    assert "position_mode" in snapshot_event.payload
    assert "unrealized_pnl" in snapshot_event.payload
