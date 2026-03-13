from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.arena.runner import ALL_MARKETS_SENTINEL, execute_arena_submission
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, DatasetRow
from v4t.settings import get_settings


def test_arena_submission_benchmark_all_markets_creates_100_runs(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    ids: list[str] = []
    for market_idx in range(10):
        market_id = f"spot:demo:TOKEN{market_idx}"
        for window_idx in range(10):
            start = base + timedelta(hours=window_idx * 2)
            end = start + timedelta(hours=2)
            ds = DatasetRow(
                category="spot",
                source="demo",
                start=start,
                end=end,
                params={"market_id": market_id, "base_price": 10.0 + market_idx},
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
    get_settings.cache_clear()

    now_ts = datetime.now(UTC)
    sub = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="crypto-benchmark-v1",
        market_id=ALL_MARKETS_SENTINEL,
        model_key="stub",
        prompt_template_id=None,
        prompt_vars={
            "prompt_text": "Trade the benchmark.",
            "system_prompt": None,
        },
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
    assert sub.windows_total == 100
    assert sub.windows_completed == 100

    runs = cast(
        list[ArenaSubmissionRunRow],
        db_session.execute(
            select(ArenaSubmissionRunRow).where(
                ArenaSubmissionRunRow.submission_id == sub.submission_id
            )
        )
        .scalars()
        .all(),
    )
    assert len(runs) == 100
    assert all(r.status == "finished" for r in runs)
