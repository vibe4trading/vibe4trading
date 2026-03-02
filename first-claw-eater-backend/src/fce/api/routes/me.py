from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["me"])


@router.get("/me")
def me() -> dict[str, str]:
    # MVP: auth is out of scope; this is a placeholder.
    return {"user_id": "dev", "display_name": "Dev"}
