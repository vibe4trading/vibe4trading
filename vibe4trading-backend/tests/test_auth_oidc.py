from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import TracebackType

from _pytest.monkeypatch import MonkeyPatch

from v4t.auth import oidc


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"keys": [{"kid": "first"}]}


class _FakeAsyncClient:
    calls = 0

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def get(self, url: str, timeout: float) -> _FakeResponse:
        _FakeAsyncClient.calls += 1
        return _FakeResponse()


def test_get_jwks_refreshes_after_more_than_a_day(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(oidc, "_jwks_cache", {"keys": [{"kid": "stale"}]})
    monkeypatch.setattr(oidc, "_jwks_cache_url", "https://issuer.test/jwks")
    monkeypatch.setattr(oidc, "_jwks_cache_time", datetime.now(UTC) - timedelta(days=2))
    _FakeAsyncClient.calls = 0
    monkeypatch.setattr("v4t.auth.oidc.httpx.AsyncClient", _FakeAsyncClient)

    jwks = asyncio.run(oidc.get_jwks("https://issuer.test/jwks"))

    assert _FakeAsyncClient.calls == 1
    assert jwks == {"keys": [{"kid": "first"}]}
