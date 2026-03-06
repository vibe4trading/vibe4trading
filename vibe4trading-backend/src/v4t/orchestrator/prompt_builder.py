from __future__ import annotations

from datetime import datetime
from typing import Any


def _decision_schema_version(context: dict[str, Any]) -> int:
    raw = context.get("decision_schema_version", 1)
    try:
        return int(raw)
    except Exception:
        return 1


def _normalize_includes(includes: list[str] | None) -> set[str]:
    if not includes:
        return set()

    out: set[str] = set()
    for raw in includes:
        k = (raw or "").strip().lower()
        if not k:
            continue

        if k == "raw":
            out.add("closes")
            continue
        if k == "sentiment_context":
            out.add("sentiment")
            continue

        if k in {"sentiment_summaries", "sentiment_summary", "sentiment_items"}:
            out.add("sentiment")
            continue
        if k in {"ohlcv_bars", "bars", "ohlcv_full_bars"}:
            out.add("ohlcv")
            continue
        if k in {"latest", "price", "latestprice"}:
            out.add("latest_price")
            continue

        out.add(k)

    return out


def render_user_prompt(
    *,
    style_text: str,
    context: dict[str, Any],
    include: list[str] | None,
) -> str:
    inc = _normalize_includes(include)

    market_id = str(context.get("market_id") or "")
    tick_time = str(context.get("tick_time") or "")

    lines: list[str] = []
    decision_schema_version = _decision_schema_version(context)

    style = (style_text or "").strip()
    lines.append("User strategy prompt:")
    lines.append(style if style else "(none)")

    lines.append("")
    lines.append("Market:")
    lines.append(f"market_id={market_id}")
    lines.append(f"tick_time={tick_time}")

    if "latest_price" in inc:
        lp = context.get("latest_price")
        lines.append("")
        lines.append("Latest price:")
        if isinstance(lp, dict):
            lines.append(f"- observed_at={lp.get('observed_at')}")
            lines.append(f"- price={lp.get('price')}")
        else:
            lines.append("(none)")

    if "ohlcv" in inc:
        bars = context.get("ohlcv_bars")
        timeframe = str(context.get("timeframe") or "")
        lines.append("")
        header = "Recent OHLCV bars"
        if timeframe:
            header += f" (timeframe={timeframe})"
        header += " (oldest->newest):"
        lines.append(header)
        if isinstance(bars, list) and bars:
            for b in bars:
                if not isinstance(b, dict):
                    continue
                bar_start = b.get("bar_start")
                bar_end = b.get("bar_end")
                o = b.get("o")
                h = b.get("h")
                l = b.get("l")
                c = b.get("c")
                vb = b.get("volume_base")
                vq = b.get("volume_quote")
                lines.append(
                    f"- {bar_start} -> {bar_end} O={o} H={h} L={l} C={c} volume_base={vb} volume_quote={vq}"
                )
        else:
            lines.append("(none)")

    if "closes" in inc:
        closes = context.get("closes")
        lines.append("")
        lines.append("Recent closes (oldest->newest):")
        if isinstance(closes, list) and closes:
            for c in closes:
                lines.append(f"- {c}")
        else:
            lines.append("(none)")

    if "features" in inc:
        features = context.get("features")
        lines.append("")
        lines.append("Features:")
        if isinstance(features, dict) and features:
            for k in sorted(features.keys()):
                lines.append(f"- {k}={features.get(k)}")
        else:
            lines.append("(none)")

    if "portfolio" in inc:
        portfolio = context.get("portfolio")
        lines.append("")
        lines.append("Portfolio:")
        if isinstance(portfolio, dict) and portfolio:
            if decision_schema_version == 2:
                for k in (
                    "equity_quote",
                    "cash_quote",
                    "position_mode",
                    "position_direction",
                    "position_qty_base",
                    "position_leverage",
                    "entry_price",
                    "current_price",
                    "liquidation_price",
                    "unrealized_pnl",
                    "unrealized_pnl_pct",
                    "funding_cost_accumulated",
                    "stop_loss_price",
                    "take_profit_price",
                ):
                    if k in portfolio:
                        lines.append(f"- {k}={portfolio.get(k)}")
            else:
                for k in ("equity_quote", "cash_quote", "position_qty_base", "price"):
                    if k in portfolio:
                        lines.append(f"- {k}={portfolio.get(k)}")
        else:
            lines.append("(none)")

    if "sentiment" in inc:
        ss = context.get("sentiment_summaries")
        lines.append("")
        lines.append("Recent sentiment summaries:")
        if isinstance(ss, list) and ss:
            for s in ss:
                if not isinstance(s, dict):
                    continue
                item_time = s.get("item_time")
                summary_text = s.get("summary_text")
                tags = s.get("tags")
                score = s.get("sentiment_score")
                tag_str = ",".join(tags) if isinstance(tags, list) else ""
                score_str = f" score={score}" if score is not None else ""
                lines.append(f"- {item_time} {summary_text} tags=[{tag_str}]{score_str}")
        else:
            lines.append("(none)")

    if "memory" in inc:
        mem = context.get("memory")
        lines.append("")
        lines.append("Recent decisions:")
        if isinstance(mem, list) and mem:
            for m in mem:
                if not isinstance(m, dict):
                    continue
                accepted = m.get("accepted")
                targets = m.get("targets")
                target = m.get("target")
                mode = m.get("mode")
                leverage = m.get("leverage")
                confidence = m.get("confidence")
                next_check = m.get("next_check_seconds")
                reject_reason = m.get("reject_reason")
                key_signals = m.get("key_signals")
                rationale = m.get("rationale")
                lines.append(
                    "- accepted="
                    + str(accepted)
                    + " targets="
                    + str(targets)
                    + " target="
                    + str(target)
                    + " mode="
                    + str(mode)
                    + " leverage="
                    + str(leverage)
                    + " confidence="
                    + str(confidence)
                    + " next_check_seconds="
                    + str(next_check)
                    + " reject_reason="
                    + str(reject_reason)
                    + " key_signals="
                    + str(key_signals)
                )
                if rationale:
                    lines.append(f"  {rationale}")
        else:
            lines.append("(none)")

    lines.append("")
    lines.append("Return ONLY a JSON object like:")
    if decision_schema_version == 2:
        lines.append(
            '{"schema_version":2,"target":0.5,"mode":"spot","leverage":1,'
            '"stop_loss_pct":5.0,"take_profit_pct":10.0,"next_check_seconds":3600,'
            '"confidence":0.6,"key_signals":["..."],"rationale":"..."}'
        )
    else:
        lines.append(
            '{"schema_version":1,"targets":{"'
            + (market_id or "<market_id>")
            + '":0.25},"next_check_seconds":600,"confidence":0.6,"key_signals":["..."],"rationale":"..."}'
        )

    return "\n".join(lines).strip() + "\n"


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
