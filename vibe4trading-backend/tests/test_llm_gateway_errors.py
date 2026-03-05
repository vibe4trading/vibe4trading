from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx

from v4t.db.models import LlmCallRow, LlmModelRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.settings import get_settings


def test_llm_gateway_returns_fallback_on_transport_error(db_session, monkeypatch) -> None:
    # Force the gateway into non-stub mode.
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "0.1")
    get_settings.cache_clear()

    class BoomClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, D401
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def post(self, url, headers=None, json=None):  # noqa: ANN001
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
    assert result.decision.targets == {}

    row = db_session.get(LlmCallRow, result.call_id)
    assert row is not None
    assert row.error is not None
