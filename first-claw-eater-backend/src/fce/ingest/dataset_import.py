from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from fce.contracts.events import EventEnvelopeV1, make_event_v1
from fce.contracts.numbers import decimal_to_str
from fce.contracts.payloads import (
    SentimentItemKind,
    SentimentItemPayloadV1,
    SentimentItemSummaryPayloadV1,
)
from fce.db.event_store import append_event
from fce.db.models import DatasetRow
from fce.ingest.demo import (
    DemoSpotParams,
    generate_demo_sentiment_events,
    generate_demo_spot_events,
)
from fce.ingest.dexscreener import resolve_spot_market
from fce.ingest.rss import fetch_rss_items
from fce.llm.gateway import LlmGateway
from fce.settings import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


def _insert_dataset_event(session: Session, *, ev: EventEnvelopeV1) -> None:
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

        elif ds.source == "dexscreener":
            # DexScreener does not provide historical backfill. For MVP we resolve the
            # current price and use it as a seed for a deterministic synthetic dataset.
            market_id = str(ds.params.get("market_id") or "")
            base_price_raw = ds.params.get("base_price")

            if not market_id or base_price_raw is None:
                chain_id = ds.params.get("chain_id")
                pair_id = ds.params.get("pair_id") or ds.params.get("pair_address")
                if not chain_id or not pair_id:
                    raise ValueError(
                        "dexscreener spot dataset requires params.chain_id + params.pair_id (or market_id+base_price)"
                    )

                resolved = resolve_spot_market(chain_id=str(chain_id), pair_id=str(pair_id))
                market_id = market_id or resolved.market_id
                base_price = resolved.base_price

                # Persist resolved values so retries are deterministic.
                ds.params = {
                    **(ds.params or {}),
                    "market_id": market_id,
                    "base_price": decimal_to_str(base_price),
                }
                ds.updated_at = _now()
                session.commit()
            else:
                base_price = Decimal(str(base_price_raw))

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
        elif ds.source == "rss":
            settings = get_settings()

            feeds_raw = ds.params.get("feeds")
            if isinstance(feeds_raw, list):
                feeds = [str(x) for x in feeds_raw if str(x).strip()]
            elif isinstance(feeds_raw, str) and feeds_raw.strip():
                feeds = [s.strip() for s in feeds_raw.split(",") if s.strip()]
            elif settings.sentiment_rss_feeds:
                feeds = [s.strip() for s in settings.sentiment_rss_feeds.split(",") if s.strip()]
            else:
                feeds = []

            max_items = int(ds.params.get("max_items", 50))
            items, errors = fetch_rss_items(
                feeds=feeds, start=ds.start, end=ds.end, max_items=max_items
            )
            if not items and errors:
                raise ValueError("RSS fetch failed: " + "; ".join(errors[:3]))

            model_key = str(ds.params.get("model_key") or settings.llm_model or "stub")
            gateway = LlmGateway()

            for it in items:
                text = (it.text or "").strip()
                if len(text) > 2000:
                    text = text[:2000].rstrip() + "..."

                item_payload = SentimentItemPayloadV1(
                    source="rss",
                    external_id=it.external_id,
                    item_time=it.item_time,
                    item_kind=SentimentItemKind.news,
                    text=text,
                    url=it.url,
                ).model_dump(mode="json")
                _insert_dataset_event(
                    session,
                    ev=make_event_v1(
                        event_type="sentiment.item",
                        source="ingest.rss",
                        observed_at=it.item_time,
                        event_time=it.item_time,
                        dedupe_key=f"rss:{it.external_id}",
                        dataset_id=dataset_id,
                        payload=item_payload,
                        raw_payload={"feed_url": it.feed_url, "title": it.title, "url": it.url},
                    ),
                )

                call_id, summary_text = gateway.call_sentiment_item_summary(
                    session,
                    dataset_id=dataset_id,
                    observed_at=it.item_time,
                    model_key=model_key,
                    item_text=text,
                    item_url=it.url,
                )
                summary_payload = SentimentItemSummaryPayloadV1(
                    source="rss",
                    external_id=it.external_id,
                    item_time=it.item_time,
                    item_kind=SentimentItemKind.news,
                    summary_text=summary_text,
                    tags=["rss"],
                    llm_call_id=call_id,
                ).model_dump(mode="json")
                _insert_dataset_event(
                    session,
                    ev=make_event_v1(
                        event_type="sentiment.item_summary",
                        source="ingest.rss",
                        observed_at=it.item_time,
                        event_time=it.item_time,
                        dedupe_key=f"rss:{it.external_id}",
                        dataset_id=dataset_id,
                        payload=summary_payload,
                    ),
                )
        else:
            raise ValueError(f"Unsupported sentiment dataset source={ds.source}")

    else:
        raise ValueError(f"Unknown dataset.category={ds.category}")

    ds.status = "ready"
    ds.error = None
    ds.updated_at = _now()
    session.commit()
