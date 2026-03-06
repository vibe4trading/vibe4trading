from __future__ import annotations

from sqlalchemy.orm import Session

from v4t.auth.tokens import create_token_for_user, generate_token, validate_token
from v4t.db.models import UserRow


def test_generate_token_returns_string() -> None:
    token = generate_token()
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_token_unique() -> None:
    token1 = generate_token()
    token2 = generate_token()
    assert token1 != token2


def test_create_token_for_user(db_session: Session) -> None:
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    token = create_token_for_user(db_session, user.user_id)
    assert isinstance(token, str)
    assert len(token) > 0

    db_session.refresh(user)
    assert user.api_token == token


def test_validate_token_valid(db_session: Session) -> None:
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    token = create_token_for_user(db_session, user.user_id)
    token_user = validate_token(db_session, token)
    assert token_user is not None
    assert token_user.user_id == user.user_id


def test_validate_token_invalid(db_session: Session) -> None:
    token_user = validate_token(db_session, "invalid-token")
    assert token_user is None


def test_validate_token_nonexistent(db_session: Session) -> None:
    token_user = validate_token(db_session, "nonexistent-token-12345")
    assert token_user is None
