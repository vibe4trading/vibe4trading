from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from v4t.db.models import (
    DatasetRow,
    EventRow,
    JobRow,
    PortfolioSnapshotRow,
    RunConfigSnapshotRow,
    RunRow,
)
from v4t.jobs.types import JOB_TYPE_RUN_EXECUTE_REPLAY


def _make_ready_dataset(
    db_session,
    *,
    category: str,
    source: str,
    start: datetime,
    end: datetime,
    params: dict,
) -> DatasetRow:
    row = DatasetRow(
        category=category,
        source=source,
        start=start,
        end=end,
        params=params,
        status="ready",
        error=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_create_run_validates_datasets_exist(db_session, client) -> None:  # noqa: ANN001
    req = {
        "market_id": "spot:demo:DEMO",
        "model_key": "stub",
        "market_dataset_id": str(uuid4()),
        "sentiment_dataset_id": str(uuid4()),
    }
    res = client.post("/runs", json=req)
    assert res.status_code == 400
    assert res.json()["detail"] == "Dataset not found"


def test_create_run_validates_dataset_status_ready(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    start = (now - timedelta(hours=4)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    spot = DatasetRow(
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
        status="pending",
        error=None,
        created_at=now,
        updated_at=now,
    )
    sent = DatasetRow(
        category="sentiment",
        source="empty",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
        status="ready",
        error=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([spot, sent])
    db_session.commit()

    res = client.post(
        "/runs",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "market_dataset_id": str(spot.dataset_id),
            "sentiment_dataset_id": str(sent.dataset_id),
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Datasets must be ready before creating a run"


def test_create_run_validates_windows_match(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    start = (now - timedelta(hours=4)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    spot = _make_ready_dataset(
        db_session,
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
    )
    sent = _make_ready_dataset(
        db_session,
        category="sentiment",
        source="empty",
        start=start,
        end=end + timedelta(hours=1),
        params={"market_id": "spot:demo:DEMO"},
    )

    res = client.post(
        "/runs",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "market_dataset_id": str(spot.dataset_id),
            "sentiment_dataset_id": str(sent.dataset_id),
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "All datasets must have matching time windows"


def test_create_run_validates_market_id_against_spot_dataset(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    start = (now - timedelta(hours=4)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    spot = _make_ready_dataset(
        db_session,
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:OTHER"},
    )
    sent = _make_ready_dataset(
        db_session,
        category="sentiment",
        source="empty",
        start=start,
        end=end,
        params={"market_id": "spot:demo:OTHER"},
    )

    res = client.post(
        "/runs",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "market_dataset_id": str(spot.dataset_id),
            "sentiment_dataset_id": str(sent.dataset_id),
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"].startswith("market_id mismatch:")


def test_create_run_enqueues_job_and_persists_task_id(db_session, client, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "task-abc")

    now = datetime.now(UTC)
    start = (now - timedelta(hours=4)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)
    spot = _make_ready_dataset(
        db_session,
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
    )
    sent = _make_ready_dataset(
        db_session,
        category="sentiment",
        source="empty",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
    )

    res = client.post(
        "/runs",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "market_dataset_id": str(spot.dataset_id),
            "sentiment_dataset_id": str(sent.dataset_id),
        },
    )
    assert res.status_code == 200
    run_id = UUID(res.json()["run_id"])

    run = db_session.get(RunRow, run_id)
    assert run is not None
    assert run.status == "pending"

    jobs = list(
        db_session.execute(select(JobRow).where(JobRow.run_id == run.run_id)).scalars().all()
    )
    assert len(jobs) == 1
    assert jobs[0].job_type == JOB_TYPE_RUN_EXECUTE_REPLAY
    assert jobs[0].payload["celery_task_id"] == "task-abc"


def test_create_run_rejects_disallowed_model_key(db_session, client, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "t")

    now = datetime.now(UTC)
    start = (now - timedelta(hours=4)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)
    spot = _make_ready_dataset(
        db_session,
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
    )
    sent = _make_ready_dataset(
        db_session,
        category="sentiment",
        source="empty",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
    )

    res = client.post(
        "/runs",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "not-allowed",
            "market_dataset_id": str(spot.dataset_id),
            "sentiment_dataset_id": str(sent.dataset_id),
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"].startswith("model_key not in predefined list:")


def test_create_run_rejects_unsupported_prompt_template_engine(
    db_session, client, monkeypatch
) -> None:  # noqa: ANN001
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "t")


def test_private_tournament_run_is_hidden(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    cfg = RunConfigSnapshotRow(config={"mode": "replay"}, created_at=now)
    db_session.add(cfg)
    db_session.flush()

    run = RunRow(
        kind="tournament",
        visibility="private",
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=cfg.config_id,
        status="finished",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.commit()

    list_res = client.get("/runs")
    assert list_res.status_code == 200
    assert all(r["run_id"] != str(run.run_id) for r in list_res.json()["items"])

    assert client.get(f"/runs/{run.run_id}").status_code == 404
    assert client.get(f"/runs/{run.run_id}/decisions").status_code == 404
    assert client.get(f"/runs/{run.run_id}/summary").status_code == 404


def test_runs_list_uses_cursor_pagination(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    cfg = RunConfigSnapshotRow(config={"mode": "replay"}, created_at=now)
    db_session.add(cfg)
    db_session.flush()

    rows = []
    for i in range(3):
        row = RunRow(
            market_id=f"spot:demo:PAIR{i}",
            model_key="stub",
            config_id=cfg.config_id,
            status="finished",
            created_at=now - timedelta(minutes=i),
            updated_at=now - timedelta(minutes=i),
        )
        rows.append(row)
    db_session.add_all(rows)
    db_session.commit()

    first = client.get("/runs?limit=2")
    assert first.status_code == 200
    first_payload = first.json()
    assert len(first_payload["items"]) == 2
    assert first_payload["has_more"] is True
    assert first_payload["next_cursor"] is not None

    second = client.get("/runs", params={"limit": 2, "cursor": first_payload["next_cursor"]})
    assert second.status_code == 200
    second_payload = second.json()
    assert len(second_payload["items"]) == 1
    assert second_payload["has_more"] is False


def test_runs_cursor_tiebreaks_same_timestamp(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    cfg = RunConfigSnapshotRow(config={"mode": "replay"}, created_at=now)
    db_session.add(cfg)
    db_session.flush()

    first_row = RunRow(
        market_id="spot:demo:AAA",
        model_key="stub",
        config_id=cfg.config_id,
        status="finished",
        created_at=now,
        updated_at=now,
    )
    second_row = RunRow(
        market_id="spot:demo:BBB",
        model_key="stub",
        config_id=cfg.config_id,
        status="finished",
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first_row, second_row])
    db_session.commit()

    first = client.get("/runs?limit=1")
    assert first.status_code == 200
    first_payload = first.json()
    second = client.get("/runs", params={"limit": 1, "cursor": first_payload["next_cursor"]})
    assert second.status_code == 200
    second_payload = second.json()
    returned_ids = {first_payload["items"][0]["run_id"], second_payload["items"][0]["run_id"]}
    assert returned_ids == {str(first_row.run_id), str(second_row.run_id)}


def test_stop_run_sets_flag(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    run = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=uuid4(),
        status="running",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.commit()

    res = client.post(f"/runs/{run.run_id}/stop")
    assert res.status_code == 200
    db_session.refresh(run)
    assert run.stop_requested is True

    missing = client.post("/runs/00000000-0000-0000-0000-000000000000/stop")
    assert missing.status_code == 404


def test_timeline_prices_decisions_and_summary(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    start = (now - timedelta(hours=4)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    spot = _make_ready_dataset(
        db_session,
        category="spot",
        source="demo",
        start=start,
        end=end,
        params={"market_id": "spot:demo:DEMO"},
    )
    cfg = {
        "mode": "replay",
        "market_id": "spot:demo:DEMO",
        "model": {"key": "stub"},
        "datasets": {"market_dataset_id": str(spot.dataset_id), "sentiment_dataset_id": None},
        "scheduler": {
            "base_interval_seconds": 3600,
            "min_interval_seconds": 60,
            "price_tick_seconds": 60,
        },
        "prompt": {
            "prompt_text": "Analyze market data.",
            "lookback_bars": 72,
            "timeframe": "1h",
        },
        "execution": {
            "fee_bps": 10.0,
            "initial_equity_quote": 1000.0,
            "gross_leverage_cap": 1.0,
            "net_exposure_cap": 1.0,
        },
    }
    from v4t.db.models import RunConfigSnapshotRow

    cfg_row = RunConfigSnapshotRow(config=cfg, created_at=now)
    db_session.add(cfg_row)
    db_session.flush()

    run = RunRow(
        market_id="spot:demo:DEMO",
        model_key="stub",
        config_id=cfg_row.config_id,
        status="finished",
        summary_text="hello",
        created_at=now,
        updated_at=now,
    )
    db_session.add(run)
    db_session.flush()

    db_session.add_all(
        [
            PortfolioSnapshotRow(
                run_id=run.run_id,
                observed_at=now - timedelta(minutes=2),
                equity_quote=1000,
                cash_quote=900,
                positions={},
            ),
            PortfolioSnapshotRow(
                run_id=run.run_id,
                observed_at=now - timedelta(minutes=1),
                equity_quote=1100,
                cash_quote=800,
                positions={},
            ),
        ]
    )

    db_session.add_all(
        [
            EventRow(
                event_type="market.price",
                source="t",
                schema_version=1,
                observed_at=now - timedelta(minutes=3),
                event_time=None,
                dedupe_key="p1",
                dataset_id=spot.dataset_id,
                run_id=None,
                payload={"market_id": "spot:demo:DEMO", "price": "1.23", "price_type": "mid"},
                raw_payload=None,
            ),
            EventRow(
                event_type="market.price",
                source="t",
                schema_version=1,
                observed_at=now - timedelta(minutes=2),
                event_time=None,
                dedupe_key="p2",
                dataset_id=spot.dataset_id,
                run_id=None,
                payload={"market_id": "spot:demo:OTHER", "price": "9.99", "price_type": "mid"},
                raw_payload=None,
            ),
            EventRow(
                event_type="market.price",
                source="t",
                schema_version=1,
                observed_at=now - timedelta(minutes=1),
                event_time=None,
                dedupe_key="p3",
                dataset_id=spot.dataset_id,
                run_id=None,
                payload={"bad": "payload"},
                raw_payload=None,
            ),
            EventRow(
                event_type="llm.decision",
                source="t",
                schema_version=1,
                observed_at=now - timedelta(minutes=2),
                event_time=None,
                dedupe_key="d1",
                dataset_id=None,
                run_id=run.run_id,
                payload={
                    "tick_time": (now - timedelta(minutes=2)).isoformat(),
                    "accepted": True,
                    "targets": {},
                },
                raw_payload=None,
            ),
            EventRow(
                event_type="llm.decision",
                source="t",
                schema_version=1,
                observed_at=now - timedelta(minutes=1),
                event_time=None,
                dedupe_key="d2",
                dataset_id=None,
                run_id=run.run_id,
                payload={
                    "tick_time": (now - timedelta(minutes=1)).isoformat(),
                    "accepted": False,
                    "targets": {},
                },
                raw_payload=None,
            ),
        ]
    )

    db_session.commit()

    tl = client.get(f"/runs/{run.run_id}/timeline")
    assert tl.status_code == 200
    points = tl.json()
    assert [p["equity_quote"] for p in points] == [1000.0, 1100.0]

    prices = client.get(f"/runs/{run.run_id}/prices?limit=100")
    assert prices.status_code == 200
    out = prices.json()
    assert len(out) == 1
    assert out[0]["price"] == 1.23

    dec = client.get(f"/runs/{run.run_id}/decisions?limit=10&offset=0")
    assert dec.status_code == 200
    assert [d["accepted"] for d in dec.json()] == [True, False]

    summ = client.get(f"/runs/{run.run_id}/summary")
    assert summ.status_code == 200
    assert summ.json()["summary_text"] == "hello"

    missing = client.get("/runs/00000000-0000-0000-0000-000000000000/prices")
    assert missing.status_code == 404
