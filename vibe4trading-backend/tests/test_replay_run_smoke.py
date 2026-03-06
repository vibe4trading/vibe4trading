from __future__ import annotations

from datetime import UTC, datetime, timedelta

from v4t.contracts.run_config import (
    DatasetRefs,
    ModelConfig,
    PromptConfig,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.models import DatasetRow, RunConfigSnapshotRow, RunRow
from v4t.ingest.dataset_import import import_dataset
from v4t.orchestrator.replay_run import execute_replay_run


def test_execute_replay_run_finishes(db_session) -> None:
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

    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id="spot:demo:DEMO",
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(
            market_dataset_id=spot.dataset_id, sentiment_dataset_id=sent.dataset_id
        ),
        scheduler=SchedulerConfig(base_interval_seconds=3600, price_tick_seconds=60),
        prompt=PromptConfig(
            prompt_text="Analyze the market and output JSON.",
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
    db_session.refresh(run)

    assert run.status == "finished"
    assert run.summary_text is not None
