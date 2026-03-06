from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from v4t.contracts.events import EventEnvelope, make_event
from v4t.contracts.numbers import decimal_to_str
from v4t.contracts.payloads import (
    MarketOHLCVPayload,
    MarketPricePayload,
    SentimentItemKind,
    SentimentItemPayload,
    SentimentItemSummaryPayload,
)


@dataclass(frozen=True)
class DemoSpotParams:
    market_id: str
    base_price: Decimal = Decimal("1.00")


def _ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _ceil_to_minute(dt: datetime) -> datetime:
    dt = _ensure_aware_utc(dt)
    floored = dt.replace(second=0, microsecond=0)
    if floored < dt:
        return floored + timedelta(minutes=1)
    return floored


def _floor_to_hour(dt: datetime) -> datetime:
    dt = _ensure_aware_utc(dt)
    return dt.replace(minute=0, second=0, microsecond=0)


def _rng_from_uuid(seed_uuid: UUID) -> random.Random:
    # Seed is stable and portable.
    return random.Random(seed_uuid.int & 0xFFFFFFFF)


def generate_demo_spot_events(
    *,
    dataset_id: UUID,
    start: datetime,
    end: datetime,
    params: DemoSpotParams,
    price_tick_seconds: int = 60,
    ohlcv_timeframe: str = "1h",
) -> Iterable[EventEnvelope]:
    """Deterministic synthetic spot dataset for end-to-end demos.

    Emits:
    - `market.price` at `price_tick_seconds` cadence
    - `market.ohlcv` at 1h timeframe (bars close at bar_end)
    """

    start = _ensure_aware_utc(start)
    end = _ensure_aware_utc(end)
    if end <= start:
        return

    rng = _rng_from_uuid(dataset_id)

    tick = timedelta(seconds=price_tick_seconds)
    t = _ceil_to_minute(start)

    # Minute-level price path: multiplicative random walk in (bps) space.
    price = params.base_price
    prices_by_minute: list[tuple[datetime, Decimal]] = []
    while t <= end:
        step_bp = rng.randint(-12, 12)  # +-12 bps per minute
        drift_bp = 1  # tiny drift upwards
        price = (price * Decimal(10000 + drift_bp + step_bp)) / Decimal(10000)
        if price <= 0:
            price = params.base_price
        # Keep strings small/stable.
        price_q = price.quantize(Decimal("0.000001"))
        prices_by_minute.append((t, price_q))
        t = t + tick

    for ts, px in prices_by_minute:
        payload = MarketPricePayload(
            market_id=params.market_id,
            price=decimal_to_str(px),
        ).model_dump(mode="json")
        yield make_event(
            event_type="market.price",
            source="ingest.demo",
            observed_at=ts,
            event_time=ts,
            dedupe_key=f"{params.market_id}:{ts.isoformat()}",
            dataset_id=dataset_id,
            payload=payload,
        )

    # Build hourly OHLCV bars from the minute series.
    start_hour = _floor_to_hour(start)
    hour = start_hour
    while hour + timedelta(hours=1) <= end:
        bar_start = hour
        bar_end = hour + timedelta(hours=1)

        in_bar = [px for (ts, px) in prices_by_minute if bar_start <= ts < bar_end]
        if not in_bar:
            hour = bar_end
            continue

        o = in_bar[0]
        h = max(in_bar)
        l = min(in_bar)
        c = in_bar[-1]

        # Deterministic volume.
        volume_base = Decimal(rng.randint(50, 500)) / Decimal(10)
        volume_quote = (volume_base * c).quantize(Decimal("0.01"))

        payload = MarketOHLCVPayload(
            market_id=params.market_id,
            timeframe=ohlcv_timeframe,
            bar_start=bar_start,
            bar_end=bar_end,
            o=decimal_to_str(o),
            h=decimal_to_str(h),
            l=decimal_to_str(l),
            c=decimal_to_str(c),
            volume_base=decimal_to_str(volume_base),
            volume_quote=decimal_to_str(volume_quote),
        ).model_dump(mode="json")
        yield make_event(
            event_type="market.ohlcv",
            source="ingest.demo",
            observed_at=bar_end,
            event_time=bar_end,
            dedupe_key=f"{params.market_id}:{ohlcv_timeframe}:{bar_start.isoformat()}",
            dataset_id=dataset_id,
            payload=payload,
        )

        hour = bar_end


def generate_demo_sentiment_events(
    *,
    dataset_id: UUID,
    start: datetime,
    end: datetime,
    market_id: str,
    max_items: int = 12,
) -> Iterable[EventEnvelope]:
    """Deterministic synthetic sentiment dataset.

    The MVP allows empty sentiment datasets; this generator emits a small number of
    items+summaries for demos, spaced across the window.
    """

    start = _ensure_aware_utc(start)
    end = _ensure_aware_utc(end)
    if end <= start:
        return

    rng = _rng_from_uuid(dataset_id)
    total_seconds = int((end - start).total_seconds())
    if total_seconds <= 0:
        return

    items = min(max_items, max(0, total_seconds // (3 * 3600)))
    if items == 0:
        return

    for i in range(items):
        offset = int((i + 1) * total_seconds / (items + 1))
        ts = start + timedelta(seconds=offset)
        external_id = f"demo:{dataset_id.hex}:{i}"

        kind = SentimentItemKind.x_post if i % 2 == 0 else SentimentItemKind.news
        text = f"{kind}: chatter about {market_id} (demo item {i})"
        url = f"https://example.invalid/{external_id}"

        item_payload = SentimentItemPayload(
            source="demo",
            external_id=external_id,
            item_time=ts,
            item_kind=kind,
            text=text,
            url=url,
        ).model_dump(mode="json")
        yield make_event(
            event_type="sentiment.item",
            source="ingest.demo",
            observed_at=ts,
            event_time=ts,
            dedupe_key=f"demo:{external_id}",
            dataset_id=dataset_id,
            payload=item_payload,
        )

        summary_text = (
            f"Summary: {market_id} mentioned; tone={rng.choice(['bullish', 'neutral', 'bearish'])}."
        )
        summary_payload = SentimentItemSummaryPayload(
            source="demo",
            external_id=external_id,
            item_time=ts,
            item_kind=kind,
            summary_text=summary_text,
            tags=["demo"],
        ).model_dump(mode="json")
        yield make_event(
            event_type="sentiment.item_summary",
            source="ingest.demo",
            observed_at=ts,
            event_time=ts,
            dedupe_key=f"demo:{external_id}",
            dataset_id=dataset_id,
            payload=summary_payload,
        )
