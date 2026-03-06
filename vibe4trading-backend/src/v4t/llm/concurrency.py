from __future__ import annotations

import atexit
import contextvars
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any, Final, cast

import structlog

from v4t.settings import get_settings

_LOG: Final = structlog.get_logger("llm.concurrency")
_STOP_PRIORITY: Final = 10**9
_STOP_SENTINEL: Final = object()

T = Any
QueueEntry = tuple[int, int, object]


class QueueFullError(RuntimeError):
    def __init__(self, queue_name: str, max_queue_size: int) -> None:
        super().__init__(f"Queue '{queue_name}' is full (max_size={max_queue_size})")
        self.queue_name = queue_name
        self.max_queue_size = max_queue_size


@dataclass(slots=True)
class QueueJob:
    ctx: contextvars.Context
    func: Any
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    result_future: Future[Any]
    queued_at: float


class SyncTaskQueue:
    def __init__(self, name: str, max_concurrent: int, max_queue_size: int | None = None) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")

        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size if (max_queue_size or 0) > 0 else None

        queue_max = self.max_queue_size or 0
        self._queue: queue.PriorityQueue[QueueEntry] = queue.PriorityQueue(maxsize=queue_max)
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._workers: list[threading.Thread] = []
        self._sequence = 0
        self._in_flight = 0
        self._stopped = False

    def submit(
        self,
        func: Any,
        *args: Any,
        queue_priority: int = 0,
        **kwargs: Any,
    ) -> Any:
        with self._lock:
            if self._stopped:
                raise RuntimeError(f"Queue '{self.name}' is stopped")
            self._ensure_workers_locked()
            sequence = self._sequence
            self._sequence += 1

        result_future: Future[Any] = Future()
        job = QueueJob(
            ctx=contextvars.copy_context(),
            func=func,
            args=args,
            kwargs=kwargs,
            result_future=result_future,
            queued_at=time.monotonic(),
        )

        try:
            self._queue.put_nowait((int(queue_priority), sequence, job))
        except queue.Full as exc:
            max_size = self.max_queue_size or 0
            raise QueueFullError(self.name, max_size) from exc

        return result_future.result()

    def stats(self) -> dict[str, Any]:
        with self._stats_lock:
            in_flight = self._in_flight
        return {
            "pending": self._queue.qsize(),
            "in_flight": in_flight,
            "max_concurrent": self.max_concurrent,
            "max_queue_size": self.max_queue_size,
            "stopped": self._stopped,
        }

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self, *, cancel_queued: bool = True) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            workers = list(self._workers)

        if cancel_queued:
            self._drain_queued_jobs()

        for _worker in workers:
            self._enqueue_stop_sentinel()

        for worker in workers:
            worker.join(timeout=1.0)

    def _ensure_workers_locked(self) -> None:
        if self._workers:
            return
        for index in range(self.max_concurrent):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self.name}-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

    def _enqueue_stop_sentinel(self) -> None:
        while True:
            try:
                self._queue.put_nowait((_STOP_PRIORITY, 0, _STOP_SENTINEL))
                return
            except queue.Full:
                time.sleep(0.01)

    def _drain_queued_jobs(self) -> None:
        while True:
            try:
                _priority, _sequence, item = self._queue.get_nowait()
            except queue.Empty:
                return

            try:
                if item is _STOP_SENTINEL:
                    continue
                job = cast(QueueJob, item)
                if not job.result_future.done():
                    job.result_future.set_exception(RuntimeError(f"Queue '{self.name}' stopped"))
            finally:
                self._queue.task_done()

    def _worker_loop(self) -> None:
        while True:
            _priority, _sequence, item = self._queue.get()
            try:
                if item is _STOP_SENTINEL:
                    return

                job = cast(QueueJob, item)
                if job.result_future.cancelled():
                    continue

                with self._stats_lock:
                    self._in_flight += 1

                try:
                    result = job.ctx.run(job.func, *job.args, **job.kwargs)
                except BaseException as exc:
                    if not job.result_future.done():
                        job.result_future.set_exception(exc)
                else:
                    if not job.result_future.done():
                        job.result_future.set_result(result)
                finally:
                    with self._stats_lock:
                        self._in_flight -= 1
            finally:
                self._queue.task_done()


_queue_lock = threading.Lock()
_llm_request_queue: SyncTaskQueue | None = None
_llm_request_queue_config: tuple[int, int] | None = None


def get_llm_request_queue() -> SyncTaskQueue:
    global _llm_request_queue, _llm_request_queue_config

    settings = get_settings()
    max_concurrent = max(1, int(settings.llm_max_concurrent_requests))
    configured_queue_size = settings.llm_max_queued_requests
    if isinstance(configured_queue_size, int) and configured_queue_size > 0:
        max_queue_size = configured_queue_size
    else:
        max_queue_size = max_concurrent * 3

    desired = (max_concurrent, max_queue_size)
    with _queue_lock:
        if (
            _llm_request_queue is None
            or _llm_request_queue.stopped
            or _llm_request_queue_config != desired
        ):
            old_queue = _llm_request_queue
            _llm_request_queue = SyncTaskQueue(
                name="llm_requests",
                max_concurrent=max_concurrent,
                max_queue_size=max_queue_size,
            )
            _llm_request_queue_config = desired
            if old_queue is not None and not old_queue.stopped:
                old_queue.stop(cancel_queued=False)
            _LOG.info("llm_request_queue_initialized", **_llm_request_queue.stats())
        return _llm_request_queue


def submit_llm_request(
    func: Any,
    *args: Any,
    queue_priority: int = 0,
    **kwargs: Any,
) -> Any:
    return get_llm_request_queue().submit(
        func,
        *args,
        queue_priority=queue_priority,
        **kwargs,
    )


def reset_llm_request_queue() -> None:
    global _llm_request_queue, _llm_request_queue_config

    with _queue_lock:
        queue_ref = _llm_request_queue
        _llm_request_queue = None
        _llm_request_queue_config = None

    if queue_ref is not None and not queue_ref.stopped:
        queue_ref.stop(cancel_queued=True)


atexit.register(reset_llm_request_queue)
