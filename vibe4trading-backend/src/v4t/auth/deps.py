from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.auth.oidc import validate_jwt
from v4t.auth.tokens import create_token_for_user, validate_token
from v4t.db.models import UserRow
from v4t.settings import get_settings, parse_csv_set

import structlog

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserRow:
    settings = get_settings()
    if settings.bypass_auth:
        import os

        if os.environ.get("V4T_ENVIRONMENT", "").lower() == "production":
            logger.warning("bypass_auth is enabled in production — ignoring")
        else:
            stmt = select(UserRow).limit(1)
            user = db.execute(stmt).scalar_one_or_none()
            if not user:
                user = UserRow(
                    oidc_issuer="dev",
                    oidc_sub="dev-user",
                    email="dev@example.com",
                    display_name="Dev User",
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            return user

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
        )

    token = credentials.credentials

    user_id = validate_token(db, token)
    if user_id:
        stmt = select(UserRow).where(UserRow.user_id == user_id)
        user = db.execute(stmt).scalar_one_or_none()
        if user:
            return user

    try:
        settings = get_settings()
        payload = await validate_jwt(
            token, settings.oidc_jwks_url, settings.oidc_audience, settings.oidc_issuer
        )
        user = await provision_user_from_jwt(db, payload)
        return user
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


async def provision_user_from_jwt(db: Session, payload: dict) -> UserRow:
    oidc_issuer = payload.get("iss")
    oidc_sub = payload.get("sub")
    email = payload.get("email")
    display_name = payload.get("name") or payload.get("preferred_username")

    stmt = select(UserRow).where(UserRow.oidc_issuer == oidc_issuer, UserRow.oidc_sub == oidc_sub)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        user = UserRow(
            oidc_issuer=oidc_issuer,
            oidc_sub=oidc_sub,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        create_token_for_user(db, user.user_id)
    else:
        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            changed = True
        if changed:
            db.commit()

    return user


def is_admin_user(user: UserRow) -> bool:
    settings = get_settings()
    if settings.bypass_auth:
        return True

    admins = parse_csv_set(settings.admin_email_allowlist)
    if not admins:
        return False

    email = (user.email or "").strip().lower()
    return bool(email) and email in {e.strip().lower() for e in admins}


async def get_admin_user(user: UserRow = Depends(get_current_user)) -> UserRow:
    if not is_admin_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
