from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from v4t.arena.reporting import generate_submission_report
from v4t.arena.runner import execute_arena_submission
from v4t.db.models import ArenaSubmissionRow, DatasetRow
from v4t.settings import get_settings


def test_generate_submission_report_with_window_breakdowns(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integration test: generate_submission_report() populates window breakdowns."""
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

    dataset_ids: list[str] = []
    for i in range(10):
        start = base + timedelta(hours=i * 12)
        end = start + timedelta(hours=12)
        ds = DatasetRow(
            category="spot",
            source="demo",
            start=start,
            end=end,
            params={"market_id": "spot:demo:TEST"},
            status="ready",
            error=None,
            created_at=base,
            updated_at=base,
        )
        db_session.add(ds)
        db_session.flush()
        dataset_ids.append(str(ds.dataset_id))
    db_session.commit()

    monkeypatch.setenv("V4T_ARENA_DATASET_IDS", ",".join(dataset_ids))
    get_settings.cache_clear()

    submission = ArenaSubmissionRow(
        owner_user_id=None,
        scenario_set_key="env-datasets-v1",
        market_id="spot:demo:TEST",
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
        created_at=base,
        updated_at=base,
    )
    db_session.add(submission)
    db_session.commit()

    mock_breakdown = {
        "window_story": "This window showed strong momentum with 3 trades executed. The strategy captured upward movement effectively while managing risk through disciplined position sizing.",
        "what_worked": [
            "Timely entry on momentum signals",
            "Consistent position sizing",
            "Risk management discipline",
        ],
        "what_didnt_work": [
            "Missed early reversal signals",
            "Could have scaled positions better",
        ],
        "improvement_areas": [
            "Add reversal detection logic",
            "Implement dynamic position scaling",
            "Improve exit timing",
        ],
        "key_takeaway": "Strong execution with room for optimization in exit strategy.",
    }

    with patch("v4t.llm.gateway.call_with_retry") as mock_retry:
        mock_retry.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(mock_breakdown),
                        }
                    }
                ]
            },
        )

        execute_arena_submission(db_session, submission_id=submission.submission_id)
        report = generate_submission_report(db_session, submission_id=submission.submission_id)

    assert report is not None
    assert len(report.windows) == 10

    for window in report.windows:
        assert window.breakdown is not None
        assert window.breakdown.window_story is not None
        assert len(window.breakdown.window_story) > 0
        assert len(window.breakdown.what_worked) >= 2
        assert len(window.breakdown.what_didnt_work) >= 1
        assert len(window.breakdown.improvement_areas) >= 2
        assert window.breakdown.key_takeaway is not None
        assert len(window.breakdown.key_takeaway) > 0
