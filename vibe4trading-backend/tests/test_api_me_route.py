from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from v4t.db.models import UserRow


def test_me_omits_api_token_and_reports_token_status(
    db_session: Session, client: TestClient
) -> None:
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="me-user",
        email="me@example.com",
        display_name="Me User",
        api_token="bot-token-123",
    )
    db_session.add(user)
    db_session.commit()

    res = client.get("/me")

    assert res.status_code == 200
    payload = res.json()
    assert payload["email"] == "me@example.com"
    assert payload["display_name"] == "Me User"
    assert payload["has_api_token"] is True
    assert "api_token" not in payload
    assert res.headers["cache-control"] == "no-store"


def test_me_api_token_returns_existing_token(db_session: Session, client: TestClient) -> None:
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="token-user",
        email="token@example.com",
        display_name="Token User",
        api_token="existing-bot-token",
    )
    db_session.add(user)
    db_session.commit()

    res = client.get("/me/api-token")

    assert res.status_code == 200
    assert res.json() == {"api_token": "existing-bot-token", "created": False}
    assert res.headers["cache-control"] == "no-store"


def test_me_api_token_creates_token_when_missing(db_session: Session, client: TestClient) -> None:
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="new-token-user",
        email="new-token@example.com",
        display_name="New Token User",
    )
    db_session.add(user)
    db_session.commit()

    res = client.get("/me/api-token")

    assert res.status_code == 200
    payload = res.json()
    assert payload["created"] is True
    assert isinstance(payload["api_token"], str)
    assert payload["api_token"]
    assert res.headers["cache-control"] == "no-store"

    db_session.refresh(user)
    assert user.api_token == payload["api_token"]
