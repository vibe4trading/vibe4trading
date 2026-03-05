from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.api.schemas import ModelPublicOut
from v4t.db.models import LlmModelRow

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelPublicOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelPublicOut]:
    rows = list(
        db.execute(
            select(LlmModelRow).where(LlmModelRow.enabled.is_(True)).order_by(LlmModelRow.model_key)
        )
        .scalars()
        .all()
    )

    out: list[ModelPublicOut] = [ModelPublicOut(model_key="stub", label="Stub")]
    for r in rows:
        if r.model_key == "stub":
            continue
        out.append(ModelPublicOut(model_key=r.model_key, label=r.label))
    return out
