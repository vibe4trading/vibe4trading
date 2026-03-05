from __future__ import annotations

import random
import time
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


def compute_backoff_seconds(*, attempt: int, exc: Exception) -> float:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            ra = exc.response.headers.get("Retry-After")
            if ra:
                try:
                    seconds = float(ra)
                    if seconds >= 0:
                        return min(10.0, seconds)
                except Exception:
                    pass

    base = 0.05
    cap = 2.0
    raw = min(cap, base * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0.8, 1.2)
    return max(0.0, raw * jitter)


def _sleep_before_retry(*, attempt: int, exc: Exception) -> None:
    delay = compute_backoff_seconds(attempt=attempt, exc=exc)
    if delay > 0:
        time.sleep(delay)


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
    max_attempts = max(1, int(max_retries) + 1)

    with httpx.Client(timeout=timeout_seconds) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                r = client.post(url, headers=headers, json=req)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_attempts and retryable(exc):
                    _sleep_before_retry(attempt=attempt, exc=exc)
                    continue
                data = None
                break

    if data is None:
        raise last_exc or RuntimeError("LLM request failed")
    return data
