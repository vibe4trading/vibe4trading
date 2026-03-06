from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from v4t.db.models import JobRow, RunConfigSnapshotRow, RunRow
from v4t.jobs.types import JOB_TYPE_RUN_EXECUTE_LIVE


def _make_live_cfg(*, market_id: str) -> dict:
    return {
        "mode": "live",
        "market_id": market_id,
        "model": {"key": "stub"},
        "datasets": {"market_dataset_id": None, "sentiment_dataset_id": None},
        "live": {"source": "demo", "chain_id": None, "pair_id": None, "base_price": 1.0},
        "scheduler": {
            "base_interval_seconds": 60,
            "price_tick_seconds": 60,
        },
        "prompt": {
            "prompt_text": "Analyze market data.",
            "lookback_bars": 60,
            "timeframe": "1m",
        },
        "execution": {
            "fee_bps": 10.0,
            "initial_equity_quote": 1000.0,
            "gross_leverage_cap": 1.0,
            "net_exposure_cap": 1.0,
        },
    }


def test_get_live_run_returns_latest_live_run(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)

    replay_cfg = RunConfigSnapshotRow(config={"mode": "replay"}, created_at=now)
    live_cfg = RunConfigSnapshotRow(
        config=_make_live_cfg(market_id="spot:demo:DEMO"), created_at=now
    )
    db_session.add_all([replay_cfg, live_cfg])
    db_session.flush()

    r1 = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=replay_cfg.config_id,
        status="finished",
        created_at=now,
        updated_at=now,
    )
    r2 = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=live_cfg.config_id,
        status="running",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    res = client.get("/live/run")
    assert res.status_code == 200
    body = res.json()
    assert body["run"] is not None
    assert body["run"]["run_id"] == str(r2.run_id)


def test_start_live_run_reuses_existing_running_when_not_forced(
    db_session, client, monkeypatch
) -> None:  # noqa: ANN001
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "should-not-be-called")

    now = datetime.now(UTC)
    cfg = RunConfigSnapshotRow(config=_make_live_cfg(market_id="spot:demo:DEMO"), created_at=now)
    db_session.add(cfg)
    db_session.flush()

    existing = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=cfg.config_id,
        status="running",
        stop_requested=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(existing)
    db_session.commit()

    res = client.post(
        "/live/run",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "force_restart": False,
            "live_source": "demo",
            "base_price": 1.0,
        },
    )
    assert res.status_code == 200
    assert res.json()["run_id"] == str(existing.run_id)


def test_start_live_run_force_restart_marks_old_stop_requested_and_starts_new(
    db_session, client, monkeypatch
) -> None:  # noqa: ANN001
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "task-live")

    now = datetime.now(UTC)
    cfg = RunConfigSnapshotRow(config=_make_live_cfg(market_id="spot:demo:DEMO"), created_at=now)
    db_session.add(cfg)
    db_session.flush()

    existing = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=cfg.config_id,
        status="running",
        stop_requested=False,
        created_at=now,
        updated_at=now,
    )
    db_session.add(existing)
    db_session.commit()

    res = client.post(
        "/live/run",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "force_restart": True,
            "live_source": "demo",
            "base_price": 1.0,
        },
    )
    assert res.status_code == 200
    new_run_id = res.json()["run_id"]
    assert new_run_id != str(existing.run_id)

    db_session.refresh(existing)
    assert existing.stop_requested is True

    jobs = list(
        db_session.execute(select(JobRow).where(JobRow.run_id == UUID(new_run_id))).scalars().all()
    )
    assert len(jobs) == 1
    assert jobs[0].job_type == JOB_TYPE_RUN_EXECUTE_LIVE
    assert jobs[0].payload["celery_task_id"] == "task-live"


def test_start_live_run_validates_dexscreener_requires_ids(client) -> None:  # noqa: ANN001
    res = client.post(
        "/live/run",
        json={
            "market_id": "spot:dexscreener:SOL/USDC",
            "model_key": "stub",
            "force_restart": True,
            "live_source": "dexscreener",
            "base_price": 1.0,
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Chain ID and Pair ID are required for DexScreener"
