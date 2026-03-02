from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fce.contracts.payloads import LlmDecisionOutputV1
from fce.db.models import LlmCallRow
from fce.llm.json_extract import extract_first_json_object
from fce.settings import get_settings
from fce.settings import parse_csv_set


class StubDecisionFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    closes: list[str]  # decimal strings


@dataclass
class LlmCallResult:
    call_id: UUID | None
    decision: LlmDecisionOutputV1
    error: str | None = None


def _now() -> datetime:
    return datetime.now(UTC)


class LlmGateway:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._allowed_models = parse_csv_set(self.settings.llm_model_allowlist)

        # Best-effort caches to avoid repeated budget queries in long-lived loops (live runs).
        self._budget_blocked_runs: set[tuple[UUID, str]] = set()
        self._budget_blocked_datasets: set[tuple[UUID, str]] = set()

    def _model_allowed(self, model_key: str) -> bool:
        if model_key == "stub":
            return True
        if self._allowed_models is None:
            return True
        return model_key in self._allowed_models

    def _budget_exceeded_run(
        self, session: Session, *, run_id: UUID, purpose: str, limit: int
    ) -> bool:
        if limit <= 0:
            return False
        key = (run_id, purpose)
        if key in self._budget_blocked_runs:
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.run_id == run_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._budget_blocked_runs.add(key)
            return True
        return False

    def _budget_exceeded_dataset(
        self, session: Session, *, dataset_id: UUID, purpose: str, limit: int
    ) -> bool:
        if limit <= 0:
            return False
        key = (dataset_id, purpose)
        if key in self._budget_blocked_datasets:
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.dataset_id == dataset_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._budget_blocked_datasets.add(key)
            return True
        return False

    def _is_retryable(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.TransportError):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            return status in (408, 429) or status >= 500
        return False

    def call_decision(
        self,
        session: Session,
        *,
        run_id: UUID,
        observed_at: datetime,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        stub_features: StubDecisionFeatures,
        temperature: float = 0.0,
        max_output_tokens: int = 800,
    ) -> LlmCallResult:
        """Call the model and parse a strict decision JSON object."""

        use_stub = (
            model_key == "stub" or not self.settings.llm_base_url or not self.settings.llm_api_key
        )

        if use_stub:
            decision = self._stub_decision(stub_features)
            call = LlmCallRow(
                run_id=run_id,
                dataset_id=None,
                purpose="decision",
                observed_at=observed_at,
                prompt={
                    "model": "stub",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stub_features": stub_features.model_dump(),
                },
                response_raw=None,
                response_parsed=decision.model_dump(mode="json"),
                usage=None,
                latency_ms=0,
                error=None,
                created_at=_now(),
            )
            session.add(call)
            session.flush()
            return LlmCallResult(call_id=call.call_id, decision=decision, error=None)

        if not self._model_allowed(model_key):
            return LlmCallResult(
                call_id=None,
                decision=LlmDecisionOutputV1(schema_version=1, targets={}),
                error=f"model_not_allowed: {model_key}",
            )

        if self._budget_exceeded_run(
            session,
            run_id=run_id,
            purpose="decision",
            limit=int(self.settings.llm_max_decision_calls_per_run),
        ):
            return LlmCallResult(
                call_id=None,
                decision=LlmDecisionOutputV1(schema_version=1, targets={}),
                error="budget_exceeded: max decision calls per run",
            )

        started = time.perf_counter()
        req = {
            "model": model_key,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        assert self.settings.llm_base_url is not None
        assert self.settings.llm_api_key is not None
        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}

        resp_raw: str | None = None
        resp_parsed: dict[str, Any] | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        decision: LlmDecisionOutputV1 | None = None

        try:
            last_exc: Exception | None = None
            data: dict[str, Any] | None = None
            max_attempts = max(1, int(self.settings.llm_max_retries))
            for attempt in range(1, max_attempts + 1):
                try:
                    with httpx.Client(timeout=float(self.settings.llm_timeout_seconds)) as client:
                        r = client.post(url, headers=headers, json=req)
                        r.raise_for_status()
                        data = r.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if (
                        attempt < max_attempts
                        and isinstance(exc, Exception)
                        and self._is_retryable(exc)
                    ):
                        continue
                    data = None
                    break

            if data is None:
                raise last_exc or RuntimeError("LLM request failed")

            usage = data.get("usage")
            content = data["choices"][0]["message"]["content"]
            resp_raw = content
            obj = extract_first_json_object(content)
            resp_parsed = obj
            decision = LlmDecisionOutputV1.model_validate(obj)
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            # Failure policy: hold last targets by returning an empty targets dict.
            decision = LlmDecisionOutputV1(schema_version=1, targets={})
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = LlmCallRow(
                run_id=run_id,
                dataset_id=None,
                purpose="decision",
                observed_at=observed_at,
                prompt=req,
                response_raw=resp_raw,
                response_parsed=resp_parsed,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
                created_at=_now(),
            )
            session.add(call)
            session.flush()

        assert decision is not None
        return LlmCallResult(call_id=call.call_id, decision=decision, error=error)

    def call_summary(
        self,
        session: Session,
        *,
        run_id: UUID,
        observed_at: datetime,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_output_tokens: int = 800,
    ) -> tuple[UUID | None, str]:
        """Generate a post-run summary text."""

        use_stub = (
            model_key == "stub" or not self.settings.llm_base_url or not self.settings.llm_api_key
        )

        if use_stub:
            text = "(stub) Run complete. See equity curve + decision stream for details."
            call = LlmCallRow(
                run_id=run_id,
                dataset_id=None,
                purpose="summary",
                observed_at=observed_at,
                prompt={
                    "model": "stub",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                response_raw=text,
                response_parsed=None,
                usage=None,
                latency_ms=0,
                error=None,
                created_at=_now(),
            )
            session.add(call)
            session.flush()
            return call.call_id, text

        if not self._model_allowed(model_key):
            return None, f"(guardrail) model_not_allowed: {model_key}"

        if self._budget_exceeded_run(
            session,
            run_id=run_id,
            purpose="summary",
            limit=int(self.settings.llm_max_summary_calls_per_run),
        ):
            return None, "(guardrail) budget exceeded: summary skipped"

        started = time.perf_counter()
        req = {
            "model": model_key,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        assert self.settings.llm_base_url is not None
        assert self.settings.llm_api_key is not None
        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}

        resp_raw: str | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        return_text: str
        try:
            last_exc: Exception | None = None
            data: dict[str, Any] | None = None
            max_attempts = max(1, int(self.settings.llm_max_retries))
            for attempt in range(1, max_attempts + 1):
                try:
                    with httpx.Client(timeout=float(self.settings.llm_timeout_seconds)) as client:
                        r = client.post(url, headers=headers, json=req)
                        r.raise_for_status()
                        data = r.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if (
                        attempt < max_attempts
                        and isinstance(exc, Exception)
                        and self._is_retryable(exc)
                    ):
                        continue
                    data = None
                    break

            if data is None:
                raise last_exc or RuntimeError("LLM request failed")

            usage = data.get("usage")
            content = data["choices"][0]["message"]["content"]
            resp_raw = content
            return_text = content
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            return_text = f"(error) summary unavailable: {error}"
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = LlmCallRow(
                run_id=run_id,
                dataset_id=None,
                purpose="summary",
                observed_at=observed_at,
                prompt=req,
                response_raw=resp_raw,
                response_parsed=None,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
                created_at=_now(),
            )
            session.add(call)
            session.flush()

        return call.call_id, return_text

    def call_sentiment_item_summary(
        self,
        session: Session,
        *,
        dataset_id: UUID,
        observed_at: datetime,
        model_key: str,
        item_text: str,
        item_url: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 200,
    ) -> tuple[UUID | None, str]:
        """Generate a 1:1 summary for a single sentiment.item.

        Always records an LlmCallRow (even in stub mode) so sentiment.item_summary
        can reference llm_call_id.
        """

        system_prompt = (
            "You summarize a single news/social item for a trading agent. "
            "Return 1-2 plain-text sentences. No markdown, no bullet list."
        )
        user_prompt = (f"url={item_url}\n\n" if item_url else "") + item_text

        use_stub = (
            model_key == "stub" or not self.settings.llm_base_url or not self.settings.llm_api_key
        )
        if use_stub:
            snippet = " ".join((item_text or "").split())
            if len(snippet) > 240:
                snippet = snippet[:240].rstrip() + "..."
            text = f"Summary: {snippet}" if snippet else "Summary: (empty)"
            call = LlmCallRow(
                run_id=None,
                dataset_id=dataset_id,
                purpose="sentiment_item_summary",
                observed_at=observed_at,
                prompt={
                    "model": "stub",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                response_raw=text,
                response_parsed=None,
                usage=None,
                latency_ms=0,
                error=None,
                created_at=_now(),
            )
            session.add(call)
            session.flush()
            return call.call_id, text

        if not self._model_allowed(model_key):
            snippet = " ".join((item_text or "").split())
            if len(snippet) > 240:
                snippet = snippet[:240].rstrip() + "..."
            text = f"(guardrail) Summary: {snippet}" if snippet else "(guardrail) Summary: (empty)"
            return None, text

        if self._budget_exceeded_dataset(
            session,
            dataset_id=dataset_id,
            purpose="sentiment_item_summary",
            limit=int(self.settings.llm_max_sentiment_item_summaries_per_dataset),
        ):
            snippet = " ".join((item_text or "").split())
            if len(snippet) > 240:
                snippet = snippet[:240].rstrip() + "..."
            text = f"(guardrail) Summary: {snippet}" if snippet else "(guardrail) Summary: (empty)"
            return None, text

        started = time.perf_counter()
        req = {
            "model": model_key,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

        assert self.settings.llm_base_url is not None
        assert self.settings.llm_api_key is not None
        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}

        resp_raw: str | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        return_text: str
        try:
            last_exc: Exception | None = None
            data: dict[str, Any] | None = None
            max_attempts = max(1, int(self.settings.llm_max_retries))
            for attempt in range(1, max_attempts + 1):
                try:
                    with httpx.Client(timeout=float(self.settings.llm_timeout_seconds)) as client:
                        r = client.post(url, headers=headers, json=req)
                        r.raise_for_status()
                        data = r.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if (
                        attempt < max_attempts
                        and isinstance(exc, Exception)
                        and self._is_retryable(exc)
                    ):
                        continue
                    data = None
                    break

            if data is None:
                raise last_exc or RuntimeError("LLM request failed")

            usage = data.get("usage")
            content = data["choices"][0]["message"]["content"]
            resp_raw = content
            return_text = content
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            return_text = f"(error) summary unavailable: {error}"
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = LlmCallRow(
                run_id=None,
                dataset_id=dataset_id,
                purpose="sentiment_item_summary",
                observed_at=observed_at,
                prompt=req,
                response_raw=resp_raw,
                response_parsed=None,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
                created_at=_now(),
            )
            session.add(call)
            session.flush()

        return call.call_id, return_text

    def _stub_decision(self, features: StubDecisionFeatures) -> LlmDecisionOutputV1:
        closes = [Decimal(c) for c in features.closes if c]
        if len(closes) < 2:
            target = Decimal("0")
            rationale = "No price history; stay in cash."
            confidence = Decimal("0.2")
        else:
            momentum = closes[-1] - closes[0]
            if momentum > 0:
                target = Decimal("0.50")
                rationale = "Momentum up over lookback; take moderate long exposure."
                confidence = Decimal("0.55")
            else:
                target = Decimal("0")
                rationale = "Momentum flat/down; reduce exposure."
                confidence = Decimal("0.45")

        return LlmDecisionOutputV1(
            schema_version=1,
            targets={features.market_id: target},
            next_check_seconds=900,
            confidence=confidence,
            key_signals=["stub_momentum"],
            rationale=rationale,
        )
