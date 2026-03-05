from __future__ import annotations

import json


def extract_first_json_object(text: str) -> dict:
    """Extract and parse the first JSON object from a string.

    Models sometimes wrap JSON in markdown fences or include pre/post text.
    This parser finds the first balanced {...} region and json.loads it.
    """

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
                return json.loads(candidate)

    raise ValueError("Unbalanced JSON braces in response")
