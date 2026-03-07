from __future__ import annotations

import asyncio
import os
import secrets
from typing import Any, cast
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.auth.deps import is_admin_user, provision_user_from_jwt
from v4t.auth.oidc import validate_jwt
from v4t.auth.quota import check_quota
from v4t.auth.tokens import create_token_for_user, validate_token
from v4t.settings import get_settings

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])

_oidc_config_cache: dict[str, Any] | None = None
_oidc_config_lock = asyncio.Lock()


async def _get_oidc_config() -> dict[str, Any]:
    global _oidc_config_cache

    if _oidc_config_cache is not None:
        return _oidc_config_cache

    async with _oidc_config_lock:
        if _oidc_config_cache is not None:
            return _oidc_config_cache

        settings = get_settings()
        issuer = settings.oidc_issuer.rstrip("/")
        url = f"{issuer}/.well-known/openid-configuration"

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            _oidc_config_cache = cast(dict[str, Any], resp.json())
            return _oidc_config_cache


def _cookie_params() -> dict[str, Any]:
    settings = get_settings()
    params: dict[str, Any] = {
        "key": settings.session_cookie_name,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.session_cookie_secure,
        "path": "/",
    }
    if settings.session_cookie_domain:
        params["domain"] = settings.session_cookie_domain
    return params


def _get_callback_url() -> str:
    backend_url = os.environ.get("V4T_BACKEND_URL", "http://localhost:8000")
    return f"{backend_url.rstrip('/')}/auth/callback"


def _safe_redirect_path(raw: str) -> str:
    if not raw.startswith("/"):
        return "/"
    if raw.startswith("//"):
        return "/"
    first_segment = raw[1:].split("/", 1)[0]
    if ":" in first_segment:
        return "/"
    return raw


def _user_session_dict(db: Session, user: Any) -> dict[str, Any]:
    has_quota, runs_used, runs_limit = check_quota(db, user.user_id)
    return {
        "authenticated": True,
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "has_api_token": bool(user.api_token),
        "is_admin": is_admin_user(user),
        "quota": {
            "runs_used": runs_used,
            "runs_limit": runs_limit,
            "has_quota": has_quota,
        },
    }


@router.get("/login")
async def login(
    redirect_to: str | None = Query(
        default=None,
        description="Frontend path to redirect to after login.",
    ),
) -> RedirectResponse:
    settings = get_settings()
    oidc_config = await _get_oidc_config()

    authorize_url: str = oidc_config["authorization_endpoint"]
    state = secrets.token_urlsafe(32)
    state_payload = f"{state}|{redirect_to or '/'}"

    params = {
        "client_id": settings.oidc_client_id,
        "response_type": "code",
        "scope": settings.oidc_scopes,
        "redirect_uri": _get_callback_url(),
        "state": state_payload,
    }

    target = f"{authorize_url}?{urlencode(params)}"
    response = RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)

    response.set_cookie(
        key="v4t_oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
        max_age=600,
    )
    return response


@router.get("/callback")
async def callback(
    code: str = Query(...),
    state: str = Query(...),
    v4t_oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()

    parts = state.split("|", 1)
    received_state = parts[0]
    redirect_to = parts[1] if len(parts) > 1 else "/"

    if not v4t_oauth_state or not secrets.compare_digest(v4t_oauth_state, received_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    oidc_config = await _get_oidc_config()
    token_url: str = oidc_config["token_endpoint"]

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _get_callback_url(),
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
            },
            timeout=15.0,
        )

    if token_resp.status_code != 200:
        logger.error(
            "oidc_token_exchange_failed",
            status=token_resp.status_code,
            body=token_resp.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC token exchange failed",
        )

    token_data = token_resp.json()
    access_token: str | None = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No access_token in OIDC response",
        )

    try:
        payload = await validate_jwt(
            access_token,
            settings.oidc_jwks_url,
            settings.oidc_audience,
            settings.oidc_issuer,
        )
    except ValueError as exc:
        logger.error("oidc_jwt_validation_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token from OIDC provider",
        ) from exc

    user = provision_user_from_jwt(db, payload)

    if not user.api_token:
        create_token_for_user(db, user.user_id)
        db.refresh(user)

    frontend_url = settings.frontend_url.rstrip("/")
    redirect_url = f"{frontend_url}{_safe_redirect_path(redirect_to)}"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        **_cookie_params(),
        value=user.api_token,
        max_age=60 * 60 * 24 * 30,
    )
    response.delete_cookie(key="v4t_oauth_state", path="/")

    return response


@router.get("/session")
def get_session(
    response: Response,
    db: Session = Depends(get_db),
    v4t_session: str | None = Cookie(default=None),
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    settings = get_settings()

    if settings.bypass_auth:
        if os.environ.get("V4T_ENVIRONMENT", "").lower() != "production":
            from sqlalchemy import select

            from v4t.db.models import UserRow

            stmt = select(UserRow).limit(1)
            user = db.execute(stmt).scalar_one_or_none()
            if user:
                return _user_session_dict(db, user)

    if not v4t_session:
        return {"authenticated": False}

    user = validate_token(db, v4t_session)
    if not user:
        return {"authenticated": False}

    return _user_session_dict(db, user)


@router.post("/logout")
def logout() -> RedirectResponse:
    settings = get_settings()
    frontend_url = settings.frontend_url.rstrip("/")

    response = RedirectResponse(url=frontend_url, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(**_cookie_params())
    return response


@router.get("/logout")
def logout_json(response: Response) -> dict[str, bool]:
    response.delete_cookie(**_cookie_params())
    return {"ok": True}
