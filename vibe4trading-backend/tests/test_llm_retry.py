from __future__ import annotations

import json
from unittest.mock import Mock, patch

import httpx
import pytest

from v4t.llm.retry import post_json_request


def test_decode_response_handles_invalid_json() -> None:
    """_decode_response raises ValueError with clear message for non-JSON responses."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    mock_response.text = "<html><body>Error 500</body></html>"
    mock_response.raise_for_status.return_value = None

    mock_client = Mock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    with patch("v4t.llm.retry.submit_llm_request") as mock_submit:
        mock_submit.side_effect = lambda fn, queue_priority: fn()

        with pytest.raises(ValueError, match="Response body is not valid JSON"):
            post_json_request(
                url="http://test.local/v1/chat",
                headers={},
                req={},
                timeout_seconds=1.0,
                client=mock_client,
            )
