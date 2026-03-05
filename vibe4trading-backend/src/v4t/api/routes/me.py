from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.auth.deps import get_current_user, is_admin_user
from v4t.auth.quota import check_quota
from v4t.db.models import UserRow

router = APIRouter(tags=["me"])


@router.get("/me")
def me(
    user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    has_quota, runs_used, runs_limit = check_quota(db, user.user_id)

    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "api_token": user.api_token,
        "is_admin": is_admin_user(user),
        "quota": {
            "runs_used": runs_used,
            "runs_limit": runs_limit,
            "has_quota": has_quota,
        },
    }
