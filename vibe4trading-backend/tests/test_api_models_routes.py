from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.app import create_app
from v4t.api.deps import get_db
from v4t.db.models import DatasetRow, LlmModelRow, UserRow
from v4t.settings import get_settings


def _dispatch_task_arena(*, job: Any) -> str:
    return "task-arena"


@contextmanager
def _fresh_client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_public_models_endpoint_includes_stub(client: TestClient) -> None:
    res = client.get("/models")
    assert res.status_code == 200
    models = res.json()
    assert any(m["model_key"] == "stub" for m in models)


def test_public_models_endpoint_shows_disabled_and_disallowed_models(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="models-user",
        email="models@example.com",
        model_allowlist_override="+deepseekv3,-gpt-4o-mini",
    )
    db_session.add(user)
    db_session.add_all(
        [
            LlmModelRow(model_key="gpt-4o-mini", label="GPT-4o mini", enabled=True),
            LlmModelRow(model_key="deepseekv3", label="DeepSeek V3", enabled=True),
            LlmModelRow(model_key="gemini-3-pro", label="Gemini 3 Pro", enabled=False),
        ]
    )
    db_session.commit()

    monkeypatch.setenv("V4T_LLM_MODEL_ALLOWLIST", "gpt-4o-mini")
    get_settings.cache_clear()

    res = client.get("/models")
    assert res.status_code == 200
    payload = {row["model_key"]: row for row in res.json()}

    assert payload["stub"]["selectable"] is True
    assert payload["gpt-4o-mini"]["allowed"] is False
    assert payload["gpt-4o-mini"]["selectable"] is False
    assert payload["gpt-4o-mini"]["disabled_reason"] == "Not enabled for your account"
    assert payload["deepseekv3"]["allowed"] is True
    assert payload["deepseekv3"]["selectable"] is True
    assert payload["gemini-3-pro"]["enabled"] is False
    assert payload["gemini-3-pro"]["selectable"] is False
    assert payload["gemini-3-pro"]["disabled_reason"] == "Disabled by admin"


def test_admin_models_crud(db_session: Session, client: TestClient) -> None:
    res = client.post(
        "/admin/models",
        json={
            "model_key": "gpt-4o-mini",
            "label": "GPT-4o mini",
            "api_base_url": "https://example.test/v1",
            "api_key": "sk-model-1",
            "enabled": True,
        },
    )
    assert res.status_code == 200
    created = res.json()
    assert created["model_key"] == "gpt-4o-mini"
    assert created["api_base_url"] == "https://example.test/v1"
    assert created["has_api_key"] is True

    res = client.get("/admin/models")
    assert res.status_code == 200
    rows = res.json()
    assert any(r["model_key"] == "gpt-4o-mini" for r in rows)
    assert next(r for r in rows if r["model_key"] == "gpt-4o-mini")["has_api_key"] is True

    res = client.put(
        "/admin/models/gpt-4o-mini",
        json={
            "api_base_url": "https://router.example.test/api/v1",
            "api_key": "sk-model-2",
            "enabled": False,
        },
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["api_base_url"] == "https://router.example.test/api/v1"
    assert updated["has_api_key"] is True
    assert updated["enabled"] is False

    row = (
        db_session.execute(
            select(LlmModelRow).where(LlmModelRow.model_key == "gpt-4o-mini").limit(1)
        )
        .scalars()
        .one()
    )
    assert row.api_key == "sk-model-2"

    res = client.delete("/admin/models/gpt-4o-mini")
    assert res.status_code == 200
    assert res.json()["deleted"] is True


def test_admin_models_can_clear_api_key(db_session: Session, client: TestClient) -> None:
    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url="https://example.test/v1",
            api_key="sk-model-1",
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    res = client.put("/admin/models/gpt-4o-mini", json={"clear_api_key": True})
    assert res.status_code == 200
    assert res.json()["has_api_key"] is False

    row = db_session.query(LlmModelRow).filter(LlmModelRow.model_key == "gpt-4o-mini").one()
    assert row.api_key is None


def test_env_model_is_listed_without_db_row(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("V4T_LLM_MODEL", "env-gpt-test")
    monkeypatch.setenv("V4T_LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("V4T_LLM_API_KEY", "")
    get_settings.cache_clear()

    with _fresh_client(db_session) as client:
        public_res = client.get("/models")
        assert public_res.status_code == 200
        public_models = {row["model_key"]: row for row in public_res.json()}
        assert "env-gpt-test" in public_models

        admin_res = client.get("/admin/models")
        assert admin_res.status_code == 200
        admin_models = {row["model_key"]: row for row in admin_res.json()}
        assert "env-gpt-test" in admin_models
        assert admin_models["env-gpt-test"]["api_base_url"] == "https://example.test/v1"
        assert admin_models["env-gpt-test"]["has_api_key"] is False


def test_env_model_reports_api_key_presence(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("V4T_LLM_MODEL", "env-gpt-test")
    monkeypatch.setenv("V4T_LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("V4T_LLM_API_KEY", "sk-env")
    get_settings.cache_clear()

    with _fresh_client(db_session) as client:
        admin_res = client.get("/admin/models")
        assert admin_res.status_code == 200
        admin_models = {row["model_key"]: row for row in admin_res.json()}
        assert admin_models["env-gpt-test"]["has_api_key"] is True


def test_admin_models_reject_env_model_key_mutation(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_MODEL", "env-gpt-test")
    monkeypatch.setenv("V4T_LLM_BASE_URL", "https://example.test/v1")
    get_settings.cache_clear()

    with _fresh_client(db_session) as client:
        create_res = client.post(
            "/admin/models",
            json={
                "model_key": "env-gpt-test",
                "label": "duplicate",
                "api_base_url": "https://example.test/v1",
                "enabled": True,
            },
        )
        assert create_res.status_code == 400
        assert create_res.json()["detail"] == "model_key is reserved"

        update_res = client.put("/admin/models/env-gpt-test", json={"enabled": False})
        assert update_res.status_code == 400
        assert update_res.json()["detail"] == "model_key is reserved"

        delete_res = client.delete("/admin/models/env-gpt-test")
        assert delete_res.status_code == 400
        assert delete_res.json()["detail"] == "model_key is reserved"


def test_admin_model_access_update_normalizes_override(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_MODEL", "stub")
    get_settings.cache_clear()
    user = UserRow(oidc_issuer="test", oidc_sub="user-1", email="user1@example.com")
    db_session.add(user)
    db_session.add_all(
        [
            LlmModelRow(model_key="gpt-4o-mini", label="GPT-4o mini", enabled=True),
            LlmModelRow(model_key="deepseekv3", label="DeepSeek V3", enabled=True),
        ]
    )
    db_session.commit()

    res = client.put(
        f"/admin/model-access/users/{user.user_id}",
        json={"model_allowlist_override": " +deepseekv3 , -gpt-4o-mini "},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["model_allowlist_override"] == "+deepseekv3,-gpt-4o-mini"
    assert payload["allowed_model_keys"] == ["deepseekv3"]
    assert payload["selectable_model_keys"] == ["deepseekv3"]


def test_admin_model_access_rejects_invalid_override(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_MODEL", "stub")
    get_settings.cache_clear()
    user = UserRow(oidc_issuer="test", oidc_sub="user-invalid", email="invalid@example.com")
    db_session.add(user)
    db_session.commit()

    res = client.put(
        f"/admin/model-access/users/{user.user_id}",
        json={"model_allowlist_override": "gpt-4o-mini"},
    )
    assert res.status_code == 400
    assert "Invalid allowlist override token" in res.json()["detail"]


def test_admin_model_access_is_paginated(db_session: Session, client: TestClient) -> None:
    db_session.add_all(
        [
            UserRow(oidc_issuer="test", oidc_sub=f"user-{i}", email=f"user{i}@example.com")
            for i in range(3)
        ]
    )
    db_session.commit()

    res = client.get("/admin/model-access?limit=2&offset=0")
    assert res.status_code == 200
    payload = res.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert payload["total_users"] >= 3
    assert payload["has_more"] is True
    assert len(payload["users"]) == 2


def test_arena_submission_rejects_non_predefined_model(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
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

    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", _dispatch_task_arena)

    res = client.post(
        "/arena/submissions",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "gpt-4o-mini",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 200


def test_arena_submission_rejects_model_not_allowed_for_user(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    user = UserRow(oidc_issuer="test", oidc_sub="arena-user", email="arena@example.com")
    db_session.add(user)

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

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(ids))
    monkeypatch.setenv("V4T_LLM_MODEL_ALLOWLIST", "stub")
    get_settings.cache_clear()

    res = client.post(
        "/arena/submissions",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "gpt-4o-mini",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 400
    assert "not allowed for user" in res.json()["detail"]

    user.model_allowlist_override = "+gpt-4o-mini"
    db_session.commit()
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", _dispatch_task_arena)

    res = client.post(
        "/arena/submissions",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "gpt-4o-mini",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 200
