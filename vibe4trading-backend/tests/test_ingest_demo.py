from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from v4t.ingest.demo import (
    DemoSpotParams,
    _ceil_to_minute,
    _floor_to_hour,
    generate_demo_spot_events,
)


def test_ceil_to_minute_already_on_minute() -> None:
    dt = datetime(2024, 1, 1, 12, 30, 0, 0, tzinfo=UTC)
    result = _ceil_to_minute(dt)
    assert result == dt


def test_ceil_to_minute_rounds_up() -> None:
    dt = datetime(2024, 1, 1, 12, 30, 15, 0, tzinfo=UTC)
    result = _ceil_to_minute(dt)
    assert result == datetime(2024, 1, 1, 12, 31, 0, 0, tzinfo=UTC)


def test_floor_to_hour() -> None:
    dt = datetime(2024, 1, 1, 12, 45, 30, 0, tzinfo=UTC)
    result = _floor_to_hour(dt)
    assert result == datetime(2024, 1, 1, 12, 0, 0, 0, tzinfo=UTC)


def test_generate_demo_spot_events_deterministic() -> None:
    dataset_id = uuid4()
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)
    params = DemoSpotParams(market_id="spot:demo:BTC", base_price=Decimal("100"))

    events1 = list(
        generate_demo_spot_events(dataset_id=dataset_id, start=start, end=end, params=params)
    )
    events2 = list(
        generate_demo_spot_events(dataset_id=dataset_id, start=start, end=end, params=params)
    )

    assert len(events1) == len(events2)
    assert len(events1) > 0
    for e1, e2 in zip(events1, events2, strict=True):
        assert e1.event_type == e2.event_type
        assert e1.payload == e2.payload


def test_generate_demo_spot_events_empty_range() -> None:
    dataset_id = uuid4()
    start = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    params = DemoSpotParams(market_id="spot:demo:BTC")

    events = list(
        generate_demo_spot_events(dataset_id=dataset_id, start=start, end=end, params=params)
    )
    assert len(events) == 0


def test_generate_demo_spot_events_has_price_and_ohlcv() -> None:
    dataset_id = uuid4()
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 1, 2, 0, 0, tzinfo=UTC)
    params = DemoSpotParams(market_id="spot:demo:BTC")

    events = list(
        generate_demo_spot_events(dataset_id=dataset_id, start=start, end=end, params=params)
    )

    price_events = [e for e in events if e.event_type == "market.price"]
    ohlcv_events = [e for e in events if e.event_type == "market.ohlcv"]

    assert len(price_events) > 0
    assert len(ohlcv_events) > 0
