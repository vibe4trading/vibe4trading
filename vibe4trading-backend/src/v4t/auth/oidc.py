from __future__ import annotations

from datetime import UTC, datetime

import httpx
from jose import JWTError, jwt

_jwks_cache: dict | None = None
_jwks_cache_time: datetime | None = None


async def get_jwks(jwks_url: str) -> dict:
    global _jwks_cache, _jwks_cache_time

    now = datetime.now(UTC)
    if _jwks_cache and _jwks_cache_time and (now - _jwks_cache_time).seconds < 3600:
        assert _jwks_cache is not None
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url, timeout=10.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = now
        assert _jwks_cache is not None
        return _jwks_cache


async def validate_jwt(token: str, jwks_url: str, audience: str, issuer: str) -> dict:
    jwks = await get_jwks(jwks_url)

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break

        if not key:
            raise ValueError("Key not found in JWKS")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid JWT: {e}") from e
