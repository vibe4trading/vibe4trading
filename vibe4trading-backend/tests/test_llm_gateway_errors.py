from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import uuid4

import httpx

from v4t.contracts.payloads import LlmDecisionOutput
from v4t.db.models import LlmCallRow, LlmModelRow
from v4t.llm.concurrency import QueueFullError
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.settings import get_settings


def test_llm_gateway_returns_fallback_on_transport_error(db_session: Any, monkeypatch: Any) -> None:
    # Force the gateway into non-stub mode.
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "0.1")
    get_settings.cache_clear()

    class BoomClient:
        def __init__(self, *args: Any, **kwargs: Any):
            del args, kwargs

        def __enter__(self) -> Any:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            del exc_type, exc, tb
            return False

        def post(self, url: Any, headers: Any = None, json: Any = None) -> NoReturn:
            del headers, json
            raise httpx.ConnectError("boom", request=httpx.Request("POST", str(url)))

    monkeypatch.setattr(httpx, "Client", BoomClient)

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url=None,
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    gateway = LlmGateway()
    run_id = uuid4()

    result = gateway.call_decision(
        db_session,
        run_id=run_id,
        observed_at=observed_at,
        model_key="gpt-4o-mini",
        system_prompt="s",
        user_prompt="u",
        stub_features=StubDecisionFeatures(market_id="m", closes=["1", "2"]),
    )

    assert result.error is not None
    assert isinstance(result.decision, LlmDecisionOutput)
    assert str(result.decision.target) == "0"

    row = db_session.get(LlmCallRow, result.call_id)
    assert row is not None
    assert row.error is not None


def test_llm_gateway_records_queue_full_error(db_session: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "0.1")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url=None,
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    def _raise_queue_full(
        *,
        url: str,
        headers: dict[str, str],
        req: dict[str, Any],
        timeout_seconds: float,
        client: httpx.Client | None = None,
        queue_priority: int = 0,
    ) -> dict[str, Any]:
        del url, headers, req, timeout_seconds, client, queue_priority
        raise QueueFullError("llm_requests", 2)

    monkeypatch.setattr("v4t.llm.gateway.post_json_request", _raise_queue_full)

    gateway = LlmGateway()
    run_id = uuid4()

    result = gateway.call_decision(
        db_session,
        run_id=run_id,
        observed_at=observed_at,
        model_key="gpt-4o-mini",
        system_prompt="s",
        user_prompt="u",
        stub_features=StubDecisionFeatures(market_id="m", closes=["1", "2"]),
    )

    assert result.error is not None
    assert "Queue 'llm_requests' is full" in result.error

    row = db_session.get(LlmCallRow, result.call_id)
    assert row is not None
    assert row.error is not None
    assert "Queue 'llm_requests' is full" in row.error


def test_model_not_allowed_records_audit_trail(db_session: Any) -> None:
    """Verify model_not_allowed path creates LlmCallRow with error."""
    gateway = LlmGateway()
    run_id = uuid4()
    observed_at = datetime.now(UTC)

    result = gateway.call_decision(
        db_session,
        run_id=run_id,
        observed_at=observed_at,
        model_key="forbidden-model",
        system_prompt="test system",
        user_prompt="test user",
        stub_features=StubDecisionFeatures(market_id="m", closes=["1", "2"]),
    )

    assert result.call_id is not None
    assert result.error == "model_not_allowed: forbidden-model"

    call = db_session.get(LlmCallRow, result.call_id)
    assert call is not None
    assert call.run_id == run_id
    assert call.purpose == "decision"
    assert call.error == "model_not_allowed: forbidden-model"
    assert call.response_raw is None


def test_budget_exceeded_records_audit_trail(db_session: Any, monkeypatch: Any) -> None:
    """Verify budget_exceeded path creates LlmCallRow with error."""
    monkeypatch.setenv("V4T_LLM_MAX_DECISION_CALLS_PER_RUN", "1")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    run_id = uuid4()

    # Pre-populate one call to hit the budget limit
    db_session.add(
        LlmCallRow(
            run_id=run_id,
            dataset_id=None,
            purpose="decision",
            observed_at=observed_at,
            prompt={},
            response_raw=None,
            response_parsed=None,
            usage=None,
            latency_ms=0,
            error=None,
            created_at=observed_at,
        )
    )
    db_session.commit()

    gateway = LlmGateway()

    result = gateway.call_decision(
        db_session,
        run_id=run_id,
        observed_at=observed_at,
        model_key="stub",
        system_prompt="test system",
        user_prompt="test user",
        stub_features=StubDecisionFeatures(market_id="m", closes=["1", "2"]),
    )

    assert result.call_id is not None
    assert result.error == "budget_exceeded: max decision calls per run"

    call = db_session.get(LlmCallRow, result.call_id)
    assert call is not None
    assert call.run_id == run_id
    assert call.purpose == "decision"
    assert call.error == "budget_exceeded: max decision calls per run"
    assert call.response_raw is None


def test_window_breakdown_circuit_breaker_isolated_per_submission(
    db_session: Any, monkeypatch: Any
) -> None:
    """Verify circuit breaker state is isolated per submission_id."""
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "0.1")
    get_settings.cache_clear()

    class BoomClient:
        def __init__(self, *args: Any, **kwargs: Any):
            pass

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *args: Any) -> bool:
            return False

        def post(self, url: Any, **kwargs: Any) -> NoReturn:
            raise httpx.ConnectError("boom", request=httpx.Request("POST", str(url)))

    monkeypatch.setattr(httpx, "Client", BoomClient)

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url=None,
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    gateway = LlmGateway()
    sub_a = uuid4()
    sub_b = uuid4()

    # Trigger 5 failures for submission A to open its circuit
    for _ in range(5):
        _call_id, _breakdown, used_fallback = gateway.call_window_breakdown(
            db_session,
            submission_id=sub_a,
            window_code="w1",
            observed_at=observed_at,
            model_key="gpt-4o-mini",
            system_prompt="s",
            user_prompt="u",
            fallback_breakdown={"summary": "fallback"},
        )
        assert used_fallback

    # 6th call for submission A should hit circuit breaker
    call_id_a, _breakdown_a, used_fallback_a = gateway.call_window_breakdown(
        db_session,
        submission_id=sub_a,
        window_code="w1",
        observed_at=observed_at,
        model_key="gpt-4o-mini",
        system_prompt="s",
        user_prompt="u",
        fallback_breakdown={"summary": "fallback"},
    )
    assert used_fallback_a
    row_a = db_session.get(LlmCallRow, call_id_a)
    assert row_a.error == "circuit_breaker_open"

    # Submission B should NOT be blocked
    call_id_b, _breakdown_b, used_fallback_b = gateway.call_window_breakdown(
        db_session,
        submission_id=sub_b,
        window_code="w1",
        observed_at=observed_at,
        model_key="gpt-4o-mini",
        system_prompt="s",
        user_prompt="u",
        fallback_breakdown={"summary": "fallback"},
    )
    assert used_fallback_b
    row_b = db_session.get(LlmCallRow, call_id_b)
    assert row_b.error != "circuit_breaker_open"
