from __future__ import annotations

from datetime import UTC, datetime, timedelta


def now() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def floor_time(dt: datetime, *, step_seconds: int) -> datetime:
    dt = as_utc(dt)
    step_seconds = max(1, int(step_seconds))
    epoch = int(dt.timestamp())
    floored = (epoch // step_seconds) * step_seconds
    return datetime.fromtimestamp(floored, tz=UTC)


def ceil_time(dt: datetime, *, step_seconds: int) -> datetime:
    dt = as_utc(dt)
    step_seconds = max(1, int(step_seconds))
    floored = floor_time(dt, step_seconds=step_seconds)
    if floored == dt:
        return floored
    return floored + timedelta(seconds=step_seconds)


def ceil_seconds(delta_seconds: int, *, step: int) -> int:
    if step <= 0:
        return delta_seconds
    if delta_seconds % step == 0:
        return delta_seconds
    return ((delta_seconds // step) + 1) * step
