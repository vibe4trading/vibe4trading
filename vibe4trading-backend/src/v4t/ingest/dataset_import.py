from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from v4t.contracts.events import EventEnvelope
from v4t.db.event_store import append_event
from v4t.db.models import DatasetRow
from v4t.ingest.demo import (
    DemoSpotParams,
    generate_demo_sentiment_events,
    generate_demo_spot_events,
)
from v4t.ingest.freqtrade import generate_freqtrade_ohlcv_events
from v4t.ingest.tweets import generate_tweet_sentiment_events
from v4t.settings import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


def _insert_dataset_event(session: Session, *, ev: EventEnvelope) -> None:
    append_event(session, ev=ev, dedupe_scope="dataset")


def import_dataset(session: Session, *, dataset_id: UUID) -> None:
    ds = session.get(DatasetRow, dataset_id)
    if ds is None:
        raise ValueError(f"dataset_id not found: {dataset_id}")

    ds.status = "running"
    ds.updated_at = _now()
    session.commit()

    if ds.category == "spot":
        if ds.source == "demo":
            market_id = str(ds.params.get("market_id") or "spot:demo:DEMO")
            base_price_raw = ds.params.get("base_price", 1.0)
            base_price = Decimal(str(base_price_raw))

        elif ds.source == "freqtrade":
            from pathlib import Path

            market_id = str(ds.params.get("market_id") or "")
            feather_path_str = ds.params.get("feather_path")

            if not market_id or not feather_path_str:
                raise ValueError(
                    "freqtrade spot dataset requires params.market_id and params.feather_path"
                )

            feather_path = Path(feather_path_str)
            if not feather_path.exists():
                data_dir = get_settings().data_dir
                if data_dir:
                    feather_path = Path(data_dir) / feather_path_str
            if not feather_path.exists():
                raise ValueError(f"Feather file not found: {feather_path}")

            for ev in generate_freqtrade_ohlcv_events(
                dataset_id=dataset_id,
                market_id=market_id,
                feather_path=feather_path,
                start=ds.start,
                end=ds.end,
            ):
                _insert_dataset_event(session, ev=ev)

            ds.status = "ready"
            ds.error = None
            ds.updated_at = _now()
            session.commit()
            return

        else:
            raise ValueError(f"Unsupported spot dataset source={ds.source}")

        params = DemoSpotParams(market_id=market_id, base_price=base_price)
        for ev in generate_demo_spot_events(
            dataset_id=dataset_id,
            start=ds.start,
            end=ds.end,
            params=params,
        ):
            _insert_dataset_event(session, ev=ev)

    elif ds.category == "sentiment":
        if ds.source == "demo":
            market_id = str(ds.params.get("market_id") or "spot:demo:DEMO")
            for ev in generate_demo_sentiment_events(
                dataset_id=dataset_id,
                start=ds.start,
                end=ds.end,
                market_id=market_id,
            ):
                _insert_dataset_event(session, ev=ev)
        elif ds.source == "empty":
            # Valid MVP case: empty sentiment dataset (still produces a dataset_id).
            pass
        elif ds.source == "tweets":
            from pathlib import Path

            tweets_dir_str = ds.params.get("tweets_dir")
            if not tweets_dir_str:
                raise ValueError("tweets sentiment dataset requires params.tweets_dir")

            tweets_dir = Path(tweets_dir_str)
            if not tweets_dir.is_dir():
                data_dir = get_settings().data_dir
                if data_dir:
                    tweets_dir = Path(data_dir) / tweets_dir_str
            if not tweets_dir.is_dir():
                raise ValueError(f"tweets_dir not found: {tweets_dir}")

            for ev in generate_tweet_sentiment_events(
                dataset_id=dataset_id,
                tweets_dir=tweets_dir,
                start=ds.start,
                end=ds.end,
            ):
                _insert_dataset_event(session, ev=ev)
        else:
            raise ValueError(f"Unsupported sentiment dataset source={ds.source}")

    else:
        raise ValueError(f"Unknown dataset.category={ds.category}")

    ds.status = "ready"
    ds.error = None
    ds.updated_at = _now()
    session.commit()
