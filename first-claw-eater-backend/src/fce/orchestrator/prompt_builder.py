from __future__ import annotations

from datetime import datetime
from typing import Any

import pystache


def render_mustache(*, template: str, context: dict[str, Any]) -> str:
    # pystache renders missing keys as empty strings; that's fine for MVP.
    return pystache.render(template, context)


def build_default_prompt_context(
    *,
    market_id: str,
    tick_time: datetime,
    closes: list[str],
    features: dict[str, Any] | None,
    sentiment_summaries: list[dict[str, Any]],
    portfolio: dict[str, Any],
    memory: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "market_id": market_id,
        "tick_time": tick_time.isoformat(),
        "closes": closes,
        "features": features,
        "sentiment_summaries": sentiment_summaries,
        "portfolio": portfolio,
        "memory": memory,
    }
