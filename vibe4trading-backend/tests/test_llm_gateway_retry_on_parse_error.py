from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import select

from v4t.db.models import LlmCallRow, LlmModelRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.settings import get_settings


def test_llm_gateway_retries_on_unparseable_json(db_session, monkeypatch) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
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

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def post(self, url, headers=None, json=None):  # noqa: ANN001
            self.calls += 1
            if self.calls == 1:
                content = '{"schema_version":1,"targets":{"m":0.25}'
            else:
                content = (
                    '{"schema_version":1,"targets":{"m":0.25},"key_signals":[],"rationale":"ok"}'
                )
            return FakeResponse({"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(httpx, "Client", FakeClient)

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

    assert result.error is None
    assert str(result.decision.targets.get("m")) == "0.25"

    rows = list(
        db_session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id == run_id, LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.created_at)
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert rows[0].error is not None
    assert rows[1].error is None


def test_llm_gateway_keeps_prompt_on_transport_retry(db_session, monkeypatch) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
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

    user_prompt = "u"

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002
            self.calls = 0
            self.prompts = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def post(self, url, headers=None, json=None):  # noqa: ANN001
            self.calls += 1
            msgs = (json or {}).get("messages") if isinstance(json, dict) else None
            if isinstance(msgs, list) and len(msgs) >= 2 and isinstance(msgs[1], dict):
                self.prompts.append(msgs[1].get("content"))

            if self.calls == 1:
                raise httpx.ConnectError("boom", request=httpx.Request("POST", str(url)))

            content = '{"schema_version":1,"targets":{"m":0.25},"key_signals":[],"rationale":"ok"}'
            return FakeResponse({"choices": [{"message": {"content": content}}]})

    fake_client = FakeClient()

    def _client_factory(*args, **kwargs):  # noqa: ANN002
        return fake_client

    monkeypatch.setattr(httpx, "Client", _client_factory)

    gateway = LlmGateway()
    run_id = uuid4()

    result = gateway.call_decision(
        db_session,
        run_id=run_id,
        observed_at=observed_at,
        model_key="gpt-4o-mini",
        system_prompt="s",
        user_prompt=user_prompt,
        stub_features=StubDecisionFeatures(market_id="m", closes=["1", "2"]),
    )

    assert result.error is None
    assert fake_client.prompts == [user_prompt, user_prompt]
