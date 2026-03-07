from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.schemas import ModelPublicOut
from v4t.api.utils import effective_allowed_model_keys
from v4t.auth.deps import get_optional_current_user
from v4t.db.models import LlmModelRow, UserRow

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelPublicOut])
def list_models(
    db: Session = Depends(get_db),
    user: UserRow | None = Depends(get_optional_current_user),
) -> list[ModelPublicOut]:
    rows = list(db.execute(select(LlmModelRow).order_by(LlmModelRow.model_key)).scalars().all())

    models: dict[str, tuple[str | None, bool]] = {
        row.model_key: (row.label, bool(row.enabled)) for row in rows if row.model_key != "stub"
    }

    allowed_model_keys = effective_allowed_model_keys(all_model_keys=set(models), user=user)

    out: list[ModelPublicOut] = []
    for model_key in sorted(models):
        label, enabled = models[model_key]
        allowed = model_key in allowed_model_keys
        selectable = enabled and allowed
        disabled_reason = None
        if not enabled:
            disabled_reason = "Disabled by admin"
        elif not allowed:
            disabled_reason = "Not enabled for your account"

        out.append(
            ModelPublicOut(
                model_key=model_key,
                label=label,
                enabled=enabled,
                allowed=allowed,
                selectable=selectable,
                disabled_reason=disabled_reason,
            )
        )
    return out
