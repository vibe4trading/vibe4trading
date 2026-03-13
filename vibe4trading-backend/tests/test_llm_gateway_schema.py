from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy.orm import Session

from v4t.contracts.payloads import LlmDecisionOutput
from v4t.db.models import LlmModelRow
from v4t.llm.gateway import LlmGateway, StubDecisionFeatures
from v4t.settings import get_settings


def test_llm_gateway_parses_schema(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("V4T_LLM_BASE_URL", "http://example.invalid")
    monkeypatch.setenv("V4T_LLM_API_KEY", "x")
    monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "0")
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
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, dict[str, str]]]]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"schema_version":2,"target":-2.0,"mode":"futures",'
                                '"leverage":3,"stop_loss_pct":5.0,"take_profit_pct":10.0,'
                                '"confidence":0.7,'
                                '"key_signals":["trend"],"rationale":"short the breakdown"}'
                            )
                        }
                    }
                ]
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

    result = LlmGateway().call_decision(
        db_session,
        run_id=uuid4(),
        observed_at=observed_at,
        model_key="gpt-4o-mini",
        system_prompt="s",
        user_prompt="u",
        stub_features=StubDecisionFeatures(
            market_id="spot:test:BTC",
            closes=["1", "2"],
        ),
    )

    assert result.error is None
    assert isinstance(result.decision, LlmDecisionOutput)
    assert result.decision.mode == "futures"
    assert str(result.decision.target) == "-2.0"
