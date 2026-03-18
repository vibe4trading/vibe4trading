from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from v4t.llm.gateway import LlmGateway


class TestWindowBreakdownRespectsRetryConfig:
    """Test that call_window_breakdown respects V4T_LLM_MAX_RETRIES setting."""

    @patch("v4t.llm.gateway.call_with_retry")
    def test_window_breakdown_respects_retry_setting(
        self, mock_retry: MagicMock, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """call_window_breakdown respects V4T_LLM_MAX_RETRIES environment variable."""
        monkeypatch.setenv("V4T_LLM_MAX_RETRIES", "5")

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

        from v4t.settings import get_settings

        get_settings.cache_clear()
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
            gateway.call_window_breakdown(
                db_session,
                submission_id=uuid4(),
                window_code="W1",
                observed_at=datetime.now(UTC),
                model_key="test-model",
                system_prompt="test",
                user_prompt="test",
                fallback_breakdown=fallback,
            )

        mock_retry.assert_called_once()
        call_kwargs = mock_retry.call_args.kwargs
        assert call_kwargs["max_retries"] == 5
