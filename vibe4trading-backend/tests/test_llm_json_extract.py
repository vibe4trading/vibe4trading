from __future__ import annotations

import pytest

from v4t.llm.json_extract import extract_first_json_object, extract_first_json_object_text


def test_extract_plain_json() -> None:
    text = '{"key": "value"}'
    result = extract_first_json_object(text)
    assert result == {"key": "value"}


def test_extract_json_with_prefix() -> None:
    text = 'Here is the result: {"key": "value"}'
    result = extract_first_json_object(text)
    assert result == {"key": "value"}


def test_extract_json_text_returns_candidate() -> None:
    text = 'prefix {"key": "value"} suffix'
    obj, candidate = extract_first_json_object_text(text)
    assert obj == {"key": "value"}
    assert candidate == '{"key": "value"}'


def test_extract_json_with_markdown_fence() -> None:
    text = '```json\n{"key": "value"}\n```'
    result = extract_first_json_object(text)
    assert result == {"key": "value"}


def test_extract_nested_json() -> None:
    text = '{"outer": {"inner": "value"}}'
    result = extract_first_json_object(text)
    assert result == {"outer": {"inner": "value"}}


def test_extract_json_with_string_containing_braces() -> None:
    text = '{"message": "This has {braces} in it"}'
    result = extract_first_json_object(text)
    assert result == {"message": "This has {braces} in it"}


def test_extract_empty_text_fails() -> None:
    with pytest.raises(ValueError, match="Empty LLM response"):
        extract_first_json_object("")


def test_extract_no_json_fails() -> None:
    with pytest.raises(ValueError, match="No JSON object start"):
        extract_first_json_object("No JSON here")


def test_extract_unbalanced_braces_fails() -> None:
    with pytest.raises(ValueError, match="Unbalanced JSON braces"):
        extract_first_json_object('{"key": "value"')
