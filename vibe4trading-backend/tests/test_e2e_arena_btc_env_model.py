from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from v4t.arena.runner import execute_arena_submission
from v4t.contracts.run_config import RunConfigSnapshot
from v4t.db.models import (
    ArenaSubmissionRow,
    ArenaSubmissionRunRow,
    DatasetRow,
    EventRow,
    LlmCallRow,
    LlmModelRow,
    RunConfigSnapshotRow,
    RunRow,
)
from v4t.settings import get_settings

ENV_MODEL_KEY = "test-env-model"
BTC_MARKET_ID = "spot:freqtrade:BTC/USDT"


def _setup_env(monkeypatch):
    monkeypatch.setenv("V4T_CELERY_ALWAYS_EAGER", "1")
    get_settings.cache_clear()


def _create_model_row(session):
    ts = datetime.now(UTC)
    session.add(
        LlmModelRow(
            model_key=ENV_MODEL_KEY,
            label="Test Env Model",
            api_base_url=None,
            enabled=True,
            created_at=ts,
            updated_at=ts,
        )
    )
    session.commit()


def _create_btc_arena_datasets(session, *, n_datasets: int = 1):
    base = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)
    ids: list[str] = []
    for i in range(n_datasets):
        start = base + timedelta(days=i * 7)
        end = start + timedelta(days=7)
        ds = DatasetRow(
            category="spot",
            source="demo",
            start=start,
            end=end,
            params={"market_id": BTC_MARKET_ID, "base_price": 60000.0 + i * 1000},
            status="pending",
            error=None,
            created_at=base,
            updated_at=base,
        )
        session.add(ds)
        session.flush()
        ids.append(str(ds.dataset_id))
    session.commit()
    return ids


def test_arena_submission_accepts_env_model_via_api(db_session, client, monkeypatch):
    _setup_env(monkeypatch)
    _create_model_row(db_session)
    ids = _create_btc_arena_datasets(db_session)
    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(ids))
    get_settings.cache_clear()

    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "task-env")

    res = client.post(
        "/arena/submissions",
        json={
            "market_id": BTC_MARKET_ID,
            "model_key": ENV_MODEL_KEY,
            "prompt_text": "Analyze BTC market data and decide exposure.",
            "visibility": "public",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["model_key"] == ENV_MODEL_KEY
    assert body["status"] == "pending"


def test_e2e_arena_btc_tournament_env_model(db_session, monkeypatch):
    _setup_env(monkeypatch)
    _create_model_row(db_session)
    ids = _create_btc_arena_datasets(db_session)
    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(ids))
    get_settings.cache_clear()

    now_ts = datetime.now(UTC)
    sub = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-fullrange-v1",
        market_id=BTC_MARKET_ID,
        model_key=ENV_MODEL_KEY,
        prompt_template_id=None,
        prompt_vars={
            "prompt_text": "Analyze BTC market data and decide target exposure.",
        },
        visibility="public",
        status="pending",
        windows_total=0,
        windows_completed=0,
        total_return_pct=None,
        avg_return_pct=None,
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now_ts,
        updated_at=now_ts,
    )
    db_session.add(sub)
    db_session.commit()

    execute_arena_submission(db_session, submission_id=sub.submission_id)

    db_session.refresh(sub)
    assert sub.status == "finished"
    assert sub.windows_total >= 1
    assert sub.windows_completed == sub.windows_total
    assert sub.total_return_pct is not None
    assert sub.avg_return_pct is not None

    runs = list(
        db_session.execute(
            select(ArenaSubmissionRunRow).where(
                ArenaSubmissionRunRow.submission_id == sub.submission_id
            )
        )
        .scalars()
        .all()
    )
    assert len(runs) >= 1
    assert all(r.status == "finished" for r in runs)
    assert all(r.return_pct is not None for r in runs)

    run_ids = [r.run_id for r in runs]

    llm_calls = list(
        db_session.execute(
            select(LlmCallRow).where(
                LlmCallRow.run_id.in_(run_ids), LlmCallRow.purpose == "decision"
            )
        )
        .scalars()
        .all()
    )
    assert len(llm_calls) >= 1

    for call in llm_calls:
        assert call.prompt is not None
        messages = call.prompt.get("messages", [])
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert call.prompt.get("model") == ENV_MODEL_KEY
        assert call.response_raw is not None or call.error is not None

    for run_id in run_ids:
        run_row = db_session.get(RunRow, run_id)
        assert run_row is not None
        assert run_row.model_key == ENV_MODEL_KEY
        assert run_row.status == "finished"

        cfg_row = db_session.get(RunConfigSnapshotRow, run_row.config_id)
        assert cfg_row is not None
        cfg = RunConfigSnapshot.model_validate(cfg_row.config)
        assert cfg.datasets.market_dataset_id is not None
        assert cfg.model.key == ENV_MODEL_KEY
        assert cfg.market_id == BTC_MARKET_ID

    for run_id in run_ids:
        events = list(
            db_session.execute(
                select(EventRow).where(EventRow.run_id == run_id).order_by(EventRow.observed_at)
            )
            .scalars()
            .all()
        )
        event_types = {e.event_type for e in events}
        assert "run.started" in event_types
        assert "run.finished" in event_types

        started_events = [e for e in events if e.event_type == "run.started"]
        assert len(started_events) == 1
        finished_events = [e for e in events if e.event_type == "run.finished"]
        assert len(finished_events) == 1
        finished_payload = finished_events[0].payload
        assert "return_pct" in finished_payload

        decision_events = [e for e in events if e.event_type == "llm.decision"]
        assert len(decision_events) >= 1
        for de in decision_events:
            assert "decision" in de.payload or "targets" in str(de.payload)

        portfolio_events = [e for e in events if e.event_type == "portfolio.snapshot"]
        assert len(portfolio_events) >= 1
