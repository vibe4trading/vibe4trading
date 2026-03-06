from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import httpx
from jose import JWTError, jwt

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_time: datetime | None = None
_jwks_cache_url: str | None = None
_jwks_cache_lock = asyncio.Lock()


def _cache_is_fresh(*, jwks_url: str, now: datetime) -> bool:
    return (
        _jwks_cache is not None
        and _jwks_cache_time is not None
        and _jwks_cache_url == jwks_url
        and (now - _jwks_cache_time).total_seconds() < 3600
    )


async def get_jwks(jwks_url: str) -> dict[str, Any]:
    global _jwks_cache, _jwks_cache_time, _jwks_cache_url

    now = datetime.now(UTC)
    if _cache_is_fresh(jwks_url=jwks_url, now=now):
        assert _jwks_cache is not None
        return _jwks_cache

    async with _jwks_cache_lock:
        now = datetime.now(UTC)
        if _cache_is_fresh(jwks_url=jwks_url, now=now):
            assert _jwks_cache is not None
            return _jwks_cache

        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url, timeout=10.0)
            resp.raise_for_status()
            _jwks_cache = cast(dict[str, Any], resp.json())
            _jwks_cache_time = now
            _jwks_cache_url = jwks_url
            assert _jwks_cache is not None
            return _jwks_cache


async def validate_jwt(token: str, jwks_url: str, audience: str, issuer: str) -> dict[str, Any]:
    jwks = await get_jwks(jwks_url)

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key: dict[str, Any] | None = None
        keys_raw = jwks.get("keys", [])
        keys: list[dict[str, Any]] = (
            [
                cast(dict[str, Any], item)
                for item in cast(list[object], keys_raw)
                if isinstance(item, dict)
            ]
            if isinstance(keys_raw, list)
            else []
        )
        for key_candidate in keys:
            if key_candidate.get("kid") == kid:
                key = key_candidate
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
