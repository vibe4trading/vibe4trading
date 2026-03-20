from __future__ import annotations

from eth_utils.address import to_checksum_address
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.deps import get_db
from v4t.auth.deps import get_current_user, is_admin_user
from v4t.auth.nonce import verify_and_consume_nonce
from v4t.auth.quota import check_quota
from v4t.auth.tokens import create_token_for_user
from v4t.auth.wallet import verify_wallet_signature
from v4t.db.models import UserRow

router = APIRouter(tags=["me"])


class LinkWalletRequest(BaseModel):
    wallet_address: str
    signature: str
    nonce: str


class LinkWalletResponse(BaseModel):
    wallet_address: str


@router.get("/me")
def me(
    response: Response,
    user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | bool | dict[str, int | bool] | None]:
    response.headers["Cache-Control"] = "no-store"

    has_quota, runs_used, runs_limit = check_quota(db, user.user_id)

    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "display_name": user.display_name,
        "has_api_token": bool(user.api_token),
        "is_admin": is_admin_user(user),
        "wallet_address": user.wallet_address,
        "quota": {
            "runs_used": runs_used,
            "runs_limit": runs_limit,
            "has_quota": has_quota,
        },
    }


@router.get("/me/api-token")
def me_api_token(
    response: Response,
    user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    response.headers["Cache-Control"] = "no-store"

    api_token = user.api_token
    created = False
    if not api_token:
        api_token = create_token_for_user(db, user.user_id)
        created = True

    return {
        "api_token": api_token,
        "created": created,
    }


@router.post("/me/link-wallet")
def link_wallet(
    request: LinkWalletRequest,
    user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LinkWalletResponse:
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet linking requires OIDC account",
        )

    normalized_address = to_checksum_address(request.wallet_address)

    if not verify_and_consume_nonce(normalized_address, request.nonce):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired nonce"
        )

    message = f"Sign in to Vibe4Trading\n\nNonce: {request.nonce}\nChain ID: 1"
    if not verify_wallet_signature(normalized_address, message, request.signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    stmt = select(UserRow).where(UserRow.wallet_address == normalized_address)
    existing_user = db.execute(stmt).scalar_one_or_none()

    if existing_user and existing_user.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Wallet already linked to another user"
        )

    user.wallet_address = normalized_address
    db.commit()

    return LinkWalletResponse(wallet_address=normalized_address)


@router.post("/me/unlink-wallet")
def unlink_wallet(
    user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet linking requires OIDC account",
        )

    user.wallet_address = None
    db.commit()
    return {"success": True}
