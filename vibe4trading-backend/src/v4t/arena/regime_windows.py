from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.arena.scenario_sets import ScenarioWindow
from v4t.contracts.payloads import MarketOHLCVPayload
from v4t.db.models import EventRow
from v4t.utils.datetime import as_utc

_logger = structlog.get_logger()


def _parse_timeframe(timeframe: str) -> timedelta:
    s = (timeframe or "").strip()
    if len(s) < 2:
        raise ValueError(f"Invalid timeframe: {timeframe!r}")

    unit = s[-1]
    try:
        n = int(s[:-1])
    except ValueError as exc:
        raise ValueError(f"Invalid timeframe: {timeframe!r}") from exc
    if n <= 0:
        raise ValueError(f"Invalid timeframe: {timeframe!r}")

    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    raise ValueError(f"Invalid timeframe unit: {timeframe!r}")


def _mean_std(xs: list[float]) -> tuple[float, float]:
    if not xs:
        return (0.0, 0.0)
    mean = sum(xs) / float(len(xs))
    var = sum((x - mean) ** 2 for x in xs) / float(len(xs))
    return (mean, math.sqrt(var))


@dataclass(frozen=True)
class _Candidate:
    start_i: int
    end_i: int
    start: datetime
    end: datetime
    ret: float
    vol: float
    choppy: float
    drawdown: float

    z_ret: float = 0.0
    z_vol: float = 0.0
    z_choppy: float = 0.0
    z_drawdown: float = 0.0


def _candidate_features(
    closes: list[float], *, start_i: int, window_len_bars: int
) -> tuple[float, float, float, float]:
    end_i = start_i + window_len_bars - 1
    c0 = closes[start_i]
    c1 = closes[end_i]
    ret = (c1 / c0) - 1.0 if c0 > 0 else 0.0

    rets: list[float] = []
    sum_abs = 0.0
    for j in range(start_i + 1, end_i + 1):
        a = closes[j - 1]
        b = closes[j]
        if a <= 0 or b <= 0:
            continue
        r = math.log(b / a)
        rets.append(r)
        sum_abs += abs(r)
    if rets:
        m = sum(rets) / float(len(rets))
        var = sum((r - m) ** 2 for r in rets) / float(len(rets))
        vol = math.sqrt(var)
    else:
        vol = 0.0

    peak = closes[start_i]
    dd = 0.0
    for j in range(start_i, end_i + 1):
        px = closes[j]
        if px > peak:
            peak = px
        if peak > 0:
            dd = min(dd, (px / peak) - 1.0)

    return (ret, vol, sum_abs, dd)


def _load_ohlcv_bars(
    session: Session, *, dataset_id: UUID, market_id: str, timeframe: str
) -> list[MarketOHLCVPayload]:
    rows = list(
        session.execute(
            select(EventRow)
            .where(EventRow.dataset_id == dataset_id, EventRow.event_type == "market.ohlcv")
            .order_by(EventRow.observed_at.asc())
        )
        .scalars()
        .all()
    )

    out: list[MarketOHLCVPayload] = []
    for r in rows:
        try:
            b = MarketOHLCVPayload.model_validate(r.payload)
        except Exception:
            _logger.warning("skipping unparseable OHLCV event", event_id=r.event_id, exc_info=True)
            continue
        if b.market_id != market_id:
            continue
        if b.timeframe != timeframe:
            continue
        out.append(b)
    return out


def compute_regime_windows(
    session: Session,
    *,
    dataset_id: UUID,
    market_id: str,
    timeframe: str,
    window_hours: int = 12,
    n_windows: int = 10,
) -> list[ScenarioWindow]:
    bars = _load_ohlcv_bars(
        session, dataset_id=dataset_id, market_id=market_id, timeframe=timeframe
    )
    if not bars:
        raise ValueError(f"No OHLCV bars found for dataset_id={dataset_id}")

    tf = _parse_timeframe(timeframe)
    window_len = timedelta(hours=int(window_hours))
    if window_len.total_seconds() <= 0:
        raise ValueError("window_hours must be > 0")
    if window_len.total_seconds() % tf.total_seconds() != 0:
        raise ValueError(f"window_hours={window_hours} not aligned with timeframe={timeframe}")
    window_len_bars = int(window_len.total_seconds() // tf.total_seconds())
    if window_len_bars < 2:
        raise ValueError("window too small")

    closes: list[float] = []
    bar_ends: list[datetime] = []
    bar_starts: list[datetime] = []
    for b in bars:
        try:
            closes.append(float(Decimal(str(b.c))))
        except Exception as exc:
            _logger.error(
                "regime_windows: invalid close price",
                bar_start=b.bar_start,
                close=b.c,
                error=str(exc),
            )
            raise ValueError(f"Invalid close price in bar: {b.c}") from exc
        bar_starts.append(as_utc(b.bar_start))
        bar_ends.append(as_utc(b.bar_end))

    n = len(bars)
    if n < window_len_bars:
        raise ValueError("Not enough bars to compute windows")

    candidates: list[_Candidate] = []
    expected_span = tf * (window_len_bars - 1)
    for i in range(0, n - window_len_bars + 1):
        j = i + window_len_bars - 1
        if bar_ends[j] - bar_ends[i] != expected_span:
            continue

        ret, vol, choppy, dd = _candidate_features(
            closes, start_i=i, window_len_bars=window_len_bars
        )
        candidates.append(
            _Candidate(
                start_i=i,
                end_i=j,
                start=bar_starts[i],
                end=bar_ends[j],
                ret=ret,
                vol=vol,
                choppy=choppy,
                drawdown=dd,
            )
        )

    if not candidates:
        raise ValueError("No contiguous candidate windows found")

    rets = [c.ret for c in candidates]
    vols = [c.vol for c in candidates]
    chs = [c.choppy for c in candidates]
    dds = [c.drawdown for c in candidates]

    mean_ret, std_ret = _mean_std(rets)
    mean_vol, std_vol = _mean_std(vols)
    mean_ch, std_ch = _mean_std(chs)
    mean_dd, std_dd = _mean_std(dds)

    def z(x: float, mean: float, std: float) -> float:
        if std <= 0:
            return 0.0
        return (x - mean) / std

    candidates_z: list[_Candidate] = []
    for c in candidates:
        candidates_z.append(
            _Candidate(
                **{
                    **c.__dict__,
                    "z_ret": z(c.ret, mean_ret, std_ret),
                    "z_vol": z(c.vol, mean_vol, std_vol),
                    "z_choppy": z(c.choppy, mean_ch, std_ch),
                    "z_drawdown": z(c.drawdown, mean_dd, std_dd),
                }
            )
        )

    def select_with_min_sep(min_start_sep: int) -> list[_Candidate]:
        selected: list[_Candidate] = []
        selected_starts: list[int] = []

        def ok(c: _Candidate) -> bool:
            return all(abs(c.start_i - s) >= min_start_sep for s in selected_starts)

        def pick(sorted_iter: Iterable[_Candidate]) -> None:
            for cand in sorted_iter:
                if ok(cand):
                    selected.append(cand)
                    selected_starts.append(cand.start_i)
                    return

        pick(sorted(candidates_z, key=lambda c: (c.ret, c.start_i)))
        pick(sorted(candidates_z, key=lambda c: (-c.ret, c.start_i)))
        pick(sorted(candidates_z, key=lambda c: (-c.vol, c.start_i)))
        pick(sorted(candidates_z, key=lambda c: (c.vol, c.start_i)))
        pick(sorted(candidates_z, key=lambda c: (abs(c.ret), c.start_i)))

        def dist(a: _Candidate, b: _Candidate) -> float:
            return math.sqrt(
                (a.z_ret - b.z_ret) ** 2
                + (a.z_vol - b.z_vol) ** 2
                + (a.z_choppy - b.z_choppy) ** 2
                + (a.z_drawdown - b.z_drawdown) ** 2
            )

        while len(selected) < int(n_windows):
            best: _Candidate | None = None
            best_score = -1.0
            for cand in candidates_z:
                if cand in selected:
                    continue
                if not ok(cand):
                    continue
                nearest = min((dist(cand, s) for s in selected), default=0.0)
                if nearest > best_score or (
                    math.isclose(nearest, best_score)
                    and best is not None
                    and cand.start_i < best.start_i
                ):
                    best = cand
                    best_score = nearest

            if best is None:
                break
            selected.append(best)
            selected_starts.append(best.start_i)

        return selected

    min_seps = [window_len_bars, max(1, window_len_bars // 2), max(1, window_len_bars // 4), 1, 0]
    chosen: list[_Candidate] = []
    for sep in min_seps:
        chosen = select_with_min_sep(sep)
        if len(chosen) >= int(n_windows):
            chosen = chosen[: int(n_windows)]
            break
    if len(chosen) < int(n_windows):
        chosen = sorted(candidates_z, key=lambda c: c.start_i)[: int(n_windows)]

    labels = [
        "Black Swan",
        "Bull Run",
        "Vol Spike",
        "Low Vol",
        "Sideways",
    ]
    windows: list[ScenarioWindow] = []
    for i, c in enumerate(chosen):
        label = labels[i] if i < len(labels) else f"Regime {i + 1}"
        windows.append(
            ScenarioWindow(
                index=i,
                label=label,
                start=as_utc(c.start),
                end=as_utc(c.end),
            )
        )

    return windows
