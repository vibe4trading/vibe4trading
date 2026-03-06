from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.schemas import ModelAdminCreateRequest, ModelAdminOut, ModelAdminUpdateRequest
from v4t.api.utils import now
from v4t.auth.deps import get_admin_user
from v4t.db.models import LlmModelRow, UserRow
from v4t.settings import get_env_model_key, get_settings

router = APIRouter(prefix="/admin/models", tags=["admin-models"])

_MODEL_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_RESERVED_KEYS = {"stub", "multi-pair"}


def _is_reserved_key(key: str) -> bool:
    if key in _RESERVED_KEYS:
        return True
    env_key = get_env_model_key()
    return env_key is not None and key == env_key


def _validate_api_base_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    v = raw.strip()
    if not v:
        return None
    u = urlparse(v)
    if u.scheme not in {"http", "https"} or not u.netloc:
        raise HTTPException(status_code=400, detail="api_base_url must be an http(s) URL")

    host = (u.hostname or "").strip().lower()
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        raise HTTPException(status_code=400, detail="api_base_url host is not allowed")
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="api_base_url host is not allowed")
    except ValueError:
        pass
    return v


def _normalize_api_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    v = raw.strip()
    return v or None


def _to_out(row: LlmModelRow) -> ModelAdminOut:
    return ModelAdminOut(
        model_key=row.model_key,
        label=row.label,
        api_base_url=row.api_base_url,
        has_api_key=bool((row.api_key or "").strip()),
        enabled=bool(row.enabled),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ModelAdminOut])
def list_models(
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> list[ModelAdminOut]:
    rows = list(db.execute(select(LlmModelRow).order_by(LlmModelRow.model_key)).scalars().all())
    out = [_to_out(r) for r in rows]
    env_key = get_env_model_key()
    if env_key is not None and all(r.model_key != env_key for r in rows):
        ts = now()
        out.insert(
            0,
            ModelAdminOut(
                model_key=env_key,
                label=env_key,
                api_base_url=get_settings().llm_base_url,
                has_api_key=bool((get_settings().llm_api_key or "").strip()),
                enabled=True,
                created_at=ts,
                updated_at=ts,
            ),
        )
    return out


@router.post("", response_model=ModelAdminOut)
def create_model(
    req: ModelAdminCreateRequest,
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> ModelAdminOut:
    key = (req.model_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="model_key is required")
    if _is_reserved_key(key):
        raise HTTPException(status_code=400, detail="model_key is reserved")
    if not _MODEL_KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="model_key has invalid format")

    ts = now()
    row = LlmModelRow(
        model_key=key,
        label=req.label,
        api_base_url=_validate_api_base_url(req.api_base_url),
        api_key=_normalize_api_key(req.api_key),
        enabled=bool(req.enabled),
        created_at=ts,
        updated_at=ts,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="model_key already exists") from exc
    db.refresh(row)
    return _to_out(row)


@router.put("/{model_key}", response_model=ModelAdminOut)
def update_model(
    model_key: str,
    req: ModelAdminUpdateRequest,
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> ModelAdminOut:
    key = (model_key or "").strip()
    if _is_reserved_key(key):
        raise HTTPException(status_code=400, detail="model_key is reserved")
    if not _MODEL_KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="model_key has invalid format")

    row = db.execute(
        select(LlmModelRow).where(LlmModelRow.model_key == key).limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")

    if req.clear_api_key and _normalize_api_key(req.api_key) is not None:
        raise HTTPException(
            status_code=400,
            detail="api_key and clear_api_key cannot both be set",
        )

    if req.label is not None:
        row.label = req.label
    if req.api_base_url is not None:
        row.api_base_url = _validate_api_base_url(req.api_base_url)
    if req.clear_api_key:
        row.api_key = None
    elif req.api_key is not None:
        row.api_key = _normalize_api_key(req.api_key)
    if req.enabled is not None:
        row.enabled = bool(req.enabled)
    row.updated_at = now()

    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{model_key}")
def delete_model(
    model_key: str,
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> dict[str, bool]:
    key = (model_key or "").strip()
    if _is_reserved_key(key):
        raise HTTPException(status_code=400, detail="model_key is reserved")
    if not _MODEL_KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="model_key has invalid format")

    row = db.execute(
        select(LlmModelRow).where(LlmModelRow.model_key == key).limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")

    db.delete(row)
    db.commit()
    return {"deleted": True}
