from __future__ import annotations

import json as json_lib
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import httpx
import pytest

from v4t.db.models import LlmModelRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.settings import get_settings


def test_all_methods_check_budget(db_session: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("V4T_LLM_MAX_SUBMISSION_REPORT_CALLS_PER_SUBMISSION", "0")
    monkeypatch.setenv("V4T_LLM_MAX_WINDOW_BREAKDOWN_CALLS_PER_SUBMISSION", "0")
    get_settings.cache_clear()

    gateway = LlmGateway()
    observed_at = datetime.now(UTC)
    submission_id = uuid4()

    _, report, is_fallback = gateway.call_submission_report(
        db_session,
        submission_id=submission_id,
        observed_at=observed_at,
        model_key="stub",
        system_prompt="test",
        user_prompt="test",
        fallback_report={"summary": "fallback"},
    )

    assert is_fallback is True
    assert report == {"summary": "fallback"}

    _, breakdown, is_fallback = gateway.call_window_breakdown(
        db_session,
        submission_id=submission_id,
        window_code="test",
        observed_at=observed_at,
        model_key="stub",
        system_prompt="test",
        user_prompt="test",
        fallback_breakdown={"analysis": "fallback"},
    )

    assert is_fallback is True
    assert breakdown == {"analysis": "fallback"}


def test_all_methods_support_parse_error_retry(
    db_session: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    model_key = "test-model"
    db_session.add(
        LlmModelRow(
            model_key=model_key,
            label="Test model",
            api_base_url=None,
            api_key=None,
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    prompts = {
        "decision": "decision prompt",
        "summary": "summary prompt",
        "submission_report": "submission report prompt",
        "window_breakdown": "window breakdown prompt",
        "sentiment_item_summary": "sentiment prompt",
    }
    prompt_history: dict[str, list[str]] = {purpose: [] for purpose in prompts}
    attempt_counts = {purpose: 0 for purpose in prompts}

    valid_submission_report = {
        "Score": 75,
        "Style": "Momentum",
        "Overview": "Solid follow-through.",
        "Strengths": ["Captures trend", "Defends gains"],
        "Weaknesses": ["Can lag reversals", "Overstays chop"],
        "Recommendations": ["Tighten exits", "Fade weaker setups"],
        "Roast": "At least it finally read the room.",
    }
    valid_window_breakdown = {
        "window_story": (
            "The strategy stayed aligned with the prevailing move for most of the window, "
            "adding risk when momentum confirmed and reducing exposure when price action lost "
            "follow-through near the close."
        ),
        "what_worked": ["Held winners", "Respected momentum", "Avoided overtrading"],
        "what_didnt_work": ["Trimmed late", "Reacted slowly", "Missed early fade"],
        "improvement_areas": ["Exit faster", "Reduce lag", "Size down in chop"],
        "key_takeaway": "The setup works best when momentum is clean and persistent.",
    }

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            del exc_type, exc, tb
            return False

        def post(
            self,
            url: Any,
            headers: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
        ) -> FakeResponse:
            del url, headers
            req_json = json or {}
            messages_any = req_json.get("messages")
            assert isinstance(messages_any, list)
            messages = cast(list[dict[str, Any]], messages_any)
            assert len(messages) >= 2
            message = messages[1]
            user_prompt = message.get("content")
            assert isinstance(user_prompt, str)

            for purpose, original_prompt in prompts.items():
                if not user_prompt.startswith(original_prompt):
                    continue

                prompt_history[purpose].append(user_prompt)
                attempt_counts[purpose] += 1
                attempt = attempt_counts[purpose]

                if purpose in {"summary", "sentiment_item_summary"}:
                    if attempt == 1:
                        return FakeResponse({"choices": []})

                    content = (
                        "summary retry success"
                        if purpose == "summary"
                        else "sentiment retry success"
                    )
                    return FakeResponse({"choices": [{"message": {"content": content}}]})

                if attempt == 1:
                    return FakeResponse(
                        {"choices": [{"message": {"content": '{"schema_version":2'}}]}
                    )

                if purpose == "decision":
                    content = json_lib.dumps(
                        {
                            "schema_version": 2,
                            "target": 0.25,
                            "mode": "spot",
                            "leverage": 1,
                            "confidence": 0.6,
                            "key_signals": ["ok"],
                            "rationale": "ok",
                        }
                    )
                elif purpose == "submission_report":
                    content = json_lib.dumps(valid_submission_report)
                else:
                    content = json_lib.dumps(valid_window_breakdown)

                return FakeResponse({"choices": [{"message": {"content": content}}]})

            raise AssertionError(f"Unexpected user prompt: {user_prompt}")

    def fake_client_factory(*args: Any, **kwargs: Any) -> FakeClient:
        del args, kwargs
        return FakeClient()

    monkeypatch.setattr(httpx, "Client", fake_client_factory)

    gateway = LlmGateway()

    decision_result = gateway.call_decision(
        db_session,
        run_id=uuid4(),
        observed_at=observed_at,
        model_key=model_key,
        system_prompt="system",
        user_prompt=prompts["decision"],
        stub_features=StubDecisionFeatures(market_id="btc", closes=["1", "2"]),
    )
    summary_call_id, summary_text = gateway.call_summary(
        db_session,
        run_id=uuid4(),
        observed_at=observed_at,
        model_key=model_key,
        system_prompt="system",
        user_prompt=prompts["summary"],
    )
    report_call_id, report, report_fallback = gateway.call_submission_report(
        db_session,
        submission_id=uuid4(),
        observed_at=observed_at,
        model_key=model_key,
        system_prompt="system",
        user_prompt=prompts["submission_report"],
        fallback_report={"fallback": True},
    )
    breakdown_call_id, breakdown, breakdown_fallback = gateway.call_window_breakdown(
        db_session,
        submission_id=uuid4(),
        window_code="window-a",
        observed_at=observed_at,
        model_key=model_key,
        system_prompt="system",
        user_prompt=prompts["window_breakdown"],
        fallback_breakdown={"fallback": True},
    )
    sentiment_call_id, sentiment_text = gateway.call_sentiment_item_summary(
        db_session,
        dataset_id=uuid4(),
        observed_at=observed_at,
        model_key=model_key,
        item_text=prompts["sentiment_item_summary"],
    )

    assert decision_result.error is None
    assert str(decision_result.decision.target) == "0.25"
    assert summary_call_id is not None
    assert summary_text == "summary retry success"
    assert report_call_id is not None
    assert report_fallback is False
    assert report == valid_submission_report
    assert breakdown_call_id is not None
    assert breakdown_fallback is False
    assert breakdown == valid_window_breakdown
    assert sentiment_call_id is not None
    assert sentiment_text == "sentiment retry success"

    for purpose, original_prompt in prompts.items():
        history = prompt_history[purpose]
        assert len(history) == 2
        assert history[0] == original_prompt
        assert history[1].startswith(original_prompt)
        assert history[1] != original_prompt
        assert "Your previous output was invalid." in history[1]


def test_call_decision_circuit_breaker(db_session: Any) -> None:
    from unittest.mock import patch

    gateway = LlmGateway()
    run_id = uuid4()

    # Mock to return valid config and allow model
    with patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")):
        with patch.object(gateway, "_model_allowed", return_value=True):
            with patch("v4t.llm.gateway.post_json_request", side_effect=Exception("LLM error")):
                # First 5 calls should fail and track failures
                for _ in range(5):
                    result = gateway.call_decision(
                        db_session,
                        run_id=run_id,
                        observed_at=datetime.now(UTC),
                        model_key="openai/gpt-4o-mini",
                        system_prompt="test",
                        user_prompt="test",
                        stub_features=StubDecisionFeatures(market_id="btc", closes=["100"]),
                    )
                    assert result.error is not None
                    assert result.decision.target == 0.0

                # 6th call should return immediately with circuit_breaker_open
                result = gateway.call_decision(
                    db_session,
                    run_id=run_id,
                    observed_at=datetime.now(UTC),
                    model_key="openai/gpt-4o-mini",
                    system_prompt="test",
                    user_prompt="test",
                    stub_features=StubDecisionFeatures(market_id="btc", closes=["100"]),
                )
                assert result.error == "circuit_breaker_open"
                assert result.decision.target == 0.0
