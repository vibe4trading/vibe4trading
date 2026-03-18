from __future__ import annotations

import json
import time
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

from v4t.contracts.arena_report import ArenaSubmissionReportNarrative
from v4t.contracts.payloads import LlmDecisionOutput
from v4t.db.models import LlmCallRow, LlmModelRow
from v4t.llm.budget import LlmBudgetTracker
from v4t.llm.json_extract import extract_first_json_object_text
from v4t.llm.retry import (
    call_with_retry,
    compute_backoff_seconds,
    is_retryable,
    post_json_request,
)
from v4t.settings import get_settings
from v4t.utils.datetime import now

_LOG: Final = structlog.get_logger("llm.gateway")

_CIRCUIT_BREAKER_THRESHOLD = 5
_CIRCUIT_BREAKER_TIMEOUT_SECONDS = 60.0


def _extract_usage(data: dict[str, Any]) -> dict[str, Any] | None:
    usage_any = data.get("usage")
    return cast(dict[str, Any], usage_any) if isinstance(usage_any, dict) else None


def _extract_message_content(data: dict[str, Any]) -> str:
    choices_any = data.get("choices")
    if not isinstance(choices_any, list) or not choices_any:
        raise ValueError("LLM response missing 'choices'")
    choices = cast(list[object], choices_any)

    first_any = choices[0]
    if not isinstance(first_any, dict):
        raise ValueError("LLM response has invalid 'choices' entry")
    first = cast(dict[str, Any], first_any)

    msg_any = first.get("message")
    if not isinstance(msg_any, dict):
        raise ValueError("LLM response missing 'message'")
    message = cast(dict[str, Any], msg_any)

    content_any = message.get("content")
    if not isinstance(content_any, str):
        raise ValueError("LLM response missing text content")
    return content_any


class StubDecisionFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: str
    closes: list[str]  # decimal strings


@dataclass
class LlmCallResult:
    call_id: UUID | None
    decision: LlmDecisionOutput
    error: str | None = None


class LlmGateway:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._budget = LlmBudgetTracker()
        self._window_breakdown_circuit: dict[UUID, tuple[int, float | None]] = {}

    def _get_enabled_model_row(self, session: Session, model_key: str) -> LlmModelRow | None:
        return (
            session.execute(
                select(LlmModelRow)
                .where(LlmModelRow.model_key == model_key, LlmModelRow.enabled.is_(True))
                .limit(1)
            )
            .scalars()
            .one_or_none()
        )

    def _model_allowed(self, session: Session, model_key: str) -> bool:
        if model_key == "stub":
            return True

        return self._get_enabled_model_row(session, model_key) is not None

    def _resolve_transport(self, session: Session, model_key: str) -> tuple[str | None, str | None]:
        if model_key == "stub":
            return None, None

        row = self._get_enabled_model_row(session, model_key)
        base_url = self.settings.llm_base_url
        api_key = self.settings.llm_api_key

        if row is not None and row.api_base_url:
            base_url = row.api_base_url
        if row is not None and row.api_key:
            api_key = row.api_key

        return base_url, api_key

    def _use_stub(self, session: Session, model_key: str) -> bool:
        return model_key == "stub"

    def _api_url_and_headers(self, base_url: str, api_key: str) -> tuple[str, dict[str, str]]:
        base_url = base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
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
    ) -> tuple[UUID, str]:
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
        return call.call_id, err

    def _missing_config_decision_result(
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
    ) -> LlmCallResult:
        call_id, err = self._missing_config_result(
            session,
            run_id=run_id,
            dataset_id=dataset_id,
            purpose=purpose,
            observed_at=observed_at,
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        return LlmCallResult(call_id=call_id, decision=self._empty_decision(), error=err)

    def _missing_config_text_result(
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
    ) -> tuple[UUID, str]:
        call_id, err = self._missing_config_result(
            session,
            run_id=run_id,
            dataset_id=dataset_id,
            purpose=purpose,
            observed_at=observed_at,
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        return call_id, f"(error) {err}"

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
        if self._budget.exceeded_run(
            session,
            run_id=run_id,
            purpose="decision",
            limit=int(self.settings.llm_max_decision_calls_per_run),
        ):
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
                dataset_id=None,
                purpose="decision",
                observed_at=observed_at,
                prompt=req,
                response_raw=None,
                response_parsed=None,
                usage=None,
                latency_ms=0,
                error="budget_exceeded: max decision calls per run",
            )
            return LlmCallResult(
                call_id=call.call_id,
                decision=self._empty_decision(),
                error="budget_exceeded: max decision calls per run",
            )

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
                dataset_id=None,
                purpose="decision",
                observed_at=observed_at,
                prompt=req,
                response_raw=None,
                response_parsed=None,
                usage=None,
                latency_ms=0,
                error=f"model_not_allowed: {model_key}",
            )
            return LlmCallResult(
                call_id=call.call_id,
                decision=self._empty_decision(),
                error=f"model_not_allowed: {model_key}",
            )

        base_url, api_key = self._resolve_transport(session, model_key)
        if base_url is None or not api_key:
            return self._missing_config_decision_result(
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
        url, headers = self._api_url_and_headers(base_url, api_key)
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
                decision: LlmDecisionOutput | None = None

                try:
                    data = post_json_request(
                        url=url,
                        headers=headers,
                        req=req_attempt,
                        timeout_seconds=float(self.settings.llm_timeout_seconds),
                        client=client,
                        queue_priority=-1 if attempt > 1 else 0,
                    )

                    usage = _extract_usage(data)
                    content = _extract_message_content(data)

                    resp_raw = content
                    obj, _candidate = extract_first_json_object_text(content)
                    resp_parsed = obj
                    decision = self._parse_decision_output(obj)
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
            decision=self._empty_decision(),
            error=last_error,
        )

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

        base_url, api_key = self._resolve_transport(session, model_key)
        if base_url is None or not api_key:
            return self._missing_config_text_result(
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

        url, headers = self._api_url_and_headers(base_url, api_key)
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
            usage = _extract_usage(data)
            content = _extract_message_content(data)
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

    def call_submission_report(
        self,
        session: Session,
        *,
        submission_id: UUID,
        observed_at: datetime,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        fallback_report: dict[str, Any],
        temperature: float = 0.0,
        max_output_tokens: int = 16384,
    ) -> tuple[UUID | None, dict[str, Any], bool]:
        req = self._build_request(
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        fallback_raw = json.dumps(fallback_report, separators=(",", ":"))

        if self._use_stub(session, model_key):
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="submission_report",
                observed_at=observed_at,
                prompt=req,
                response_raw=fallback_raw,
                response_parsed=fallback_report,
                usage=None,
                latency_ms=0,
                error="stub_submission_report",
            )
            return call.call_id, fallback_report, True

        if not self._model_allowed(session, model_key):
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="submission_report",
                observed_at=observed_at,
                prompt=req,
                response_raw=fallback_raw,
                response_parsed=fallback_report,
                usage=None,
                latency_ms=0,
                error=f"model_not_allowed: {model_key}",
            )
            return call.call_id, fallback_report, True

        base_url, api_key = self._resolve_transport(session, model_key)
        if base_url is None or not api_key:
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="submission_report",
                observed_at=observed_at,
                prompt=req,
                response_raw=fallback_raw,
                response_parsed=fallback_report,
                usage=None,
                latency_ms=0,
                error="llm_not_configured",
            )
            return call.call_id, fallback_report, True

        url, headers = self._api_url_and_headers(base_url, api_key)

        started = time.perf_counter()
        resp_raw: str | None = None
        resp_parsed: dict[str, Any] | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        used_fallback = False
        try:
            data = call_with_retry(
                url=url,
                headers=headers,
                req=req,
                timeout_seconds=float(self.settings.llm_timeout_seconds),
                max_retries=int(self.settings.llm_max_retries),
            )
            usage = _extract_usage(data)
            content_any = _extract_message_content(data)
            resp_raw = content_any
            obj, _candidate = extract_first_json_object_text(content_any)
            resp_parsed = obj

            # Validate schema before recording success
            try:
                ArenaSubmissionReportNarrative.model_validate(obj)
            except ValidationError as validation_exc:
                error = f"schema_validation_failed: {validation_exc!r}"
                resp_parsed = fallback_report
                used_fallback = True
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            resp_raw = fallback_raw
            resp_parsed = fallback_report
            used_fallback = True
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="submission_report",
                observed_at=observed_at,
                prompt=req,
                response_raw=resp_raw,
                response_parsed=resp_parsed,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
            )

        return call.call_id, resp_parsed or fallback_report, used_fallback

    def call_window_breakdown(
        self,
        session: Session,
        *,
        submission_id: UUID,
        window_code: str,
        observed_at: datetime,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        fallback_breakdown: dict[str, Any],
        max_output_tokens: int = 16384,
    ) -> tuple[UUID, dict[str, Any], bool]:
        from v4t.contracts.arena_report import WindowBreakdown

        req = self._build_request(
            model_key=model_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_output_tokens=max_output_tokens,
        )
        fallback_raw = json.dumps(fallback_breakdown, separators=(",", ":"))

        if self._use_stub(session, model_key):
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="arena.window_breakdown",
                observed_at=observed_at,
                prompt=req,
                response_raw=fallback_raw,
                response_parsed=fallback_breakdown,
                usage=None,
                latency_ms=0,
                error="stub_window_breakdown",
            )
            return call.call_id, fallback_breakdown, True

        if not self._model_allowed(session, model_key):
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="arena.window_breakdown",
                observed_at=observed_at,
                prompt=req,
                response_raw=fallback_raw,
                response_parsed=fallback_breakdown,
                usage=None,
                latency_ms=0,
                error=f"model_not_allowed: {model_key}",
            )
            return call.call_id, fallback_breakdown, True

        base_url, api_key = self._resolve_transport(session, model_key)
        if base_url is None or not api_key:
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="arena.window_breakdown",
                observed_at=observed_at,
                prompt=req,
                response_raw=fallback_raw,
                response_parsed=fallback_breakdown,
                usage=None,
                latency_ms=0,
                error="llm_not_configured",
            )
            return call.call_id, fallback_breakdown, True

        failures, opened_at = self._window_breakdown_circuit.get(submission_id, (0, None))

        if opened_at is not None:
            elapsed = time.perf_counter() - opened_at
            if elapsed < _CIRCUIT_BREAKER_TIMEOUT_SECONDS:
                call = self._record_call(
                    session,
                    run_id=None,
                    dataset_id=None,
                    purpose="arena.window_breakdown",
                    observed_at=observed_at,
                    prompt=req,
                    response_raw=fallback_raw,
                    response_parsed=fallback_breakdown,
                    usage=None,
                    latency_ms=0,
                    error="circuit_breaker_open",
                )
                return call.call_id, fallback_breakdown, True
            self._window_breakdown_circuit[submission_id] = (0, None)

        url, headers = self._api_url_and_headers(base_url, api_key)

        started = time.perf_counter()
        resp_raw: str | None = None
        resp_parsed: dict[str, Any] | None = None
        usage: dict[str, Any] | None = None
        error: str | None = None
        used_fallback = False
        try:
            data = call_with_retry(
                url=url,
                headers=headers,
                req=req,
                timeout_seconds=float(self.settings.llm_timeout_seconds),
                max_retries=3,
            )
            usage = _extract_usage(data)
            content_any = _extract_message_content(data)
            resp_raw = content_any
            obj, _candidate = extract_first_json_object_text(content_any)
            resp_parsed = obj
            WindowBreakdown.model_validate(obj)
            self._window_breakdown_circuit[submission_id] = (0, None)
        except Exception as exc:  # noqa: BLE001
            error = repr(exc)
            resp_raw = fallback_raw
            resp_parsed = fallback_breakdown
            used_fallback = True
            failures += 1
            if failures >= _CIRCUIT_BREAKER_THRESHOLD:
                self._window_breakdown_circuit[submission_id] = (failures, time.perf_counter())
                _LOG.warning(
                    "window_breakdown_circuit_breaker_opened",
                    submission_id=str(submission_id),
                    consecutive_failures=failures,
                )
            else:
                self._window_breakdown_circuit[submission_id] = (failures, None)
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            call = self._record_call(
                session,
                run_id=None,
                dataset_id=None,
                purpose="arena.window_breakdown",
                observed_at=observed_at,
                prompt=req,
                response_raw=resp_raw,
                response_parsed=resp_parsed,
                usage=usage,
                latency_ms=latency_ms,
                error=error,
            )

        return call.call_id, resp_parsed or fallback_breakdown, used_fallback

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

        base_url, api_key = self._resolve_transport(session, model_key)
        if base_url is None or not api_key:
            return self._missing_config_text_result(
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
        url, headers = self._api_url_and_headers(base_url, api_key)
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
            usage = _extract_usage(data)
            content_any = _extract_message_content(data)
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

    def _stub_decision(self, features: StubDecisionFeatures) -> LlmDecisionOutput:
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

        leverage = 1
        mode = "spot"
        return LlmDecisionOutput(
            schema_version=2,
            target=target,
            mode=mode,
            leverage=leverage,
            stop_loss_pct=Decimal("5.0") if target != 0 else None,
            take_profit_pct=Decimal("10.0") if target != 0 else None,
            confidence=confidence,
            key_signals=["stub_momentum"],
            rationale=rationale,
        )

    def _empty_decision(self) -> LlmDecisionOutput:
        return LlmDecisionOutput(
            schema_version=2,
            target=Decimal("0"),
            mode="spot",
            leverage=1,
            stop_loss_pct=None,
            take_profit_pct=None,
            confidence=Decimal("0"),
            key_signals=["llm_unavailable"],
            rationale="No decision available.",
        )

    def _parse_decision_output(self, obj: dict[str, Any]) -> LlmDecisionOutput:
        return LlmDecisionOutput.model_validate(obj)


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
