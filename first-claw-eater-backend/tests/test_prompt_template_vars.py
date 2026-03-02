from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from fce.contracts.run_config import (
    DatasetRefsV1,
    ModelConfigV1,
    PromptConfigV1,
    PromptTemplateSnapshotV1,
    RunConfigSnapshotV1,
    SchedulerConfigV1,
)
from fce.db.models import DatasetRow, LlmCallRow, RunConfigSnapshotRow, RunRow
from fce.ingest.dataset_import import import_dataset
from fce.orchestrator.replay_run import execute_replay_run


def test_prompt_template_vars_available_in_mustache(db_session) -> None:
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
        mode="replay",
        market_id="spot:demo:DEMO",
        model=ModelConfigV1(key="stub"),
        datasets=DatasetRefsV1(
            spot_dataset_id=spot.dataset_id, sentiment_dataset_id=sent.dataset_id
        ),
        scheduler=SchedulerConfigV1(
            base_interval_seconds=3600, min_interval_seconds=60, price_tick_seconds=60
        ),
        prompt=PromptConfigV1(
            template=PromptTemplateSnapshotV1(
                system="Output JSON",
                user=(
                    "risk={{risk_style}} "
                    "{{#vars}}nested={{risk_style}}{{/vars}} "
                    "market={{market_id}}"
                ),
                vars={"risk_style": "balanced"},
            ),
            lookback_bars=24,
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
    assert "risk=balanced" in user_prompt
    assert "nested=balanced" in user_prompt
