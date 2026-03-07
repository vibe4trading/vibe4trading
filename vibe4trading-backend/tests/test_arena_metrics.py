from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from v4t.arena.metrics import compute_run_metrics
from v4t.contracts.run_config import (
    DatasetRefs,
    ModelConfig,
    PromptConfig,
    RunConfigSnapshot,
    RunMode,
    SchedulerConfig,
)
from v4t.db.models import PortfolioSnapshotRow, RunConfigSnapshotRow, RunRow


def _create_run(db_session: Session, *, now: datetime, base_interval_seconds: int) -> RunRow:
    cfg = RunConfigSnapshot(
        mode=RunMode.replay,
        market_id="spot:demo:DEMO",
        model=ModelConfig(key="stub"),
        datasets=DatasetRefs(),
        scheduler=SchedulerConfig(
            base_interval_seconds=base_interval_seconds, price_tick_seconds=60
        ),
        prompt=PromptConfig(prompt_text="Trade."),
    )
    cfg_row = RunConfigSnapshotRow(config=cfg.model_dump(mode="json"), created_at=now)
    db_session.add(cfg_row)
    db_session.flush()

    run = RunRow(
        market_id=cfg.market_id,
        model_key=cfg.model.key,
        config_id=cfg_row.config_id,
        status="finished",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.flush()
    return run


def _expected_sharpe(equity_series: list[Decimal], *, tick_interval_seconds: int) -> Decimal:
    returns = [
        (float(cur) - float(prev)) / float(prev)
        for prev, cur in zip(equity_series, equity_series[1:], strict=False)
        if float(prev) != 0.0
    ]
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance)
    annualization_factor = math.sqrt((365 * 24 * 60 * 60) / tick_interval_seconds)
    return Decimal(str(round((mean_r / std_r) * annualization_factor, 4)))


def test_compute_run_metrics_uses_saved_scheduler_interval_for_sharpe(db_session: Session) -> None:
    now = datetime.now(UTC)
    hourly_run = _create_run(db_session, now=now, base_interval_seconds=3600)
    four_hour_run = _create_run(
        db_session, now=now + timedelta(seconds=1), base_interval_seconds=14400
    )

    equity_series = [Decimal("1000"), Decimal("1100"), Decimal("1000")]
    for run in (hourly_run, four_hour_run):
        for idx, equity in enumerate(equity_series):
            db_session.add(
                PortfolioSnapshotRow(
                    run_id=run.run_id,
                    observed_at=now + timedelta(hours=idx),
                    equity_quote=equity,
                    cash_quote=equity,
                    positions={},
                )
            )
    db_session.commit()

    hourly_metrics = compute_run_metrics(db_session, run_id=hourly_run.run_id)
    four_hour_metrics = compute_run_metrics(db_session, run_id=four_hour_run.run_id)

    assert hourly_metrics.sharpe_ratio == _expected_sharpe(
        equity_series, tick_interval_seconds=3600
    )
    assert four_hour_metrics.sharpe_ratio == _expected_sharpe(
        equity_series, tick_interval_seconds=14400
    )
    assert hourly_metrics.sharpe_ratio > four_hour_metrics.sharpe_ratio
