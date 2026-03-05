from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from v4t.arena.runner import execute_arena_submission
from v4t.db.models import ArenaSubmissionRow, DatasetRow
from v4t.ingest.dataset_import import import_dataset
from v4t.settings import get_settings


def test_arena_uses_env_dataset_set(db_session):
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    spot_ids: list[str] = []
    spot_uuids = []
    for i in range(10):
        start = base + timedelta(hours=i * 12)
        end = start + timedelta(hours=12)
        ds = DatasetRow(
            category="spot",
            source="demo",
            start=start,
            end=end,
            params={"market_id": "spot:demo:BTC"},
            status="pending",
            error=None,
            created_at=base,
            updated_at=base,
        )
        db_session.add(ds)
        db_session.flush()
        spot_ids.append(str(ds.dataset_id))
        spot_uuids.append(ds.dataset_id)
    db_session.commit()

    for ds_id in spot_uuids:
        import_dataset(db_session, dataset_id=ds_id)

    prev = os.environ.get("V4T_ARENA_DATASET_IDS")
    os.environ["V4T_ARENA_DATASET_IDS"] = ",".join(spot_ids)
    os.environ["V4T_CELERY_ALWAYS_EAGER"] = "1"
    get_settings.cache_clear()

    now = datetime.now(UTC)
    sub = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-datasets-v1",
        market_id="spot:demo:BTC",
        model_key="stub",
        prompt_template_id=None,
        prompt_vars={},
        visibility="public",
        status="pending",
        windows_total=0,
        windows_completed=0,
        total_return_pct=None,
        avg_return_pct=None,
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(sub)
    db_session.commit()

    try:
        execute_arena_submission(db_session, submission_id=sub.submission_id)

        db_session.refresh(sub)
        assert sub.status == "finished"
        assert sub.windows_total == 10
        assert sub.windows_completed == 10
    finally:
        if prev is None:
            os.environ.pop("V4T_ARENA_DATASET_IDS", None)
        else:
            os.environ["V4T_ARENA_DATASET_IDS"] = prev
        os.environ.pop("V4T_CELERY_ALWAYS_EAGER", None)
        get_settings.cache_clear()
