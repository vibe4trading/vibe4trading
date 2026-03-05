from __future__ import annotations

from datetime import UTC, datetime, timedelta

from v4t.ingest import rss as rss_mod
from v4t.ingest.rss import fetch_rss_items
from v4t.settings import get_settings


def test_fetch_rss_items_blocks_private_ip_without_network(monkeypatch) -> None:
    # If URL validation works, we should reject before constructing an HTTP client.
    class BoomClient:  # noqa: D101
        def __init__(self, *args, **kwargs):  # noqa: ANN002
            raise AssertionError("http client should not be constructed")

    monkeypatch.setattr(rss_mod.httpx, "Client", BoomClient)

    now = datetime.now(UTC)
    items, errors = fetch_rss_items(
        feeds=["http://127.0.0.1/feed.xml"],
        start=now - timedelta(days=1),
        end=now + timedelta(days=1),
        max_items=50,
    )
    assert items == []
    assert errors
    assert "127.0.0.1" in errors[0]


def test_fetch_rss_items_enforces_max_bytes(monkeypatch) -> None:
    monkeypatch.setenv("V4T_SENTIMENT_RSS_MAX_BYTES", "10")
    get_settings.cache_clear()

    class DummyResponse:  # noqa: D101
        def __init__(self):
            self.headers = {"content-length": "20"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):  # noqa: ANN201
            yield b"x" * 20

    class DummyClient:  # noqa: D101
        def __init__(self, *args, **kwargs):  # noqa: ANN002
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def stream(self, method, url):  # noqa: ANN001
            return DummyResponse()

    monkeypatch.setattr(rss_mod.httpx, "Client", DummyClient)

    now = datetime.now(UTC)
    items, errors = fetch_rss_items(
        feeds=["https://1.1.1.1/feed.xml"],
        start=now - timedelta(days=1),
        end=now + timedelta(days=1),
        max_items=50,
    )
    assert items == []
    assert errors
    assert "too large" in errors[0]
