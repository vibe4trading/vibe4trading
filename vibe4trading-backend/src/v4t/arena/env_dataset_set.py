from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.db.models import DatasetRow
from v4t.settings import get_settings, parse_csv_set
from v4t.utils.datetime import as_utc


@dataclass(frozen=True)
class ArenaEnvDatasetSet:
    spot_by_market: dict[str, list[DatasetRow]]
    windows: list[tuple[datetime, datetime]]

    @property
    def market_ids(self) -> list[str]:
        return sorted(self.spot_by_market.keys())


def _parse_uuid_csv(raw: str | None) -> list[UUID] | None:
    items = parse_csv_set(raw)
    if items is None:
        return None

    out: list[UUID] = []
    for s in sorted(items):
        out.append(UUID(s))
    return out or None


def _ceil_to_hour(dt: datetime) -> datetime:
    dt = as_utc(dt)
    floored = dt.replace(minute=0, second=0, microsecond=0)
    if floored < dt:
        return floored + timedelta(hours=1)
    return floored


def _floor_to_hour(dt: datetime) -> datetime:
    dt = as_utc(dt)
    return dt.replace(minute=0, second=0, microsecond=0)


def _compute_windows(*, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    start = _ceil_to_hour(start)
    end = _floor_to_hour(end)

    window_len = timedelta(hours=12)
    n = 10
    latest_start = end - window_len
    if latest_start <= start:
        raise ValueError("Arena env dataset window range too small")

    total_hours = int((latest_start - start).total_seconds() // 3600)
    if total_hours <= 0:
        raise ValueError("Arena env dataset window range too small")

    windows: list[tuple[datetime, datetime]] = []
    prev_start: datetime | None = None
    for i in range(n):
        frac = 0.0 if n == 1 else i / (n - 1)
        offset_hours = int(math.floor(frac * total_hours))
        w_start = start + timedelta(hours=offset_hours)
        if prev_start is not None and w_start <= prev_start:
            w_start = prev_start + timedelta(hours=1)
        if w_start > latest_start:
            w_start = latest_start
        w_end = w_start + window_len
        if w_end > end:
            raise ValueError("Arena env dataset computed window exceeds dataset range")

        windows.append((w_start.replace(tzinfo=UTC), w_end.replace(tzinfo=UTC)))
        prev_start = w_start

    return windows


def load_arena_env_dataset_set(session: Session) -> ArenaEnvDatasetSet | None:
    ids = _parse_uuid_csv(get_settings().arena_dataset_ids)
    if not ids:
        return None

    rows = list(
        session.execute(select(DatasetRow).where(DatasetRow.dataset_id.in_(ids))).scalars().all()
    )
    by_id = {r.dataset_id: r for r in rows}
    missing = [str(x) for x in ids if x not in by_id]
    if missing:
        raise ValueError(
            "Arena env dataset set references missing dataset_id(s): " + ", ".join(missing[:5])
        )

    spot_by_market: dict[str, list[DatasetRow]] = {}
    for r in rows:
        if r.category != "spot":
            continue
        market_id = str((r.params or {}).get("market_id") or "").strip()
        if not market_id:
            raise ValueError(
                f"Arena env dataset missing params.market_id: dataset_id={r.dataset_id}"
            )
        spot_by_market.setdefault(market_id, []).append(r)

    if not spot_by_market:
        raise ValueError("Arena env dataset set contains no spot datasets")

    for m in list(spot_by_market.keys()):
        spot_by_market[m].sort(
            key=lambda ds: (as_utc(ds.start), as_utc(ds.end), str(ds.dataset_id))
        )

    counts = {len(v) for v in spot_by_market.values()}
    if counts == {10}:
        first_market = sorted(spot_by_market.keys())[0]
        canonical = [(as_utc(ds.start), as_utc(ds.end)) for ds in spot_by_market[first_market]]
        for m, dss in spot_by_market.items():
            windows = [(as_utc(ds.start), as_utc(ds.end)) for ds in dss]
            if windows != canonical:
                raise ValueError(
                    f"Arena env dataset windows must match across markets. Mismatch for market_id={m}"
                )
        return ArenaEnvDatasetSet(spot_by_market=spot_by_market, windows=canonical)

    if counts == {1}:
        starts = [as_utc(v[0].start) for v in spot_by_market.values() if v]
        ends = [as_utc(v[0].end) for v in spot_by_market.values() if v]
        windows = _compute_windows(start=max(starts), end=min(ends))
        return ArenaEnvDatasetSet(spot_by_market=spot_by_market, windows=windows)

    raise ValueError("Arena env dataset set must provide either 1 or 10 spot datasets per market")


def list_arena_env_markets(session: Session) -> list[str]:
    env_set = load_arena_env_dataset_set(session)
    if env_set is None:
        return []
    return env_set.market_ids


def get_arena_env_spot_datasets(session: Session, *, market_id: str) -> list[DatasetRow] | None:
    env_set = load_arena_env_dataset_set(session)
    if env_set is None:
        return None
    return env_set.spot_by_market.get(market_id)
