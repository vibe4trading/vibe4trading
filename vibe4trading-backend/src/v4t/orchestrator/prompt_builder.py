from __future__ import annotations

from datetime import datetime
from typing import Any, cast


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split())


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

    style = (style_text or "").strip()
    lines.append("User strategy prompt:")
    lines.append(style if style else "(none)")

    lines.append("")
    lines.append("Market:")
    lines.append(f"market_id={market_id}")
    lines.append(f"tick_time={tick_time}")

    if "latest_price" in inc:
        latest_price = context.get("latest_price")
        lines.append("")
        lines.append("Latest price:")
        if isinstance(latest_price, dict):
            latest_price_map = cast(dict[str, Any], latest_price)
            lines.append(f"- observed_at={latest_price_map.get('observed_at')}")
            lines.append(f"- price={latest_price_map.get('price')}")
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
            for raw_bar in cast(list[Any], bars):
                if not isinstance(raw_bar, dict):
                    continue
                bar = cast(dict[str, Any], raw_bar)
                bar_start = bar.get("bar_start")
                bar_end = bar.get("bar_end")
                o = bar.get("o")
                h = bar.get("h")
                l = bar.get("l")
                c = bar.get("c")
                volume_base = bar.get("volume_base")
                volume_quote = bar.get("volume_quote")
                lines.append(
                    f"- {bar_start} -> {bar_end} O={o} H={h} L={l} C={c} volume_base={volume_base} volume_quote={volume_quote}"
                )
        else:
            lines.append("(none)")

    if "closes" in inc:
        closes = context.get("closes")
        lines.append("")
        lines.append("Recent closes (oldest->newest):")
        if isinstance(closes, list) and closes:
            for close in cast(list[Any], closes):
                lines.append(f"- {close}")
        else:
            lines.append("(none)")

    if "features" in inc:
        features = context.get("features")
        lines.append("")
        lines.append("Features:")
        if isinstance(features, dict) and features:
            feature_map = cast(dict[str, Any], features)
            for key in sorted(feature_map.keys()):
                lines.append(f"- {key}={feature_map.get(key)}")
        else:
            lines.append("(none)")

    if "portfolio" in inc:
        portfolio = context.get("portfolio")
        lines.append("")
        lines.append("Portfolio:")
        if isinstance(portfolio, dict) and portfolio:
            portfolio_map = cast(dict[str, Any], portfolio)
            for key in (
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
                if key in portfolio_map:
                    lines.append(f"- {key}={portfolio_map.get(key)}")
        else:
            lines.append("(none)")

    if "sentiment" in inc:
        sentiment_summaries = context.get("sentiment_summaries")
        lines.append("")
        lines.append("Recent sentiment summaries:")
        if isinstance(sentiment_summaries, list) and sentiment_summaries:
            for raw_summary in cast(list[Any], sentiment_summaries):
                if not isinstance(raw_summary, dict):
                    continue
                sentiment_item = cast(dict[str, Any], raw_summary)
                item_time = sentiment_item.get("item_time")
                summary_text = _compact_text(sentiment_item.get("summary_text"))
                tags = sentiment_item.get("tags")
                score = sentiment_item.get("sentiment_score")
                source = _compact_text(sentiment_item.get("source"))
                item_kind = _compact_text(sentiment_item.get("item_kind"))
                external_id = _compact_text(sentiment_item.get("external_id"))
                url = _compact_text(sentiment_item.get("url"))
                raw_metadata = sentiment_item.get("metadata")
                metadata = (
                    cast(dict[str, Any], raw_metadata) if isinstance(raw_metadata, dict) else {}
                )
                metadata_str = " ".join(
                    f"{key}={metadata[key]}"
                    for key in sorted(metadata.keys())
                    if metadata.get(key) is not None
                )
                text_label = "full_text" if sentiment_item.get("uses_full_text") else "summary"
                tag_str = (
                    ",".join(tag for tag in cast(list[Any], tags) if isinstance(tag, str))
                    if isinstance(tags, list)
                    else ""
                )
                score_str = f" score={score}" if score is not None else ""
                details = [
                    f"source={source}" if source else "",
                    f"kind={item_kind}" if item_kind else "",
                    f"external_id={external_id}" if external_id else "",
                    f"url={url}" if url else "",
                    metadata_str,
                ]
                detail_str = " ".join(part for part in details if part)
                detail_suffix = f" {detail_str}" if detail_str else ""
                lines.append(
                    f"- {item_time} {text_label}={summary_text}{detail_suffix} tags=[{tag_str}]{score_str}"
                )
        else:
            lines.append("(none)")

    if "memory" in inc:
        memory = context.get("memory")
        lines.append("")
        lines.append("Recent decisions:")
        if isinstance(memory, list) and memory:
            for raw_item in cast(list[Any], memory):
                if not isinstance(raw_item, dict):
                    continue
                memory_item = cast(dict[str, Any], raw_item)
                accepted = memory_item.get("accepted")
                targets = memory_item.get("targets")
                target = memory_item.get("target")
                mode = memory_item.get("mode")
                leverage = memory_item.get("leverage")
                confidence = memory_item.get("confidence")
                reject_reason = memory_item.get("reject_reason")
                key_signals = memory_item.get("key_signals")
                rationale = memory_item.get("rationale")
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
    lines.append(
        '{"schema_version":2,"target":0.5,"mode":"spot","leverage":1,'
        '"stop_loss_pct":5.0,"take_profit_pct":10.0,'
        '"confidence":0.6,"key_signals":["..."],"rationale":"..."}'
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
