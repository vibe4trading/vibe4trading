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
