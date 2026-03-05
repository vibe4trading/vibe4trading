from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from v4t.arena.runner import execute_arena_submission
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, DatasetRow
from v4t.settings import get_settings
from v4t.utils.datetime import as_utc


def test_arena_submission_smoke(db_session, monkeypatch):
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    ids: list[str] = []
    for i in range(10):
        start = base + timedelta(hours=i * 12)
        end = start + timedelta(hours=12)
        ds = DatasetRow(
            category="spot",
            source="demo",
            start=start,
            end=end,
            params={"market_id": "spot:demo:DEMO"},
            status="ready",
            error=None,
            created_at=base,
            updated_at=base,
        )
        db_session.add(ds)
        db_session.flush()
        ids.append(str(ds.dataset_id))
    db_session.commit()

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(ids))
    monkeypatch.setenv("V4T_CELERY_ALWAYS_EAGER", "1")
    get_settings.cache_clear()

    now = datetime.now(UTC)
    sub = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-datasets-v1",
        market_id="spot:demo:DEMO",
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

    execute_arena_submission(db_session, submission_id=sub.submission_id)

    db_session.refresh(sub)
    assert sub.status == "finished"
    assert sub.windows_total == 10
    assert sub.windows_completed == 10
    assert sub.total_return_pct is not None
    assert sub.avg_return_pct is not None

    runs = list(
        db_session.execute(
            select(ArenaSubmissionRunRow).where(
                ArenaSubmissionRunRow.submission_id == sub.submission_id
            )
        )
        .scalars()
        .all()
    )
    assert len(runs) == 10
    assert all(r.status == "finished" for r in runs)
    assert all(r.return_pct is not None for r in runs)


def test_arena_submission_smoke_single_dataset(db_session, monkeypatch):
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    ds = DatasetRow(
        category="spot",
        source="demo",
        start=base,
        end=base + timedelta(hours=72),
        params={"market_id": "spot:demo:DEMO"},
        status="pending",
        error=None,
        created_at=base,
        updated_at=base,
    )
    db_session.add(ds)
    db_session.flush()
    db_session.commit()

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", str(ds.dataset_id))
    get_settings.cache_clear()

    now_ts = datetime.now(UTC)
    sub = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-regimes-v1",
        market_id="spot:demo:DEMO",
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
        created_at=now_ts,
        updated_at=now_ts,
    )
    db_session.add(sub)
    db_session.commit()

    execute_arena_submission(db_session, submission_id=sub.submission_id)

    db_session.refresh(sub)
    assert sub.status == "finished"
    assert sub.windows_total == 10
    assert sub.windows_completed == 10
    assert sub.total_return_pct is not None
    assert sub.avg_return_pct is not None

    runs = list(
        db_session.execute(
            select(ArenaSubmissionRunRow).where(
                ArenaSubmissionRunRow.submission_id == sub.submission_id
            )
        )
        .scalars()
        .all()
    )
    assert len(runs) == 10
    assert all(r.status == "finished" for r in runs)
    assert all(r.return_pct is not None for r in runs)


def test_arena_submission_smoke_single_dataset_fullrange(db_session, monkeypatch):
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    ds = DatasetRow(
        category="spot",
        source="demo",
        start=base,
        end=base + timedelta(days=7),
        params={"market_id": "spot:demo:DEMO"},
        status="ready",
        error=None,
        created_at=base,
        updated_at=base,
    )
    db_session.add(ds)
    db_session.flush()
    db_session.commit()

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", str(ds.dataset_id))
    get_settings.cache_clear()

    now_ts = datetime.now(UTC)
    sub = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-fullrange-v1",
        market_id="spot:demo:DEMO",
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
        created_at=now_ts,
        updated_at=now_ts,
    )
    db_session.add(sub)
    db_session.commit()

    execute_arena_submission(db_session, submission_id=sub.submission_id)

    db_session.refresh(sub)
    assert sub.status == "finished"
    assert sub.windows_total == 1
    assert sub.windows_completed == 1

    runs = list(
        db_session.execute(
            select(ArenaSubmissionRunRow).where(
                ArenaSubmissionRunRow.submission_id == sub.submission_id
            )
        )
        .scalars()
        .all()
    )
    assert len(runs) == 1
    assert as_utc(runs[0].window_start) == base
    assert as_utc(runs[0].window_end) == base + timedelta(days=7)
