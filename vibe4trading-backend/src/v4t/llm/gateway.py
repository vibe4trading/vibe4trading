from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final, cast
from uuid import UUID

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.contracts.payloads import LlmDecisionOutputV1
from v4t.db.models import LlmCallRow, LlmModelRow
from v4t.llm.budget import LlmBudgetTracker
from v4t.llm.json_extract import extract_first_json_object_text
from v4t.llm.retry import call_with_retry, compute_backoff_seconds, is_retryable
from v4t.settings import get_settings, parse_csv_set
from v4t.utils.datetime import now

_LOG: Final = structlog.get_logger("llm.gateway")


class StubDecisionFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    closes: list[str]  # decimal strings


@dataclass
class LlmCallResult:
    call_id: UUID | None
    decision: LlmDecisionOutputV1
    error: str | None = None


class LlmGateway:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._allowed_models = parse_csv_set(self.settings.llm_model_allowlist)
        self._budget = LlmBudgetTracker()

    def _model_allowed(self, session: Session, model_key: str) -> bool:
        if model_key == "stub":
            return True
        if self._allowed_models is not None and model_key not in self._allowed_models:
            return False

        row = (
            session.execute(
                select(LlmModelRow)
                .where(LlmModelRow.model_key == model_key, LlmModelRow.enabled.is_(True))
                .limit(1)
            )
            .scalars()
            .one_or_none()
        )
        return row is not None

    def _resolve_base_url(self, session: Session, model_key: str) -> str | None:
        if model_key == "stub":
            return None
        row = (
            session.execute(
                select(LlmModelRow)
                .where(LlmModelRow.model_key == model_key, LlmModelRow.enabled.is_(True))
                .limit(1)
            )
            .scalars()
            .one_or_none()
        )

        if row is not None and row.api_base_url:
            return row.api_base_url

        return self.settings.llm_base_url

    def _use_stub(self, session: Session, model_key: str) -> bool:
        return model_key == "stub"

    def _api_url_and_headers(self, base_url: str) -> tuple[str, dict[str, str]]:
        if self.settings.llm_api_key is None:
            raise ValueError("llm_api_key must not be None")
        base_url = base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        return url, headers

    def _missing_config_result(
        self,
        session: Session,
        *,
        run_id: UUID | None,
        dataset_id: UUID | None,
        purpose: str,
        observed_at: datetime,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> LlmCallResult | tuple[UUID | None, str]:
        err = "llm_not_configured"
        req = self._build_request(
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        call = self._record_call(
            session,
            run_id=run_id,
            dataset_id=dataset_id,
            purpose=purpose,
            observed_at=observed_at,
            prompt=req,
            response_raw=None,
            response_parsed=None,
            usage=None,
            latency_ms=0,
            error=err,
        )

        if purpose == "decision":
            return LlmCallResult(
                call_id=call.call_id,
                decision=LlmDecisionOutputV1(schema_version=1, targets={}),
                error=err,
            )
        return call.call_id, f"(error) {err}"

    def _build_request(
        self,
        *,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        return {
            "model": model_key,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }

    def _record_call(
        self,
        session: Session,
        *,
        run_id: UUID | None,
        dataset_id: UUID | None,
        purpose: str,
        observed_at: datetime,
        prompt: dict[str, Any],
        response_raw: str | None,
        response_parsed: dict[str, Any] | None,
        usage: dict[str, Any] | None,
        latency_ms: int,
        error: str | None,
    ) -> LlmCallRow:
        call = LlmCallRow(
            run_id=run_id,
            dataset_id=dataset_id,
            purpose=purpose,
            observed_at=observed_at,
            prompt=prompt,
            response_raw=response_raw,
            response_parsed=response_parsed,
            usage=usage,
            latency_ms=latency_ms,
            error=error,
            created_at=now(),
        )
        session.add(call)
        session.flush()
        return call

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
        if self._use_stub(session, model_key):
            decision = self._stub_decision(stub_features)
            call = self._record_call(
                session,
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
            )
            return LlmCallResult(call_id=call.call_id, decision=decision, error=None)

        if not self._model_allowed(session, model_key):
            return LlmCallResult(
                call_id=None,
                decision=LlmDecisionOutputV1(schema_version=1, targets={}),
                error=f"model_not_allowed: {model_key}",
            )

        if self._budget.exceeded_run(
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

        base_url = self._resolve_base_url(session, model_key)
        if base_url is None or not self.settings.llm_api_key:
            res = self._missing_config_result(
                session,
                run_id=run_id,
                dataset_id=None,
                purpose="decision",
                observed_at=observed_at,
                model_key=model_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if not isinstance(res, LlmCallResult):
                raise ValueError("unexpected _missing_config_result return type")
            return res
        url, headers = self._api_url_and_headers(base_url)
        max_attempts = max(1, int(self.settings.llm_max_retries) + 1)
        attempt_user_prompt = user_prompt

        last_call_id: UUID | None = None
        last_error: str | None = None
        last_exc: Exception | None = None

        with httpx.Client(timeout=float(self.settings.llm_timeout_seconds)) as client:
            for attempt in range(1, max_attempts + 1):
                req_attempt = self._build_request(
                    model_key=model_key,
                    system_prompt=system_prompt,
                    user_prompt=attempt_user_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )

                started = time.perf_counter()
                resp_raw: str | None = None
                resp_parsed: dict[str, Any] | None = None
                usage: dict[str, Any] | None = None
                error: str | None = None
                decision: LlmDecisionOutputV1 | None = None

                try:
                    r = client.post(url, headers=headers, json=req_attempt)
                    r.raise_for_status()
                    data_any = r.json()
                    if not isinstance(data_any, dict):
                        raise ValueError("LLM response is not a JSON object")

                    data = cast(dict[str, Any], data_any)

                    usage_any = data.get("usage")
                    usage = usage_any if isinstance(usage_any, dict) else None

                    choices = data.get("choices")
                    if not isinstance(choices, list) or not choices:
                        raise ValueError("LLM response missing 'choices'")

                    first = choices[0]
                    if not isinstance(first, dict):
                        raise ValueError("LLM response has invalid 'choices' entry")
                    msg_any = first.get("message")
                    if not isinstance(msg_any, dict):
                        raise ValueError("LLM response missing 'message'")
                    content_any = msg_any.get("content")
                    if not isinstance(content_any, str):
                        raise ValueError("LLM response missing text content")

                    content = content_any

                    resp_raw = content
                    obj, _candidate = extract_first_json_object_text(content)
                    resp_parsed = obj
                    decision = LlmDecisionOutputV1.model_validate(obj)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    error = repr(exc)
                    last_error = error
                finally:
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    try:
                        call = self._record_call(
                            session,
                            run_id=run_id,
                            dataset_id=None,
                            purpose="decision",
                            observed_at=observed_at,
                            prompt=req_attempt,
                            response_raw=resp_raw,
                            response_parsed=resp_parsed,
                            usage=usage,
                            latency_ms=latency_ms,
                            error=error,
                        )
                        last_call_id = call.call_id
                    except Exception as rec_exc:  # noqa: BLE001
                        session.rollback()
                        last_call_id = None
                        last_error = last_error or repr(rec_exc)
                        _LOG.error(
                            "llm_record_call_failed",
                            run_id=str(run_id) if run_id else None,
                            error=repr(rec_exc),
                            llm_error=error,
                            exc_info=True,
                        )

                if decision is not None:
                    return LlmCallResult(call_id=last_call_id, decision=decision, error=None)

                if attempt >= max_attempts:
                    break

                if last_exc is None:
                    break

                if is_retryable(last_exc):
                    time.sleep(compute_backoff_seconds(attempt=attempt, exc=last_exc))
                    continue

                if _should_retry_structured_exc(last_exc):
                    attempt_user_prompt = _retry_prompt(user_prompt, last_error)
                    continue

                break

        if last_error:
            _LOG.error(
                "llm_decision_failed",
                run_id=str(run_id) if run_id else None,
                error=last_error,
                exc_info=True,
            )

        return LlmCallResult(
            call_id=last_call_id,
            decision=LlmDecisionOutputV1(schema_version=1, targets={}),
            error=last_error,
        )

    def call_decision_streaming(
        self,
        session: Session,
        *,
        run_id: UUID,
        observed_at: datetime,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        stub_features: StubDecisionFeatures,
        on_delta: Callable[[str], None],
        temperature: float = 0.0,
        max_output_tokens: int = 800,
    ) -> LlmCallResult:
        if self._use_stub(session, model_key):
            decision = self._stub_decision(stub_features)
            text = decision.model_dump_json()
            for chunk in _chunk_text(text):
                on_delta(chunk)
            call = self._record_call(
                session,
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
                response_raw=text,
                response_parsed=decision.model_dump(mode="json"),
                usage=None,
                latency_ms=0,
                error=None,
            )
            return LlmCallResult(call_id=call.call_id, decision=decision, error=None)

        res = self.call_decision(
            session,
            run_id=run_id,
            observed_at=observed_at,
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            stub_features=stub_features,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if res.error is None:
            text = json.dumps(res.decision.model_dump(mode="json"), separators=(",", ":"))
        else:
            text = f"(error) {res.error}"

        for chunk in _chunk_text(text):
            on_delta(chunk)
        return res

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
        max_output_tokens: int = 300,
    ) -> tuple[UUID | None, str]:
        if self._use_stub(session, model_key):
            text = "(stub) summary unavailable"
            call = self._record_call(
                session,
                run_id=run_id,
                dataset_id=None,
                purpose="run_summary",
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
            )
            return call.call_id, text

        if not self._model_allowed(session, model_key):
            return None, f"(error) model_not_allowed: {model_key}"

        if self._budget.exceeded_run(
            session,
            run_id=run_id,
            purpose="run_summary",
            limit=int(self.settings.llm_max_summary_calls_per_run),
        ):
            return None, "(error) budget_exceeded: max summary calls per run"

        base_url = self._resolve_base_url(session, model_key)
        if base_url is None or not self.settings.llm_api_key:
            res = self._missing_config_result(
                session,
                run_id=run_id,
                dataset_id=None,
                purpose="run_summary",
                observed_at=observed_at,
                model_key=model_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if not isinstance(res, tuple):
                raise ValueError("unexpected _missing_config_result return type")
            return res

        url, headers = self._api_url_and_headers(base_url)
        req = self._build_request(
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        started = time.perf_counter()
        resp_raw: str | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        text: str
        try:
            data = call_with_retry(
                url=url,
                headers=headers,
                req=req,
                timeout_seconds=float(self.settings.llm_timeout_seconds),
                max_retries=int(self.settings.llm_max_retries),
            )
            usage_any = data.get("usage")
            usage = usage_any if isinstance(usage_any, dict) else None
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError("LLM response missing 'choices'")
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, str):
                raise ValueError("LLM response missing text content")
            resp_raw = content
            text = content
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            text = f"(error) summary unavailable: {error}"
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = self._record_call(
                session,
                run_id=run_id,
                dataset_id=None,
                purpose="run_summary",
                observed_at=observed_at,
                prompt=req,
                response_raw=resp_raw,
                response_parsed=None,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
            )

        return call.call_id, text

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
        system_prompt = (
            "You summarize a single news/social item for a trading agent. "
            "Return 1-2 plain-text sentences. No markdown, no bullet list."
        )
        user_prompt = (f"url={item_url}\n\n" if item_url else "") + item_text

        def _snippet(txt: str) -> str:
            s = " ".join((txt or "").split())
            if len(s) > 240:
                s = s[:240].rstrip() + "..."
            return s

        if self._use_stub(session, model_key):
            snippet = _snippet(item_text)
            text = f"Summary: {snippet}" if snippet else "Summary: (empty)"
            call = self._record_call(
                session,
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
            )
            return call.call_id, text

        if not self._model_allowed(session, model_key):
            snippet = _snippet(item_text)
            text = f"(guardrail) Summary: {snippet}" if snippet else "(guardrail) Summary: (empty)"
            return None, text

        if self._budget.exceeded_dataset(
            session,
            dataset_id=dataset_id,
            purpose="sentiment_item_summary",
            limit=int(self.settings.llm_max_sentiment_item_summaries_per_dataset),
        ):
            snippet = _snippet(item_text)
            text = f"(guardrail) Summary: {snippet}" if snippet else "(guardrail) Summary: (empty)"
            return None, text

        base_url = self._resolve_base_url(session, model_key)
        if base_url is None or not self.settings.llm_api_key:
            res = self._missing_config_result(
                session,
                run_id=None,
                dataset_id=dataset_id,
                purpose="sentiment_item_summary",
                observed_at=observed_at,
                model_key=model_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if not isinstance(res, tuple):
                raise ValueError("unexpected _missing_config_result return type")
            return res
        url, headers = self._api_url_and_headers(base_url)
        req = self._build_request(
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        started = time.perf_counter()
        resp_raw: str | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        return_text: str
        try:
            data = call_with_retry(
                url=url,
                headers=headers,
                req=req,
                timeout_seconds=float(self.settings.llm_timeout_seconds),
                max_retries=int(self.settings.llm_max_retries),
            )
            usage_any = data.get("usage")
            usage = usage_any if isinstance(usage_any, dict) else None
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError("LLM response missing 'choices'")
            first = choices[0]
            if not isinstance(first, dict):
                raise ValueError("LLM response has invalid 'choices' entry")
            msg_any = first.get("message")
            if not isinstance(msg_any, dict):
                raise ValueError("LLM response missing 'message'")
            content_any = msg_any.get("content")
            if not isinstance(content_any, str):
                raise ValueError("LLM response missing text content")
            resp_raw = content_any
            return_text = content_any
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            _LOG.error(
                "llm_sentiment_summary_failed",
                dataset_id=str(dataset_id) if dataset_id else None,
                error=error,
                exc_info=True,
            )
            return_text = f"(error) summary unavailable: {error}"
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = self._record_call(
                session,
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
            )

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


def _retry_prompt(user_prompt: str, err: str | None) -> str:
    suffix = (
        "\n\nYour previous output was invalid. "
        "Return ONLY a valid JSON object matching the example. "
        "Do not wrap in markdown or add extra text."
    )
    if err:
        suffix += f" Error: {err[:200]}"
    return user_prompt + suffix


def _should_retry_structured_exc(exc: Exception) -> bool:
    return isinstance(exc, (ValueError, json.JSONDecodeError, ValidationError))


def _chunk_text(text: str, *, chunk_size: int = 48) -> list[str]:
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
