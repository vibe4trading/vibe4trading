from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.settings import get_settings, parse_csv_set


def assert_model_predefined(db: Session, model_key: str) -> None:
    if model_key == "stub":
        return

    from v4t.db.models import LlmModelRow

    row = (
        db.execute(
            select(LlmModelRow)
            .where(LlmModelRow.model_key == model_key, LlmModelRow.enabled.is_(True))
            .limit(1)
        )
        .scalars()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=400, detail=f"model_key not in predefined list: {model_key}"
        )


def assert_tournament_model_allowed(db: Session, model_key: str) -> None:
    assert_model_predefined(db, model_key)


def now() -> datetime:
    return datetime.now(UTC)


def assert_model_allowed(model_key: str) -> None:
    allowed = parse_csv_set(get_settings().llm_model_allowlist)
    if model_key != "stub" and allowed is not None and model_key not in allowed:
        raise HTTPException(status_code=400, detail=f"model_key not allowed: {model_key}")
