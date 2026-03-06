from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from v4t.contracts.run_config import (
    DatasetRefs,
    ModelConfig,
    PromptConfig,
    RunConfigSnapshot,
    RunMode,
)
from v4t.db.models import RunConfigSnapshotRow, RunRow
from v4t.orchestrator.replay_run import execute_replay_run


def test_execute_replay_run_rejects_live_runs(db_session: Session) -> None:
    now = datetime.now(UTC)
    cfg = RunConfigSnapshot(
        mode=RunMode.live,
        market_id="spot:demo:DEMO",
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(),
        prompt=PromptConfig(prompt_text="stay flat"),
    )
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=now)
    db_session.add(cfg_row)
    db_session.flush()

    run = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=cfg_row.config_id,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.commit()

    with pytest.raises(ValueError, match="is not a replay run"):
        execute_replay_run(db_session, run_id=run.run_id)
