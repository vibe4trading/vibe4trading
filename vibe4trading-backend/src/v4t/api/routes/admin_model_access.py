from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.schemas import (
    AdminModelAccessIndexOut,
    AdminModelAccessUpdateRequest,
    AdminModelAccessUserOut,
)
from v4t.api.utils import (
    default_allowed_model_keys,
    effective_allowed_model_keys,
    normalize_model_allowlist_override,
)
from v4t.auth.deps import get_admin_user
from v4t.db.models import LlmModelRow, UserRow
from v4t.settings import get_settings, parse_csv_set

router = APIRouter(prefix="/admin/model-access", tags=["admin-model-access"])


def _user_out(
    user: UserRow, *, all_model_keys: set[str], selectable_model_keys: set[str]
) -> AdminModelAccessUserOut:
    allowed_model_keys = sorted(
        effective_allowed_model_keys(all_model_keys=all_model_keys, user=user)
    )
    return AdminModelAccessUserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        model_allowlist_override=user.model_allowlist_override,
        allowed_model_keys=allowed_model_keys,
        selectable_model_keys=sorted(
            model_key for model_key in allowed_model_keys if model_key in selectable_model_keys
        ),
    )


@router.get("", response_model=AdminModelAccessIndexOut)
def list_user_model_access(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> AdminModelAccessIndexOut:
    model_rows = list(
        db.execute(select(LlmModelRow).order_by(LlmModelRow.model_key)).scalars().all()
    )
    total_users = int(db.execute(select(func.count()).select_from(UserRow)).scalar_one())
    users = list(
        db.execute(
            select(UserRow).order_by(UserRow.created_at.desc()).limit(limit + 1).offset(offset)
        )
        .scalars()
        .all()
    )

    all_model_keys = {row.model_key for row in model_rows}
    selectable_model_keys = {row.model_key for row in model_rows if row.enabled}
    configured_default = parse_csv_set(get_settings().llm_model_allowlist)

    return AdminModelAccessIndexOut(
        default_allowlist_model_keys=sorted(default_allowed_model_keys(all_model_keys)),
        default_allows_all_models=configured_default is None,
        total_users=total_users,
        limit=limit,
        offset=offset,
        has_more=len(users) > limit,
        users=[
            _user_out(
                user, all_model_keys=all_model_keys, selectable_model_keys=selectable_model_keys
            )
            for user in users[:limit]
        ],
    )


@router.put("/users/{user_id}", response_model=AdminModelAccessUserOut)
def update_user_model_access(
    user_id: UUID,
    req: AdminModelAccessUpdateRequest,
    db: Session = Depends(get_db),
    _admin: UserRow = Depends(get_admin_user),
) -> AdminModelAccessUserOut:
    user = db.get(UserRow, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    try:
        user.model_allowlist_override = normalize_model_allowlist_override(
            req.model_allowlist_override
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)

    model_rows = list(
        db.execute(select(LlmModelRow).order_by(LlmModelRow.model_key)).scalars().all()
    )
    all_model_keys = {row.model_key for row in model_rows}
    selectable_model_keys = {row.model_key for row in model_rows if row.enabled}
    return _user_out(
        user, all_model_keys=all_model_keys, selectable_model_keys=selectable_model_keys
    )
