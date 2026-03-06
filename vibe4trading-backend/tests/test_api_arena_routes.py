from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from v4t.db.models import ArenaSubmissionRow, ArenaSubmissionRunRow, DatasetRow, JobRow
from v4t.jobs.types import JOB_TYPE_ARENA_EXECUTE_SUBMISSION
from v4t.settings import get_settings


def test_scenario_sets_endpoint(client) -> None:  # noqa: ANN001
    res = client.get("/arena/scenario_sets")
    assert res.status_code == 200
    sets = res.json()
    assert len(sets) >= 1
    assert sets[0]["key"] == "default-v1"
    assert len(sets[0]["windows"]) == 10


def test_create_submission_rejects_legacy_scenario_set_field(client) -> None:  # noqa: ANN001
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
    assert res.status_code == 422


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


def test_submissions_list_uses_cursor_pagination(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    rows = []
    for i in range(3):
        row = ArenaSubmissionRow(
            owner_user_id=None,
            scenario_set_key="default-v1",
            market_id="spot:demo:DEMO",
            model_key="stub",
            prompt_template_id=None,
            prompt_vars={},
            visibility="public",
            status="finished",
            windows_total=10,
            windows_completed=10,
            total_return_pct=Decimal(i),
            avg_return_pct=Decimal(i),
            error=None,
            started_at=None,
            ended_at=None,
            created_at=now - timedelta(minutes=i),
            updated_at=now - timedelta(minutes=i),
        )
        rows.append(row)
    db_session.add_all(rows)
    db_session.commit()

    first = client.get("/arena/submissions?limit=2")
    assert first.status_code == 200
    first_payload = first.json()
    assert len(first_payload["items"]) == 2
    assert first_payload["has_more"] is True
    assert first_payload["next_cursor"] is not None

    second = client.get(
        "/arena/submissions",
        params={"limit": 2, "cursor": first_payload["next_cursor"]},
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert len(second_payload["items"]) == 1
    assert second_payload["has_more"] is False


def test_submissions_cursor_tiebreaks_same_timestamp(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    first_row = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="default-v1",
        market_id="spot:demo:DEMO",
        model_key="stub",
        prompt_template_id=None,
        prompt_vars={},
        visibility="public",
        status="finished",
        windows_total=10,
        windows_completed=10,
        total_return_pct=Decimal("1"),
        avg_return_pct=Decimal("1"),
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    second_row = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="default-v1",
        market_id="spot:demo:DEMO",
        model_key="stub",
        prompt_template_id=None,
        prompt_vars={},
        visibility="public",
        status="finished",
        windows_total=10,
        windows_completed=10,
        total_return_pct=Decimal("2"),
        avg_return_pct=Decimal("2"),
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([first_row, second_row])
    db_session.commit()

    first = client.get("/arena/submissions?limit=1")
    assert first.status_code == 200
    first_payload = first.json()
    second = client.get(
        "/arena/submissions",
        params={"limit": 1, "cursor": first_payload["next_cursor"]},
    )
    assert second.status_code == 200
    second_payload = second.json()
    returned_ids = {
        first_payload["items"][0]["submission_id"],
        second_payload["items"][0]["submission_id"],
    }
    assert returned_ids == {str(first_row.submission_id), str(second_row.submission_id)}


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


def test_leaderboard_supports_model_filter_and_metrics(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    target = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-fullrange-v1",
        market_id="spot:demo:BTC",
        model_key="stub",
        prompt_template_id=None,
        prompt_vars={},
        visibility="public",
        status="finished",
        windows_total=2,
        windows_completed=2,
        total_return_pct=Decimal("4.50"),
        avg_return_pct=Decimal("2.25"),
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    other = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-fullrange-v1",
        market_id="spot:demo:BTC",
        model_key="other-model",
        prompt_template_id=None,
        prompt_vars={},
        visibility="public",
        status="finished",
        windows_total=1,
        windows_completed=1,
        total_return_pct=Decimal("1.00"),
        avg_return_pct=Decimal("1.00"),
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([target, other])
    db_session.flush()

    db_session.add_all(
        [
            ArenaSubmissionRunRow(
                submission_id=target.submission_id,
                scenario_index=0,
                run_id=UUID("00000000-0000-0000-0000-000000000101"),
                window_start=now,
                window_end=now,
                status="finished",
                return_pct=Decimal("10.0"),
                error=None,
                started_at=None,
                ended_at=None,
                created_at=now,
                updated_at=now,
            ),
            ArenaSubmissionRunRow(
                submission_id=target.submission_id,
                scenario_index=1,
                run_id=UUID("00000000-0000-0000-0000-000000000102"),
                window_start=now,
                window_end=now,
                status="finished",
                return_pct=Decimal("-5.0"),
                error=None,
                started_at=None,
                ended_at=None,
                created_at=now,
                updated_at=now,
            ),
            ArenaSubmissionRunRow(
                submission_id=other.submission_id,
                scenario_index=0,
                run_id=UUID("00000000-0000-0000-0000-000000000201"),
                window_start=now,
                window_end=now,
                status="finished",
                return_pct=Decimal("1.0"),
                error=None,
                started_at=None,
                ended_at=None,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

    res = client.get("/arena/leaderboards?market_id=spot:demo:BTC&model_key=stub")
    assert res.status_code == 200
    payload = res.json()
    assert len(payload) == 1
    entry = payload[0]
    assert entry["submission_id"] == str(target.submission_id)
    assert entry["model_key"] == "stub"
    assert entry["per_window_returns"] == [10.0, -5.0]
    assert entry["win_rate_pct"] == 50.0
    assert entry["profit_factor"] == 2.0
    assert entry["max_drawdown_pct"] == 5.0
    assert entry["sharpe_ratio"] is not None
    assert entry["num_trades"] == 0


def test_submission_detail_includes_report_json(db_session, client) -> None:  # noqa: ANN001
    now = datetime.now(UTC)
    row = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-fullrange-v1",
        market_id="spot:demo:BTC",
        model_key="stub",
        prompt_template_id=None,
        prompt_vars={},
        visibility="public",
        status="finished",
        windows_total=1,
        windows_completed=1,
        total_return_pct=Decimal("4.50"),
        avg_return_pct=Decimal("4.50"),
        report_call_id=None,
        report_json={
            "schema_version": 1,
            "generation_mode": "fallback",
            "overall_score": 72,
            "archetype": "Adaptive Swing Trader",
            "overview": "Finished one window with positive return.",
            "strengths": ["Positive total return.", "Limited drawdown.", "Finished all windows."],
            "weaknesses": ["Only one window completed.", "Low sample size.", "Fallback narrative."],
            "recommendations": [
                "Run more windows.",
                "Compare against stronger baselines.",
                "Inspect the replay.",
            ],
            "key_metrics": {
                "total_return_pct": 4.5,
                "avg_window_return_pct": 4.5,
                "win_rate_pct": 100.0,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "profit_factor": 99.99,
                "num_trades": 0,
                "decision_count": 0,
                "acceptance_rate_pct": None,
                "avg_confidence": None,
                "avg_target_exposure_pct": None,
                "window_return_dispersion_pct": 0.0,
            },
            "best_window": {
                "window_code": "W01",
                "label": "Full Range",
                "return_pct": 4.5,
                "reason": "Best-performing slice.",
            },
            "worst_window": {
                "window_code": "W01",
                "label": "Full Range",
                "return_pct": 4.5,
                "reason": "Weakest slice by default.",
            },
            "windows": [],
        },
        error=None,
        started_at=None,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )
    db_session.add(row)
    db_session.commit()

    res = client.get(f"/arena/submissions/{row.submission_id}")
    assert res.status_code == 200
    payload = res.json()
    assert payload["report_json"] is not None
    assert payload["report_json"]["overall_score"] == 72
    assert payload["report_json"]["archetype"] == "Adaptive Swing Trader"
