from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from v4t.db.models import DatasetRow, EventRow
from v4t.ingest.dataset_import import import_dataset


def test_import_dataset_empty_sentiment_is_allowed(db_session) -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    end = now.replace(minute=0, second=0, microsecond=0)

    ds = DatasetRow(
        category="sentiment",
        source="empty",
        start=start,
        end=end,
        params={},
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ds)
    db_session.commit()

    import_dataset(db_session, dataset_id=ds.dataset_id)
    db_session.refresh(ds)
    assert ds.status == "ready"

    cnt = db_session.execute(
        select(func.count()).select_from(EventRow).where(EventRow.dataset_id == ds.dataset_id)
    ).scalar_one()
    assert cnt == 0


def test_import_dataset_tweets_generates_prompt_usable_summaries(db_session, tmp_path) -> None:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(hours=2)
    end = now

    tweets_path = tmp_path / (
        "handle_"
        + start.strftime("%Y-%m-%d_%H-%M-%S_UTC_to_")
        + end.strftime("%Y-%m-%d_%H-%M-%S_UTC.json")
    )
    tweets_path.write_text(
        json.dumps(
            [
                {
                    "id": "tweet-1",
                    "handle": "TraderOne",
                    "created_at": start.strftime("%a, %d %b %Y %H:%M:%S +0000"),
                    "text": "BTC looks strong after reclaiming the key level.",
                    "tweet_url": "https://example.invalid/tweet-1",
                    "user": {"name": "Trader One", "followers_count": 42},
                }
            ]
        )
    )

    ds = DatasetRow(
        category="sentiment",
        source="tweets",
        start=start,
        end=end,
        params={"tweets_dir": str(tmp_path)},
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(ds)
    db_session.commit()

    import_dataset(db_session, dataset_id=ds.dataset_id)
    db_session.refresh(ds)
    assert ds.status == "ready"

    item_cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.dataset_id == ds.dataset_id,
            EventRow.event_type == "sentiment.item",
        )
    ).scalar_one()
    summary_cnt = db_session.execute(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.dataset_id == ds.dataset_id,
            EventRow.event_type == "sentiment.item_summary",
        )
    ).scalar_one()
    assert item_cnt == 1
    assert summary_cnt == 1
