from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from v4t.ingest.demo import DemoSpotParams, generate_demo_spot_events


def test_demo_spot_deterministic_prices() -> None:
    dataset_id = UUID("00000000-0000-0000-0000-000000000123")
    start = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=6)

    params = DemoSpotParams(market_id="spot:demo:DEMO", base_price=Decimal("1.23"))
    ev1 = list(
        generate_demo_spot_events(dataset_id=dataset_id, start=start, end=end, params=params)
    )
    ev2 = list(
        generate_demo_spot_events(dataset_id=dataset_id, start=start, end=end, params=params)
    )

    prices1 = [e.payload["price"] for e in ev1 if e.event_type == "market.price"][:25]
    prices2 = [e.payload["price"] for e in ev2 if e.event_type == "market.price"][:25]

    assert prices1 == prices2
