#!/usr/bin/env python3
"""Backfill sentiment.item_summary events using a self-contained LLM client.

No v4t.* imports required. Only needs: sqlalchemy, httpx, psycopg2.

Usage:
    python backfill_sentiment_summaries.py \
        --database-url 'postgresql+psycopg2://...' \
        --llm-base-url http://new-api.opensakura-infra-llm:3000/v1 \
        --llm-api-key sk-xxx \
        --model-key glm-4.7-flash

    python backfill_sentiment_summaries.py --dry-run
    python backfill_sentiment_summaries.py --dataset-id <uuid>
    python backfill_sentiment_summaries.py --no-llm
    python backfill_sentiment_summaries.py --budget 500 --delay 0.1

Environment (fallbacks when flags omitted):
    V4T_DATABASE_URL
    V4T_LLM_BASE_URL
    V4T_LLM_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

SYSTEM_PROMPT = (
    "You summarize a single news/social item for a trading agent. "
    "Return 1-2 plain-text sentences. No markdown, no bullet list."
)

INSERT_SUMMARY_EVENT = text("""
    INSERT INTO events (
        event_id, event_type, source, schema_version,
        observed_at, event_time, dedupe_key,
        dataset_id, run_id, payload, raw_payload, ingested_at
    ) VALUES (
        :event_id, 'sentiment.item_summary', 'backfill.sentiment_summaries', 1,
        :observed_at, :event_time, :dedupe_key,
        :dataset_id, NULL, CAST(:payload AS jsonb), CAST(:raw_payload AS jsonb), :ingested_at
    )
    ON CONFLICT (dataset_id, event_type, dedupe_key) DO NOTHING
""")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill sentiment.item_summary events (self-contained)"
    )
    p.add_argument("--dataset-id", type=str, default=None)
    p.add_argument("--model-key", type=str, default="glm-4.7-flash")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--budget", type=int, default=200)
    p.add_argument("--delay", type=float, default=0.05)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--database-url", type=str, default=None)
    p.add_argument("--llm-base-url", type=str, default=None)
    p.add_argument("--llm-api-key", type=str, default=None)
    return p.parse_args()


def _snippet(txt: str, max_len: int = 240) -> str:
    s = " ".join((txt or "").split())
    if len(s) > max_len:
        s = s[:max_len].rstrip() + "..."
    return s


def _build_tags(payload: dict[str, Any], raw_payload: dict[str, Any] | None) -> list[str]:
    tags: list[str] = []
    source = payload.get("source", "")
    if source:
        tags.append(source)
    if raw_payload:
        handle = raw_payload.get("handle", "")
        if handle:
            tags.append(handle)
    return tags


def _parse_item_time(item_time_raw: Any, fallback: datetime) -> datetime:
    if isinstance(item_time_raw, str):
        dt = datetime.fromisoformat(item_time_raw)
    elif isinstance(item_time_raw, datetime):
        dt = item_time_raw
    else:
        dt = fallback
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _call_llm(
    client: httpx.Client,
    *,
    url: str,
    model_key: str,
    item_text: str,
    item_url: str | None,
    timeout: float,
    max_retries: int,
) -> str:
    user_content = (f"url={item_url}\n\n" if item_url else "") + item_text

    body = {
        "model": model_key,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
    }

    last_err: Exception | None = None
    for attempt in range(1 + max_retries):
        try:
            resp = client.post(url, json=body, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("LLM response missing choices")
            msg: dict[str, Any] = choices[0]["message"]
            content = msg.get("content")
            # Reasoning models (e.g. glm-4.7-flash) may put all output in
            # the "reasoning" field and return content=null.  Fall back to
            # the raw reasoning text, stripping markdown formatting.
            if content is None:
                reasoning = msg.get("reasoning") or ""
                if not reasoning and isinstance(msg.get("reasoning_details"), list):
                    details: list[dict[str, Any]] = msg["reasoning_details"]
                    reasoning = " ".join(d.get("text", "") for d in details)
                content = reasoning.strip() if reasoning else None
            if not content:
                raise ValueError("LLM returned empty content and no reasoning")
            return content
        except (httpx.HTTPStatusError, httpx.ReadTimeout, httpx.ConnectError) as exc:
            last_err = exc
            if attempt < max_retries:
                backoff = 2**attempt
                time.sleep(backoff)
                continue
            break
        except Exception as exc:
            last_err = exc
            break

    return f"(error) {last_err!r}"


def _find_datasets_missing_summaries(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT
                d.dataset_id, d.source, d.params::text AS params,
                COUNT(CASE WHEN e.event_type = 'sentiment.item' THEN 1 END) AS item_count,
                COUNT(CASE WHEN e.event_type = 'sentiment.item_summary' THEN 1 END) AS summary_count
            FROM datasets d
            LEFT JOIN events e ON e.dataset_id = d.dataset_id
            WHERE d.category = 'sentiment' AND d.status = 'ready'
            GROUP BY d.dataset_id, d.source, d.params::text
            HAVING COUNT(CASE WHEN e.event_type = 'sentiment.item' THEN 1 END) > 
                   COUNT(CASE WHEN e.event_type = 'sentiment.item_summary' THEN 1 END)
            ORDER BY d.created_at
        """)
    ).fetchall()
    return [
        {
            "dataset_id": r[0],
            "source": r[1],
            "params": r[2],
            "item_count": r[3],
            "summary_count": r[4],
        }
        for r in rows
    ]


def _load_pending_sentiment_items(session: Session, dataset_id: UUID) -> list[dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT i.observed_at, i.event_time, i.dedupe_key, i.payload, i.raw_payload
            FROM events i
            WHERE i.dataset_id = :did
              AND i.event_type = 'sentiment.item'
              AND NOT EXISTS (
                  SELECT 1 FROM events s
                  WHERE s.dataset_id = :did
                    AND s.event_type = 'sentiment.item_summary'
                    AND s.dedupe_key = i.dedupe_key
              )
            ORDER BY i.observed_at
        """),
        {"did": str(dataset_id)},
    ).fetchall()
    return [
        {
            "observed_at": r[0],
            "event_time": r[1],
            "dedupe_key": r[2],
            "payload": r[3],
            "raw_payload": r[4],
        }
        for r in rows
    ]


def _insert_summary_event(
    session: Session,
    *,
    dataset_id: UUID,
    observed_at: datetime,
    event_time: datetime | None,
    dedupe_key: str,
    summary_payload: dict[str, Any],
    raw_payload: dict[str, Any] | None,
) -> None:
    session.execute(
        INSERT_SUMMARY_EVENT,
        {
            "event_id": str(uuid4()),
            "observed_at": observed_at,
            "event_time": event_time,
            "dedupe_key": dedupe_key,
            "dataset_id": str(dataset_id),
            "payload": json.dumps(summary_payload, default=str),
            "raw_payload": json.dumps(raw_payload, default=str) if raw_payload else None,
            "ingested_at": datetime.now(UTC),
        },
    )


def _backfill_dataset(
    session: Session,
    *,
    dataset_id: UUID,
    http_client: httpx.Client | None,
    llm_url: str,
    model_key: str,
    budget: int,
    delay: float,
    timeout: float,
    max_retries: int,
    no_llm: bool,
    batch_size: int,
    dry_run: bool,
) -> tuple[int, int, int]:
    items = _load_pending_sentiment_items(session, dataset_id)
    if not items:
        return 0, 0, 0

    llm_calls = 0
    fallback_count = 0
    inserted = 0

    for idx, item in enumerate(items):
        payload: dict[str, Any] = item["payload"]
        raw_payload: dict[str, Any] | None = item["raw_payload"]
        observed_at: datetime = item["observed_at"]
        event_time: datetime | None = item["event_time"]
        dedupe_key: str = item["dedupe_key"]

        item_text: str = payload.get("text", "")
        item_url: str | None = payload.get("url")
        item_time = _parse_item_time(payload.get("item_time"), observed_at)
        item_kind_raw: str = payload.get("item_kind", "x_post")
        external_id: str = payload.get("external_id", "")
        source: str = payload.get("source", "tweets")

        tags = _build_tags(payload, raw_payload)

        summary_text: str

        if no_llm or llm_calls >= budget:
            summary_text = _snippet(item_text) if item_text else "(empty)"
            fallback_count += 1
        else:
            if dry_run:
                llm_calls += 1
                continue

            assert http_client is not None
            summary_text = _call_llm(
                http_client,
                url=llm_url,
                model_key=model_key,
                item_text=item_text,
                item_url=item_url,
                timeout=timeout,
                max_retries=max_retries,
            )
            llm_calls += 1

            if delay > 0:
                time.sleep(delay)

        if dry_run:
            fallback_count += 1
            continue

        summary_payload = {
            "source": source,
            "external_id": external_id,
            "item_time": item_time.isoformat(),
            "item_kind": item_kind_raw,
            "summary_text": summary_text,
            "tags": tags,
            "sentiment_score": None,
            "llm_call_id": None,
        }

        _insert_summary_event(
            session,
            dataset_id=dataset_id,
            observed_at=item_time,
            event_time=event_time,
            dedupe_key=dedupe_key,
            summary_payload=summary_payload,
            raw_payload=raw_payload,
        )
        inserted += 1

        if inserted % batch_size == 0:
            session.commit()
            pct = (idx + 1) / len(items) * 100
            print(
                f"  ... {idx + 1}/{len(items)} ({pct:.0f}%) — LLM: {llm_calls}, fallback: {fallback_count}"
            )

    if not dry_run:
        session.commit()

    return len(items), llm_calls, fallback_count


def main() -> None:
    args = _parse_args()

    db_url = args.database_url or os.environ.get("V4T_DATABASE_URL")
    if not db_url:
        print("Error: set V4T_DATABASE_URL or pass --database-url")
        sys.exit(1)

    llm_base_url = args.llm_base_url or os.environ.get("V4T_LLM_BASE_URL", "")
    llm_api_key = args.llm_api_key or os.environ.get("V4T_LLM_API_KEY", "")
    llm_url = f"{llm_base_url.rstrip('/')}/chat/completions" if llm_base_url else ""

    if not args.no_llm and not args.dry_run and (not llm_base_url or not llm_api_key):
        print("Error: LLM mode requires --llm-base-url and --llm-api-key (or env vars)")
        print("       Use --no-llm to skip LLM and use raw text as summaries")
        sys.exit(1)

    engine = create_engine(db_url)

    print(f"Model:   {args.model_key}")
    print(f"Budget:  {args.budget} LLM calls per dataset (rest use raw text)")
    print(f"Delay:   {args.delay}s between LLM calls")
    print(f"Timeout: {args.timeout}s per LLM call, {args.max_retries} retries")
    if args.no_llm:
        print("Mode:    no-llm (raw text as summary)")
    if args.dry_run:
        print("Mode:    DRY RUN (no writes)")
    print()

    http_client: httpx.Client | None = None
    if not args.no_llm and not args.dry_run:
        http_client = httpx.Client(headers={"Authorization": f"Bearer {llm_api_key}"})

    try:
        with Session(engine) as db:
            if args.dataset_id:
                ds_id = UUID(args.dataset_id)
                row = db.execute(
                    text("SELECT dataset_id, source FROM datasets WHERE dataset_id = :did"),
                    {"did": str(ds_id)},
                ).fetchone()
                if row is None:
                    print(f"Error: dataset_id {ds_id} not found")
                    sys.exit(1)
                datasets: list[dict[str, Any]] = [
                    {"dataset_id": ds_id, "source": row[1], "item_count": "?"}
                ]
            else:
                datasets = _find_datasets_missing_summaries(db)

            if not datasets:
                print("No datasets need backfilling.")
                return

            print(f"Found {len(datasets)} dataset(s) to process:\n")

            total_items = 0
            total_llm = 0
            total_fallback = 0

            for ds in datasets:
                ds_id = ds["dataset_id"]
                item_count = ds.get("item_count", "?")
                done_count = ds.get("summary_count", 0)
                pending = (
                    item_count - done_count
                    if isinstance(item_count, int) and isinstance(done_count, int)
                    else "?"
                )
                raw_params: Any = ds.get("params") or {}
                params: dict[str, Any] = (
                    json.loads(raw_params) if isinstance(raw_params, str) else raw_params
                ) or {}
                event_name = params.get("event_name", "")
                label = f"{event_name} ({ds['source']})" if event_name else ds["source"]

                if done_count:
                    print(
                        f"Dataset {ds_id} [{label}] — {item_count} items, {done_count} already done, {pending} pending"
                    )
                else:
                    print(f"Dataset {ds_id} [{label}] — {item_count} items")

                items, llm_count, fb_count = _backfill_dataset(
                    db,
                    dataset_id=ds_id,
                    http_client=http_client,
                    llm_url=llm_url,
                    model_key=args.model_key,
                    budget=args.budget,
                    delay=args.delay,
                    timeout=args.timeout,
                    max_retries=args.max_retries,
                    no_llm=args.no_llm,
                    batch_size=args.batch_size,
                    dry_run=args.dry_run,
                )

                total_items += items
                total_llm += llm_count
                total_fallback += fb_count

                action = "would insert" if args.dry_run else "inserted"
                print(
                    f"  Done: {items} items — LLM: {llm_count}, fallback: {fb_count} ({action})\n"
                )

            print("=" * 60)
            print(
                f"Total: {total_items} items, {total_llm} LLM summaries, {total_fallback} fallback"
            )

            if not args.dry_run:
                for ds in datasets:
                    cnt = db.execute(
                        text(
                            "SELECT COUNT(*) FROM events "
                            "WHERE dataset_id = :did AND event_type = 'sentiment.item_summary'"
                        ),
                        {"did": str(ds["dataset_id"])},
                    ).scalar()
                    print(f"  {ds['dataset_id']}: {cnt} summary events")

        print("\nDone!")
    finally:
        if http_client is not None:
            http_client.close()


if __name__ == "__main__":
    main()
