from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy.orm import Session

from v4t.db.models import LlmModelRow
from v4t.llm.gateway import LlmGateway
from v4t.settings import get_settings


def test_submission_report_schema_validation_failure(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="test-model",
            label="Test",
            api_base_url=None,
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "choices": [{"message": {"content": json.dumps({"invalid": "schema"})}}],
                "usage": {"total_tokens": 100},
            }

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def post(self, url: str, headers: Any = None, json: Any = None) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    fallback = {
        "generation_mode": "fallback",
        "overall_score": 0,
        "archetype": "Unknown",
        "overview": "",
        "key_metrics": {},
        "windows": [],
    }

    call_id, result, used_fallback = LlmGateway().call_submission_report(
        db_session,
        submission_id=uuid4(),
        observed_at=observed_at,
        model_key="test-model",
        system_prompt="test",
        user_prompt="test",
        fallback_report=fallback,
    )

    assert used_fallback is True
    assert result == fallback

    from v4t.db.models import LlmCallRow

    call = db_session.query(LlmCallRow).filter_by(call_id=call_id).one()
    assert call.error is not None
    assert "schema_validation_failed" in call.error


def test_submission_report_schema_validation_success(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="test-model",
            label="Test",
            api_base_url=None,
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    valid_report = {
        "Score": 75,
        "Style": "Momentum",
        "Overview": "Test overview",
        "Strengths": ["Strong trend following", "Good risk management"],
        "Weaknesses": ["Poor in sideways markets", "High drawdowns"],
        "Recommendations": ["Add volatility filters", "Reduce position sizes"],
        "Roast": "Your strategy is basic but functional",
    }

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "choices": [{"message": {"content": json.dumps(valid_report)}}],
                "usage": {"total_tokens": 100},
            }

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def post(self, url: str, headers: Any = None, json: Any = None) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)

    call_id, result, used_fallback = LlmGateway().call_submission_report(
        db_session,
        submission_id=uuid4(),
        observed_at=observed_at,
        model_key="test-model",
        system_prompt="test",
        user_prompt="test",
        fallback_report={},
    )

    assert used_fallback is False
    assert result == valid_report

    from v4t.db.models import LlmCallRow

    call = db_session.query(LlmCallRow).filter_by(call_id=call_id).one()
    assert call.error is None
