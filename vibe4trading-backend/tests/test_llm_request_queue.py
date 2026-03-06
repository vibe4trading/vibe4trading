from __future__ import annotations

import threading
import time

import pytest

from v4t.llm.concurrency import QueueFullError, SyncTaskQueue, reset_llm_request_queue
from v4t.llm.retry import call_with_retry
from v4t.settings import get_settings


@pytest.fixture(autouse=True)
def _reset_global_llm_queue() -> None:
    reset_llm_request_queue()
    yield
    reset_llm_request_queue()
    get_settings.cache_clear()


def test_sync_task_queue_limits_concurrency() -> None:
    task_queue = SyncTaskQueue(name="test_llm", max_concurrent=2, max_queue_size=8)
    active = 0
    peak = 0
    lock = threading.Lock()

    def _work() -> int:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.05)
            return 1
        finally:
            with lock:
                active -= 1

    results: list[int] = []

    def _submit() -> None:
        results.append(task_queue.submit(_work))

    threads = [threading.Thread(target=_submit) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [1, 1, 1, 1, 1, 1]
    assert peak == 2


def test_sync_task_queue_raises_when_full() -> None:
    task_queue = SyncTaskQueue(name="test_llm", max_concurrent=1, max_queue_size=1)
    started = threading.Event()
    release = threading.Event()

    def _blocking() -> str:
        started.set()
        release.wait(timeout=1.0)
        return "done"

    first = threading.Thread(target=lambda: task_queue.submit(_blocking))
    first.start()
    assert started.wait(timeout=1.0)

    second_ready = threading.Event()

    def _enqueue_second() -> None:
        second_ready.set()
        task_queue.submit(_blocking)

    second = threading.Thread(target=_enqueue_second)
    second.start()
    assert second_ready.wait(timeout=1.0)
    time.sleep(0.05)

    with pytest.raises(QueueFullError):
        task_queue.submit(_blocking)

    release.set()
    first.join()
    second.join()


def test_call_with_retry_routes_requests_through_global_queue(monkeypatch) -> None:
    monkeypatch.setenv("V4T_LLM_MAX_CONCURRENT_REQUESTS", "2")
    monkeypatch.setenv("V4T_LLM_MAX_QUEUED_REQUESTS", "8")
    get_settings.cache_clear()

    active = 0
    peak = 0
    lock = threading.Lock()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": "ok"}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def post(self, url, headers=None, json=None):  # noqa: ANN001
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.05)
                return FakeResponse()
            finally:
                with lock:
                    active -= 1

    threads = [
        threading.Thread(
            target=lambda: call_with_retry(
                url="http://example.invalid/chat/completions",
                headers={"Authorization": "Bearer x"},
                req={"model": "gpt-4o-mini", "messages": []},
                timeout_seconds=1.0,
                max_retries=0,
            )
        )
        for _ in range(6)
    ]

    monkeypatch.setattr("v4t.llm.retry.httpx.Client", FakeClient)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak == 2
