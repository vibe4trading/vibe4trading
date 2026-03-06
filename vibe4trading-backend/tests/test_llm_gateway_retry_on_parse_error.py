from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import httpx
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.contracts.payloads import LlmDecisionOutput
from v4t.db.models import LlmCallRow, LlmModelRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.settings import get_settings


def test_llm_gateway_retries_on_unparseable_json(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url="http://example.invalid",
            api_key="x",
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs
            self.calls = 0

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: object | None,
        ) -> bool:
            del exc_type, exc, tb
            return False

        def post(
            self,
            url: Any,
            headers: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
        ) -> FakeResponse:
            del url, headers, json
            self.calls += 1
            if self.calls == 1:
                content = '{"schema_version":2,"target":0.25,"mode":"spot","leverage":1'
            else:
                content = (
                    '{"schema_version":2,"target":0.25,"mode":"spot","leverage":1,'
                    '"confidence":0.6,"key_signals":["ok"],"rationale":"ok"}'
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
    assert isinstance(result.decision, LlmDecisionOutput)
    assert str(result.decision.target) == "0.25"

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


def test_llm_gateway_keeps_prompt_on_transport_retry(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url="http://example.invalid",
            api_key="x",
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    user_prompt = "u"

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs
            self.calls = 0
            self.prompts: list[str | None] = []

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: object | None,
        ) -> bool:
            del exc_type, exc, tb
            return False

        def post(
            self,
            url: Any,
            headers: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
        ) -> FakeResponse:
            del headers
            self.calls += 1
            req_json = json or {}
            msgs_any = req_json.get("messages")
            msgs = cast(list[dict[str, Any]], msgs_any) if isinstance(msgs_any, list) else None
            if isinstance(msgs, list) and len(msgs) >= 2:
                content = msgs[1].get("content")
                self.prompts.append(content if isinstance(content, str) else None)

            if self.calls == 1:
                raise httpx.ConnectError("boom", request=httpx.Request("POST", str(url)))

            content = '{"schema_version":2,"target":0.25,"mode":"spot","leverage":1,"stop_loss_pct":5.0,"take_profit_pct":10.0,"confidence":0.5,"key_signals":["ok"],"rationale":"ok"}'
            return FakeResponse({"choices": [{"message": {"content": content}}]})

    fake_client = FakeClient()

    def _client_factory(*args: Any, **kwargs: Any) -> FakeClient:
        del args, kwargs
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
    assert isinstance(result.decision, LlmDecisionOutput)
    assert fake_client.prompts == [user_prompt, user_prompt]


def test_llm_gateway_uses_model_api_key_when_env_key_missing(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.delenv("V4T_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("V4T_LLM_API_KEY", raising=False)
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("V4T_LLM_TIMEOUT_SECONDS", "1.0")
    get_settings.cache_clear()

    observed_at = datetime.now(UTC)
    db_session.add(
        LlmModelRow(
            model_key="gpt-4o-mini",
            label="GPT-4o mini",
            api_base_url="https://router.example.test/v1",
            api_key="sk-model-override",
            enabled=True,
            created_at=observed_at,
            updated_at=observed_at,
        )
    )
    db_session.commit()

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self._payload

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: object | None,
        ) -> bool:
            del exc_type, exc, tb
            return False

        def post(
            self,
            url: Any,
            headers: dict[str, str] | None = None,
            json: dict[str, Any] | None = None,
        ) -> FakeResponse:
            del json
            assert str(url) == "https://router.example.test/v1/chat/completions"
            assert headers == {"Authorization": "Bearer sk-model-override"}
            content = '{"schema_version":2,"target":0.25,"mode":"spot","leverage":1,"confidence":0.6,"key_signals":["ok"],"rationale":"ok"}'
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
    assert isinstance(result.decision, LlmDecisionOutput)
    assert str(result.decision.target) == "0.25"
