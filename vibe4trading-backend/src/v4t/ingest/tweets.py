"""Load sentiment events from raw tweet JSON files (X/Twitter posts).

Each JSON file is an array of tweet objects scraped per-handle per-event window.
File naming convention: ``{handle}_{lookback_start}_to_{event_end}.json``

The loader reads all JSON files in a directory that match the dataset's date
range, parses each tweet, and yields ``sentiment.item`` event envelopes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from uuid import UUID

from v4t.contracts.events import EventEnvelope, make_event
from v4t.contracts.payloads import (
    SentimentItemKind,
    SentimentItemPayload,
    SentimentItemSummaryPayload,
)


def _parse_tweet_time(raw: str) -> datetime:
    """Parse Twitter's ``created_at`` format (RFC 2822)."""
    dt = parsedate_to_datetime(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_filename_dates(filename: str) -> tuple[datetime, datetime] | None:
    """Extract (start, end) UTC datetimes from a tweet JSON filename.

    Expected pattern: ``handle_YYYY-MM-DD_HH-MM-SS_UTC_to_YYYY-MM-DD_HH-MM-SS_UTC.json``
    """
    m = re.search(
        r"(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})_UTC_to_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})_UTC\.json$",
        filename,
    )
    if not m:
        return None
    start = datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}:{m.group(3)}:{m.group(4)}+00:00")
    end = datetime.fromisoformat(f"{m.group(5)}T{m.group(6)}:{m.group(7)}:{m.group(8)}+00:00")
    return start, end


def generate_tweet_sentiment_events(
    *,
    dataset_id: UUID,
    tweets_dir: Path,
    start: datetime,
    end: datetime,
) -> Iterator[EventEnvelope]:
    """Yield ``sentiment.item`` events from tweet JSON files.

    Only files whose date range overlaps ``[start, end]`` are loaded.
    Individual tweets are filtered to ``[start, end]`` by ``created_at``.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    for path in sorted(tweets_dir.glob("*.json")):
        if path.name in ("loading_memes_config.json", "meme.json"):
            continue

        file_dates = _parse_filename_dates(path.name)
        if file_dates is not None:
            file_start, file_end = file_dates
            if file_end < start or file_start > end:
                continue

        with open(path) as f:
            tweets = json.load(f)

        if not isinstance(tweets, list):
            continue

        for tweet in tweets:
            created_at_raw = tweet.get("created_at")
            if not created_at_raw:
                continue

            try:
                tweet_time = _parse_tweet_time(created_at_raw)
            except Exception:
                continue

            if tweet_time < start or tweet_time > end:
                continue

            tweet_id = tweet.get("id", "")
            handle = tweet.get("handle", "")
            text = (tweet.get("text") or "").strip()
            if not text:
                continue

            if len(text) > 2000:
                text = text[:2000].rstrip() + "..."

            tweet_url = tweet.get("tweet_url")
            external_id = tweet_id or f"tweet:{handle}:{tweet_time.isoformat()}"

            item_payload = SentimentItemPayload(
                source="tweets",
                external_id=external_id,
                item_time=tweet_time,
                item_kind=SentimentItemKind.x_post,
                text=text,
                url=tweet_url,
            ).model_dump(mode="json")

            user_info = tweet.get("user", {})
            raw_payload = {
                "handle": handle,
                "user_name": user_info.get("name", ""),
                "followers_count": user_info.get("followers_count", 0),
                "favorite_count": tweet.get("favorite_count", 0),
                "retweet_count": tweet.get("retweet_count", 0),
                "reply_count": tweet.get("reply_count", 0),
                "view_count": tweet.get("view_count"),
            }

            yield make_event(
                event_type="sentiment.item",
                source="ingest.tweets",
                observed_at=tweet_time,
                event_time=tweet_time,
                dedupe_key=f"tweet:{external_id}",
                dataset_id=dataset_id,
                payload=item_payload,
                raw_payload=raw_payload,
            )

            tags = ["tweets"]
            if handle:
                tags.append(handle)

            summary_payload = SentimentItemSummaryPayload(
                source="tweets",
                external_id=external_id,
                item_time=tweet_time,
                item_kind=SentimentItemKind.x_post,
                summary_text=text,
                tags=tags,
            ).model_dump(mode="json")

            yield make_event(
                event_type="sentiment.item_summary",
                source="ingest.tweets",
                observed_at=tweet_time,
                event_time=tweet_time,
                dedupe_key=f"tweet:{external_id}",
                dataset_id=dataset_id,
                payload=summary_payload,
                raw_payload=raw_payload,
            )
