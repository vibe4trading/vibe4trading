from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in (408, 429) or status >= 500
    return False


def call_with_retry(
    *,
    url: str,
    headers: dict[str, str],
    req: dict[str, Any],
    timeout_seconds: float,
    max_retries: int,
    retryable: Callable[[Exception], bool] = is_retryable,
) -> dict[str, Any]:
    last_exc: Exception | None = None
    data: dict[str, Any] | None = None
    max_attempts = max(1, max_retries)
    for attempt in range(1, max_attempts + 1):
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                r = client.post(url, headers=headers, json=req)
                r.raise_for_status()
                data = r.json()
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < max_attempts and retryable(exc):
                continue
            data = None
            break

    if data is None:
        raise last_exc or RuntimeError("LLM request failed")
    return data
