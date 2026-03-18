from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from v4t.arena.reporting import _build_fallback_window_breakdown  # pyright: ignore[reportPrivateUsage]
from v4t.contracts.arena_report import WindowBreakdown
from v4t.llm.gateway import LlmGateway


class TestWindowBreakdownSchema:
    """Test WindowBreakdown Pydantic schema validation."""

    def test_valid_breakdown(self) -> None:
        """Valid breakdown with all required fields passes validation."""
        data = {
            "window_story": "A" * 150,
            "what_worked": ["item1", "item2", "item3"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
            "key_takeaway": "Key lesson learned",
        }
        breakdown = WindowBreakdown.model_validate(data)
        assert breakdown.window_story == "A" * 150
        assert len(breakdown.what_worked) == 3

    def test_missing_required_field(self) -> None:
        """Missing required field raises ValidationError."""
        data = {
            "window_story": "A" * 150,
            "what_worked": ["item1", "item2", "item3"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
        }
        with pytest.raises(ValidationError, match="key_takeaway"):
            WindowBreakdown.model_validate(data)

    def test_window_story_too_short(self) -> None:
        """window_story below 150 chars raises ValidationError."""
        data = {
            "window_story": "Too short",
            "what_worked": ["item1", "item2", "item3"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
            "key_takeaway": "Key lesson",
        }
        with pytest.raises(ValidationError, match="at least 150 characters"):
            WindowBreakdown.model_validate(data)

    def test_window_story_too_long(self) -> None:
        """window_story above 250 chars raises ValidationError."""
        data = {
            "window_story": "A" * 251,
            "what_worked": ["item1", "item2", "item3"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
            "key_takeaway": "Key lesson",
        }
        with pytest.raises(ValidationError, match="at most 250 characters"):
            WindowBreakdown.model_validate(data)

    def test_list_too_few_items(self) -> None:
        """List with fewer than 3 items raises ValidationError."""
        data = {
            "window_story": "A" * 150,
            "what_worked": ["item1", "item2"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
            "key_takeaway": "Key lesson",
        }
        with pytest.raises(ValidationError, match="at least 3 items"):
            WindowBreakdown.model_validate(data)

    def test_list_too_many_items(self) -> None:
        """List with more than 5 items raises ValidationError."""
        data = {
            "window_story": "A" * 150,
            "what_worked": ["item1", "item2", "item3", "item4", "item5", "item6"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
            "key_takeaway": "Key lesson",
        }
        with pytest.raises(ValidationError, match="at most 5 items"):
            WindowBreakdown.model_validate(data)

    def test_extra_fields_forbidden(self) -> None:
        """Extra fields raise ValidationError due to extra='forbid'."""
        data = {
            "window_story": "A" * 150,
            "what_worked": ["item1", "item2", "item3"],
            "what_didnt_work": ["item1", "item2", "item3"],
            "improvement_areas": ["item1", "item2", "item3"],
            "key_takeaway": "Key lesson",
            "extra_field": "not allowed",
        }
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            WindowBreakdown.model_validate(data)


class TestFallbackWindowBreakdown:
    """Test _build_fallback_window_breakdown function."""

    def test_normal_window(self) -> None:
        """Normal window with trades generates metric-based breakdown."""
        result = _build_fallback_window_breakdown(
            return_pct=5.2, sharpe_ratio=1.3, num_trades=10, win_rate_pct=65.0
        )
        assert "10 trades" in result["window_story"]
        assert "5.20%" in result["window_story"]
        assert "1.30" in result["window_story"]
        assert "65.0%" in result["window_story"]
        assert len(result["what_worked"]) == 3
        assert len(result["what_didnt_work"]) == 3
        assert len(result["improvement_areas"]) == 3
        assert "key_takeaway" in result

    def test_empty_window(self) -> None:
        """Empty window (0 trades) generates encouraging discipline message."""
        result = _build_fallback_window_breakdown(
            return_pct=None, sharpe_ratio=None, num_trades=0, win_rate_pct=None
        )
        assert "keeping calm" in result["window_story"]
        assert "discipline" in result["window_story"].lower()
        assert "Maintained discipline" in result["what_worked"]
        assert len(result["what_worked"]) == 3
        assert len(result["what_didnt_work"]) == 3
        assert len(result["improvement_areas"]) == 3

    def test_none_values_handled(self) -> None:
        """None values in metrics are handled gracefully."""
        result = _build_fallback_window_breakdown(
            return_pct=None, sharpe_ratio=None, num_trades=5, win_rate_pct=None
        )
        assert "5 trades" in result["window_story"]
        assert "0.00%" in result["window_story"]
        assert "0.00" in result["window_story"]
        assert "0.0%" in result["window_story"]


class TestCallWindowBreakdown:
    """Test LlmGateway.call_window_breakdown method."""

    def test_stub_mode_returns_fallback(self, db_session: Session) -> None:
        """Stub mode returns fallback breakdown immediately."""
        gateway = LlmGateway()
        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "test",
        }

        call_id, breakdown, used_fallback = gateway.call_window_breakdown(
            db_session,
            submission_id=uuid4(),
            window_code="W1",
            observed_at=datetime.now(UTC),
            model_key="stub",
            system_prompt="test",
            user_prompt="test",
            fallback_breakdown=fallback,
        )

        assert isinstance(call_id, UUID)
        assert breakdown == fallback
        assert used_fallback is True

    @patch("v4t.llm.gateway.call_with_retry")
    def test_successful_llm_call(self, mock_retry: MagicMock, db_session: Session) -> None:
        """Successful LLM call returns parsed breakdown."""
        valid_response = {
            "window_story": "B" * 150,
            "what_worked": ["x", "y", "z"],
            "what_didnt_work": ["a", "b", "c"],
            "improvement_areas": ["d", "e", "f"],
            "key_takeaway": "success",
        }

        mock_retry.return_value = {
            "choices": [{"message": {"content": json.dumps(valid_response)}}],
            "usage": {"total_tokens": 100},
        }

        gateway = LlmGateway()
        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            call_id, breakdown, used_fallback = gateway.call_window_breakdown(
                db_session,
                submission_id=uuid4(),
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        assert isinstance(call_id, UUID)
        assert breakdown == valid_response
        assert used_fallback is False

    @patch("v4t.llm.gateway.call_with_retry")
    def test_validation_error_returns_fallback(
        self, mock_retry: MagicMock, db_session: Session
    ) -> None:
        """Validation error on LLM response returns fallback."""
        invalid_response = {
            "window_story": "Too short",
            "what_worked": ["x"],
            "what_didnt_work": ["a"],
            "improvement_areas": ["d"],
            "key_takeaway": "invalid",
        }

        mock_retry.return_value = {
            "choices": [{"message": {"content": json.dumps(invalid_response)}}],
            "usage": {"total_tokens": 100},
        }

        gateway = LlmGateway()
        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            call_id, breakdown, used_fallback = gateway.call_window_breakdown(
                db_session,
                submission_id=uuid4(),
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        assert isinstance(call_id, UUID)
        assert breakdown == fallback
        assert used_fallback is True

    @patch("v4t.llm.gateway.call_with_retry")
    def test_timeout_returns_fallback(self, mock_retry: MagicMock, db_session: Session) -> None:
        """Timeout on LLM call returns fallback."""
        mock_retry.side_effect = TimeoutError("Request timeout")

        gateway = LlmGateway()
        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            call_id, breakdown, used_fallback = gateway.call_window_breakdown(
                db_session,
                submission_id=uuid4(),
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        assert isinstance(call_id, UUID)
        assert breakdown == fallback
        assert used_fallback is True


class TestCircuitBreaker:
    """Test circuit breaker and retry logic."""

    @patch("v4t.llm.gateway.call_with_retry")
    def test_circuit_breaker_opens_after_5_failures(
        self, mock_retry: MagicMock, db_session: Session
    ) -> None:
        """Circuit breaker opens after 5 consecutive failures."""
        mock_retry.side_effect = Exception("LLM error")

        gateway = LlmGateway()
        submission_id = uuid4()
        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            for i in range(5):
                gateway.call_window_breakdown(
                    db_session,
                    submission_id=submission_id,
                    window_code=f"W{i}",
                    observed_at=datetime.now(UTC),
                    model_key="test-model",
                    system_prompt="test",
                    user_prompt="test",
                    fallback_breakdown=fallback,
                )

        assert gateway._window_breakdown_circuit[submission_id][0] == 5
        assert gateway._window_breakdown_circuit[submission_id][1] is not None

    @patch("v4t.llm.gateway.call_with_retry")
    def test_circuit_breaker_blocks_calls_when_open(
        self, mock_retry: MagicMock, db_session: Session
    ) -> None:
        """Circuit breaker blocks calls when open."""
        gateway = LlmGateway()
        submission_id = uuid4()
        gateway._window_breakdown_circuit[submission_id] = (5, time.perf_counter())

        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            _call_id, _breakdown, used_fallback = gateway.call_window_breakdown(
                db_session,
                submission_id=submission_id,
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        assert used_fallback is True
        assert mock_retry.call_count == 0

    @patch("v4t.llm.gateway.call_with_retry")
    def test_circuit_breaker_resets_after_timeout(
        self, mock_retry: MagicMock, db_session: Session
    ) -> None:
        """Circuit breaker resets after 60s timeout."""
        gateway = LlmGateway()
        submission_id = uuid4()
        gateway._window_breakdown_circuit[submission_id] = (5, time.perf_counter() - 61.0)

        valid_response = {
            "window_story": "B" * 150,
            "what_worked": ["x", "y", "z"],
            "what_didnt_work": ["a", "b", "c"],
            "improvement_areas": ["d", "e", "f"],
            "key_takeaway": "success",
        }

        mock_retry.return_value = {
            "choices": [{"message": {"content": json.dumps(valid_response)}}],
            "usage": {"total_tokens": 100},
        }

        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            _call_id, _breakdown, _used_fallback = gateway.call_window_breakdown(
                db_session,
                submission_id=submission_id,
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        assert gateway._window_breakdown_circuit[submission_id][1] is None
        assert gateway._window_breakdown_circuit[submission_id][0] == 0
        assert mock_retry.call_count == 1

    @patch("v4t.llm.gateway.call_with_retry")
    def test_success_resets_failure_counter(
        self, mock_retry: MagicMock, db_session: Session
    ) -> None:
        """Successful call resets failure counter."""
        gateway = LlmGateway()
        submission_id = uuid4()
        gateway._window_breakdown_circuit[submission_id] = (3, None)

        valid_response = {
            "window_story": "B" * 150,
            "what_worked": ["x", "y", "z"],
            "what_didnt_work": ["a", "b", "c"],
            "improvement_areas": ["d", "e", "f"],
            "key_takeaway": "success",
        }

        mock_retry.return_value = {
            "choices": [{"message": {"content": json.dumps(valid_response)}}],
            "usage": {"total_tokens": 100},
        }

        fallback = {
            "window_story": "A" * 150,
            "what_worked": ["a", "b", "c"],
            "what_didnt_work": ["d", "e", "f"],
            "improvement_areas": ["g", "h", "i"],
            "key_takeaway": "fallback",
        }

        with (
            patch.object(gateway, "_use_stub", return_value=False),
            patch.object(gateway, "_model_allowed", return_value=True),
            patch.object(gateway, "_resolve_transport", return_value=("http://test", "key")),
        ):
            gateway.call_window_breakdown(
                db_session,
                submission_id=submission_id,
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        assert gateway._window_breakdown_circuit[submission_id][0] == 0
