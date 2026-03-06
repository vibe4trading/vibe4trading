from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.db.models import UserRow


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def create_token_for_user(db: Session, user_id: UUID) -> str:
    token = generate_token()

    stmt = select(UserRow).where(UserRow.user_id == user_id)
    user = db.execute(stmt).scalar_one()
    user.api_token = token
    db.commit()

    return token


def validate_token(db: Session, token: str) -> UserRow | None:
    stmt = select(UserRow).where(UserRow.api_token == token)
    return db.execute(stmt).scalar_one_or_none()
