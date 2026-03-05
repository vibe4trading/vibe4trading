from __future__ import annotations

from datetime import UTC, datetime, timedelta

from v4t.db.models import DatasetRow, LlmModelRow
from v4t.settings import get_settings


def test_public_models_endpoint_includes_stub(client) -> None:  # noqa: ANN001
    res = client.get("/models")
    assert res.status_code == 200
    models = res.json()
    assert any(m["model_key"] == "stub" for m in models)


def test_admin_models_crud(client) -> None:  # noqa: ANN001
    res = client.post(
        "/admin/models",
        json={
            "model_key": "gpt-4o-mini",
            "label": "GPT-4o mini",
            "api_base_url": "https://example.test/v1",
            "enabled": True,
        },
    )
    assert res.status_code == 200
    created = res.json()
    assert created["model_key"] == "gpt-4o-mini"
    assert created["api_base_url"] == "https://example.test/v1"

    res = client.get("/admin/models")
    assert res.status_code == 200
    rows = res.json()
    assert any(r["model_key"] == "gpt-4o-mini" for r in rows)

    res = client.put(
        "/admin/models/gpt-4o-mini",
        json={"api_base_url": "https://router.example.test/api/v1", "enabled": False},
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["api_base_url"] == "https://router.example.test/api/v1"
    assert updated["enabled"] is False

    res = client.delete("/admin/models/gpt-4o-mini")
    assert res.status_code == 200
    assert res.json()["deleted"] is True


def test_arena_submission_rejects_non_predefined_model(db_session, client, monkeypatch) -> None:  # noqa: ANN001
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    ids: list[str] = []
    for i in range(10):
        start = base + timedelta(hours=i * 12)
        end = start + timedelta(hours=12)
        ds = DatasetRow(
            category="spot",
            source="demo",
            start=start,
            end=end,
            params={"market_id": "spot:demo:DEMO"},
            status="ready",
            error=None,
            created_at=base,
            updated_at=base,
        )
        db_session.add(ds)
        db_session.flush()
        ids.append(str(ds.dataset_id))
    db_session.commit()

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(ids))
    get_settings.cache_clear()

    res = client.post(
        "/arena/submissions",
        json={
            "scenario_set_key": "default-v1",
            "market_id": "spot:demo:DEMO",
            "model_key": "gpt-4o-mini",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 400
    assert "predefined list" in res.json()["detail"]

    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url="https://example.test/v1",
            enabled=True,
            created_at=base,
            updated_at=base,
        )
    )
    db_session.commit()

    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "task-arena")

    res = client.post(
        "/arena/submissions",
        json={
            "scenario_set_key": "default-v1",
            "market_id": "spot:demo:DEMO",
            "model_key": "gpt-4o-mini",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 200
