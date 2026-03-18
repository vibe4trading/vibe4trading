from __future__ import annotations

import json
from typing import Any, cast


def extract_first_json_object_text(text: str) -> tuple[dict[str, Any], str]:
    if not text:
        raise ValueError("Empty LLM response")

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object start '{' found")

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as e:
                    preview = candidate[:100]
                    raise ValueError(f"Extracted text is not valid JSON: {preview}") from e
                if not isinstance(parsed, dict):
                    raise ValueError("Expected a JSON object")
                return cast(dict[str, Any], parsed), candidate

    raise ValueError("Unbalanced JSON braces in response")


def extract_first_json_object(text: str) -> dict[str, Any]:
    obj, _candidate = extract_first_json_object_text(text)
    return obj
