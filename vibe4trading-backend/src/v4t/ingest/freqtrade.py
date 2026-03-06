from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pandas as pd

from v4t.contracts.events import EventEnvelope, make_event
from v4t.contracts.numbers import decimal_to_str
from v4t.contracts.payloads import MarketOHLCVPayload, MarketPricePayload


def _ensure_aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def generate_freqtrade_ohlcv_events(
    *,
    dataset_id: UUID,
    market_id: str,
    feather_path: Path,
    start: datetime,
    end: datetime,
    timeframe: str = "1h",
) -> Iterable[EventEnvelope]:
    start = _ensure_aware_utc(start)
    end = _ensure_aware_utc(end)

    df = pd.read_feather(feather_path)
    if "market_id" in df.columns:
        df = df[df["market_id"] == market_id]
    df = df[(df["date"] >= start) & (df["date"] <= end)]

    for _, row in df.iterrows():
        date_val = pd.Timestamp(row["date"]).to_pydatetime()  # type: ignore
        bar_start = _ensure_aware_utc(date_val)
        bar_end = bar_start + timedelta(hours=1)

        close = Decimal(str(row["close"]))

        price_payload = MarketPricePayload(
            market_id=market_id,
            price=decimal_to_str(close),
        ).model_dump(mode="json")
        yield make_event(
            event_type="market.price",
            source="ingest.freqtrade",
            observed_at=bar_end,
            event_time=bar_end,
            dedupe_key=f"{market_id}:price:{bar_end.isoformat()}",
            dataset_id=dataset_id,
            payload=price_payload,
        )

        payload = MarketOHLCVPayload(
            market_id=market_id,
            timeframe=timeframe,
            bar_start=bar_start,
            bar_end=bar_end,
            o=decimal_to_str(Decimal(str(row["open"]))),
            h=decimal_to_str(Decimal(str(row["high"]))),
            l=decimal_to_str(Decimal(str(row["low"]))),
            c=decimal_to_str(close),
            volume_base=decimal_to_str(Decimal(str(row["volume"]))),
            volume_quote=None,
        ).model_dump(mode="json")

        yield make_event(
            event_type="market.ohlcv",
            source="ingest.freqtrade",
            observed_at=bar_end,
            event_time=bar_end,
            dedupe_key=f"{market_id}:{timeframe}:{bar_start.isoformat()}",
            dataset_id=dataset_id,
            payload=payload,
        )
