from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from fce.api.deps import get_db
from fce.api.schemas import PromptTemplateCreateRequest, PromptTemplateOut
from fce.db.models import PromptTemplateRow

router = APIRouter(prefix="/prompt_templates", tags=["prompt_templates"])


def _now() -> datetime:
    return datetime.now(UTC)


def _to_out(row: PromptTemplateRow) -> PromptTemplateOut:
    return PromptTemplateOut(
        template_id=row.template_id,
        name=row.name,
        engine=row.engine,
        system_template=row.system_template,
        user_template=row.user_template,
        vars_schema=row.vars_schema,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=PromptTemplateOut)
def create_prompt_template(
    req: PromptTemplateCreateRequest, db: Session = Depends(get_db)
) -> PromptTemplateOut:
    now = _now()
    row = PromptTemplateRow(
        owner_user_id=None,
        name=req.name,
        engine=req.engine,
        system_template=req.system_template,
        user_template=req.user_template,
        vars_schema=req.vars_schema,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("", response_model=list[PromptTemplateOut])
def list_prompt_templates(db: Session = Depends(get_db)) -> list[PromptTemplateOut]:
    rows = list(
        db.execute(select(PromptTemplateRow).order_by(PromptTemplateRow.created_at.desc()))
        .scalars()
        .all()
    )
    return [_to_out(r) for r in rows]


@router.get("/{template_id}", response_model=PromptTemplateOut)
def get_prompt_template(template_id: UUID, db: Session = Depends(get_db)) -> PromptTemplateOut:
    row = db.get(PromptTemplateRow, template_id)
    if row is None:
        raise HTTPException(status_code=404, detail="prompt template not found")
    return _to_out(row)
