from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from v4t.db.models import ArenaSubmissionRow, DatasetRow, JobRow
from v4t.jobs.types import JOB_TYPE_ARENA_EXECUTE_SUBMISSION
from v4t.settings import get_settings


def test_scenario_sets_endpoint(client) -> None:  # noqa: ANN001
    res = client.get("/arena/scenario_sets")
    assert res.status_code == 200
    sets = res.json()
    assert len(sets) >= 1
    assert sets[0]["key"] == "default-v1"
    assert len(sets[0]["windows"]) == 10


def test_create_submission_rejects_unknown_scenario_set(client) -> None:  # noqa: ANN001
    res = client.post(
        "/arena/submissions",
        json={
            "scenario_set_key": "nope",
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 500
    assert res.json()["detail"] == "Arena datasets not configured"


def test_create_submission_enqueues_job(db_session, client, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", lambda *, job: "task-arena")

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
    get_settings.cache_clear()

    res = client.post(
        "/arena/submissions",
        json={
            "scenario_set_key": "default-v1",
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "prompt_text": "Analyze market data.",
            "visibility": "public",
        },
    )
    assert res.status_code == 200
    submission_id = UUID(res.json()["submission_id"])

    row = db_session.get(ArenaSubmissionRow, submission_id)
    assert row is not None
    assert row.status == "pending"
    assert row.windows_total == 10
    assert row.windows_completed == 0

    jobs = list(
        db_session.execute(
            select(JobRow).where(JobRow.job_type == JOB_TYPE_ARENA_EXECUTE_SUBMISSION)
        )
        .scalars()
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].payload["submission_id"] == str(submission_id)
    assert jobs[0].payload["celery_task_id"] == "task-arena"


def test_leaderboard_includes_private_and_caps_top_100(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    rows: list[ArenaSubmissionRow] = []
    for i in range(101):
        rows.append(
            ArenaSubmissionRow(
                owner_user_id=None,
                scenario_set_key="default-v1",
                market_id="spot:demo:DEMO",
                model_key="stub",
                prompt_template_id=None,
                prompt_vars={},
                visibility="private" if i == 100 else "public",
                status="finished",
                windows_total=10,
                windows_completed=10,
                total_return_pct=Decimal(i),
                avg_return_pct=Decimal(i),
                error=None,
                started_at=None,
                ended_at=None,
                created_at=now,
                updated_at=now,
            )
        )
    db_session.add_all(rows)
    db_session.commit()

    res = client.get("/arena/leaderboards")
    assert res.status_code == 200
    lb = res.json()
    assert len(lb) == 100
    assert lb[0]["submission_id"] == str(rows[100].submission_id)
