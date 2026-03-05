from __future__ import annotations

from datetime import UTC, datetime, timedelta

from v4t.contracts.run_config import (
    DatasetRefsV1,
    ModelConfigV1,
    PromptConfigV1,
    RunConfigSnapshotV1,
    RunMode,
    SchedulerConfigV1,
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

    cfg = RunConfigSnapshotV1(
        mode=RunMode.replay,
        market_id="spot:demo:DEMO",
        model=ModelConfigV1(key="stub"),
        datasets=DatasetRefsV1(
            market_dataset_id=spot.dataset_id, sentiment_dataset_id=sent.dataset_id
        ),
        scheduler=SchedulerConfigV1(
            base_interval_seconds=3600, min_interval_seconds=60, price_tick_seconds=60
        ),
        prompt=PromptConfigV1(
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
