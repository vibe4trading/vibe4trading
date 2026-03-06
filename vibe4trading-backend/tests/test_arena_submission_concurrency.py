from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import v4t.arena.runner as arena_runner
from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, DatasetRow
from v4t.settings import get_settings


def _seed_env_datasets(session: Session, *, market_id: str) -> list[str]:
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    dataset_ids: list[str] = []
    for index in range(10):
        start = base + timedelta(hours=index * 12)
        end = start + timedelta(hours=12)
        dataset = DatasetRow(
            category="spot",
            source="demo",
            start=start,
            end=end,
            params={"market_id": market_id},
            status="ready",
            error=None,
            created_at=base,
            updated_at=base,
        )
        session.add(dataset)
        session.flush()
        dataset_ids.append(str(dataset.dataset_id))
    session.commit()
    return dataset_ids


def _create_submission(session: Session, *, market_id: str) -> ArenaSubmissionRow:
    now_ts = datetime.now(UTC)
    submission = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-datasets-v1",
        market_id=market_id,
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
    session.add(submission)
    session.commit()
    return submission


def test_arena_submission_uses_parallel_window_slots(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_ids = _seed_env_datasets(db_session, market_id="spot:demo:DEMO")

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(dataset_ids))
    monkeypatch.setenv("V4T_LLM_MAX_CONCURRENT_REQUESTS", "3")
    get_settings.cache_clear()

    submission = _create_submission(db_session, market_id="spot:demo:DEMO")

    lock = threading.Lock()
    release = threading.Event()
    state = {"active": 0, "peak": 0, "started": 0}

    def _fake_execute_submission_window(*, run_id: UUID) -> None:
        del run_id
        with lock:
            state["active"] += 1
            state["started"] += 1
            state["peak"] = max(state["peak"], state["active"])
            if state["started"] >= 3:
                release.set()
        release.wait(timeout=2.0)
        time.sleep(0.02)
        with lock:
            state["active"] -= 1

    def _fake_get_run_return_pct(session: Session, *, run_id: UUID) -> Decimal | None:
        del session, run_id
        return Decimal("1.0")

    def _fake_generate_submission_report(session: Session, submission_id: UUID) -> None:
        del session, submission_id

    monkeypatch.setattr(arena_runner, "_execute_submission_window", _fake_execute_submission_window)
    monkeypatch.setattr(arena_runner, "_get_run_return_pct", _fake_get_run_return_pct)
    monkeypatch.setattr(
        arena_runner, "generate_submission_report", _fake_generate_submission_report
    )

    arena_runner.execute_arena_submission(db_session, submission_id=submission.submission_id)

    db_session.refresh(submission)
    assert submission.status == "finished"
    assert submission.windows_total == 10
    assert submission.windows_completed == 10
    assert state["peak"] == 3

    runs = list(
        db_session.execute(
            select(ArenaSubmissionRunRow)
            .where(ArenaSubmissionRunRow.submission_id == submission.submission_id)
            .order_by(ArenaSubmissionRunRow.scenario_index)
        )
        .scalars()
        .all()
    )
    assert len(runs) == 10
    assert all(run.status == "finished" for run in runs)
    assert all(run.return_pct == Decimal("1.0") for run in runs)
