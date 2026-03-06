from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.db.models import LlmModelRow, UserRow
from v4t.settings import (
    get_settings,
    parse_csv_set,
    parse_model_allowlist_override,
)


def default_allowed_model_keys(all_model_keys: set[str]) -> set[str]:
    configured = parse_csv_set(get_settings().llm_model_allowlist)
    allowed = (
        set(all_model_keys)
        if configured is None
        else {key for key in all_model_keys if key in configured}
    )
    return allowed


def effective_allowed_model_keys(*, all_model_keys: set[str], user: UserRow | None) -> set[str]:
    allowed = default_allowed_model_keys(all_model_keys)
    if user is not None:
        additions, removals = parse_model_allowlist_override(user.model_allowlist_override)
        allowed.update(model_key for model_key in additions if model_key in all_model_keys)
        allowed.difference_update(removals)

    return allowed


def normalize_model_allowlist_override(raw: str | None) -> str | None:
    additions, removals = parse_model_allowlist_override(raw, strict=True)
    tokens = [*(f"+{key}" for key in sorted(additions)), *(f"-{key}" for key in sorted(removals))]
    return ",".join(tokens) or None


def assert_model_selectable(db: Session, user: UserRow, model_key: str) -> None:
    if model_key == "stub":
        return

    row = (
        db.execute(select(LlmModelRow).where(LlmModelRow.model_key == model_key).limit(1))
        .scalars()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=400, detail=f"model_key not in predefined list: {model_key}"
        )
    if not row.enabled:
        raise HTTPException(status_code=400, detail=f"model_key is disabled: {model_key}")

    all_model_keys = set(db.execute(select(LlmModelRow.model_key)).scalars().all())
    allowed = effective_allowed_model_keys(all_model_keys=all_model_keys, user=user)
    if model_key not in allowed:
        raise HTTPException(status_code=400, detail=f"model_key not allowed for user: {model_key}")


def assert_tournament_model_allowed(db: Session, user: UserRow, model_key: str) -> None:
    assert_model_selectable(db, user, model_key)


def now() -> datetime:
    return datetime.now(UTC)
