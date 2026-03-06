from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from uuid import UUID

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.api.app import create_app
from v4t.api.deps import get_db
from v4t.contracts.events import make_event
from v4t.contracts.numbers import DECIMAL_STR_RE
from v4t.contracts.payloads import (
    LlmDecisionPayload,
    MarketOHLCVPayload,
    MarketPricePayload,
    PortfolioSnapshotPayload,
    SimFillPayload,
)
from v4t.contracts.run_config import RunConfigSnapshot
from v4t.db.event_store import append_event
from v4t.db.models import (
    ArenaSubmissionRow,
    ArenaSubmissionRunRow,
    DatasetRow,
    EventRow,
    LlmCallRow,
    RunConfigSnapshotRow,
    RunRow,
)
from v4t.settings import get_settings


def _config_dict(row: RunConfigSnapshotRow) -> dict[str, Any]:
    row_any = cast(Any, row)
    value = row_any.config
    return cast(dict[str, Any], value)


def _call_prompt(call: LlmCallRow) -> dict[str, Any]:
    call_any = cast(Any, call)
    value = call_any.prompt
    return cast(dict[str, Any], value)


def _call_response_parsed(call: LlmCallRow) -> dict[str, Any] | None:
    call_any = cast(Any, call)
    value = call_any.response_parsed
    return cast(dict[str, Any] | None, value)


def _event_payload(row: EventRow) -> dict[str, Any]:
    row_any = cast(Any, row)
    value = row_any.payload
    return cast(dict[str, Any], value)


class _FakeLlmHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/chat/completions":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        payload = json.loads(body.decode("utf-8"))
        server = cast(_FakeLlmServer, self.server)
        server.requests.append(payload)

        messages = payload.get("messages", [])
        system_prompt = messages[0].get("content", "") if messages else ""

        if "single-market arena submission" in system_prompt:
            content = json.dumps(
                {
                    "archetype": "Deterministic Benchmark",
                    "overview": "Stable replayable benchmark report.",
                    "strengths": [
                        "Consistent hourly cadence",
                        "Replayable output",
                        "Linked report call",
                    ],
                    "weaknesses": [
                        "Synthetic test server",
                        "No external market latency",
                        "Single-market focus",
                    ],
                    "recommendations": [
                        "Compare future runs",
                        "Track score drift",
                        "Inspect weak windows",
                    ],
                    "best_window_reason": "Best deterministic return.",
                    "worst_window_reason": "Weakest deterministic return.",
                }
            )
        else:
            content = json.dumps(
                {
                    "schema_version": 2,
                    "target": 1.0,
                    "mode": "spot",
                    "leverage": 1,
                    "stop_loss_pct": 5.0,
                    "take_profit_pct": 10.0,
                    "next_check_seconds": 3600,
                    "confidence": 0.7,
                    "key_signals": ["deterministic_hourly_trend"],
                    "rationale": "Deterministic local test response.",
                }
            )

        response = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": payload.get("model", "test-model"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class _FakeLlmServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _FakeLlmHandler)
        self.requests: list[dict[str, Any]] = []


@contextmanager
def _fake_llm_server() -> Iterator[_FakeLlmServer]:
    server = _FakeLlmServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _seed_hourly_market_events(
    session: Session, *, dataset_id: UUID, market_id: str, start: datetime, n_hours: int
) -> None:
    base_price = 50000
    for i in range(n_hours):
        bar_start = start + timedelta(hours=i)
        bar_end = start + timedelta(hours=i + 1)
        close = str(base_price + i)
        append_event(
            session,
            ev=make_event(
                event_type="market.ohlcv",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"ohlcv:{dataset_id}:{i}",
                dataset_id=dataset_id,
                payload=MarketOHLCVPayload(
                    market_id=market_id,
                    timeframe="1h",
                    bar_start=bar_start,
                    bar_end=bar_end,
                    o=close,
                    h=str(base_price + i + 1),
                    l=str(base_price + i - 1),
                    c=close,
                ).model_dump(mode="json"),
            ),
            dedupe_scope="dataset",
        )
        append_event(
            session,
            ev=make_event(
                event_type="market.price",
                source="test",
                observed_at=bar_end,
                dedupe_key=f"price:{dataset_id}:{i}",
                dataset_id=dataset_id,
                payload=MarketPricePayload(market_id=market_id, price=close).model_dump(
                    mode="json"
                ),
            ),
            dedupe_scope="dataset",
        )
    session.commit()


@contextmanager
def _fresh_client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_tournament_e2e_uses_env_model_and_persists_replay_artifacts(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("V4T_CELERY_ALWAYS_EAGER", "1")
    monkeypatch.setenv("V4T_REPLAY_BASE_INTERVAL_SECONDS", "21600")
    monkeypatch.setenv("V4T_REPLAY_MIN_INTERVAL_SECONDS", "3600")
    monkeypatch.setenv("V4T_REPLAY_PRICE_TICK_SECONDS", "21600")
    get_settings.cache_clear()

    settings = get_settings()
    model_key = (settings.llm_model or "").strip()
    if model_key in {"", "stub"} or not settings.llm_base_url or not settings.llm_api_key:
        pytest.skip("backend env LLM is not configured")

    start = datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC)
    end = start + timedelta(hours=24)
    with _fresh_client(db_session) as client:
        public_models_res = client.get("/models")
        assert public_models_res.status_code == 200
        public_models = {row["model_key"]: row for row in public_models_res.json()}
        assert model_key in public_models

        admin_models_res = client.get("/admin/models")
        assert admin_models_res.status_code == 200
        admin_models = {row["model_key"]: row for row in admin_models_res.json()}
        assert model_key in admin_models

        dataset_res = client.post(
            "/datasets",
            json={
                "category": "spot",
                "source": "demo",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "params": {
                    "market_id": "spot:demo:BTC",
                    "base_price": 50000.0,
                },
            },
        )
        assert dataset_res.status_code == 200
        dataset_id = UUID(dataset_res.json()["dataset_id"])

        spot_dataset = db_session.get(DatasetRow, dataset_id)
        assert spot_dataset is not None
        assert spot_dataset.status == "ready"

        monkeypatch.setenv("V4T_ARENA_DATASET_IDS", str(dataset_id))
        get_settings.cache_clear()

        submission_res = client.post(
            "/arena/submissions",
            json={
                "market_id": "spot:demo:BTC",
                "model_key": model_key,
                "prompt_text": (
                    "You are trading BTC. Return ONLY valid JSON with schema_version=1, "
                    'targets={"spot:demo:BTC": number between 0 and 1}, next_check_seconds, '
                    "confidence, key_signals, and rationale."
                ),
                "decision_schema_version": 1,
                "visibility": "public",
            },
        )
        assert submission_res.status_code == 200
        submission_id = submission_res.json()["submission_id"]

        detail_res = client.get(f"/arena/submissions/{submission_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()

        decisions_res = client.get(f"/runs/{UUID(detail['runs'][0]['run_id'])}/decisions?limit=50")
        assert decisions_res.status_code == 200
        assert len(decisions_res.json()) >= 1

    assert detail["status"] == "finished"
    assert detail["windows_total"] == 1
    assert detail["windows_completed"] == 1
    assert len(detail["runs"]) == 1

    run_id = UUID(detail["runs"][0]["run_id"])
    submission = db_session.get(ArenaSubmissionRow, UUID(submission_id))
    assert submission is not None
    submission_any = cast(Any, submission)
    assert submission_any.report_json is not None
    assert submission_any.report_call_id is not None

    run = db_session.get(RunRow, run_id)
    assert run is not None
    assert run.kind == "tournament"
    assert run.status == "finished"
    assert run.market_id == "spot:demo:BTC"
    assert run.model_key == model_key
    assert run.ended_at is not None

    cfg_row = db_session.get(RunConfigSnapshotRow, run.config_id)
    assert cfg_row is not None
    cfg = RunConfigSnapshot.model_validate(_config_dict(cfg_row))
    assert cfg.market_id == "spot:demo:BTC"
    assert cfg.model.key == model_key
    assert cfg.datasets.market_dataset_id == dataset_id
    assert cfg.datasets.sentiment_dataset_id is None

    link = db_session.execute(
        select(ArenaSubmissionRunRow).where(ArenaSubmissionRunRow.run_id == run_id)
    ).scalar_one()
    assert link.status == "finished"
    assert link.return_pct is not None

    decision_calls = list(
        db_session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id == run_id, LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert len(decision_calls) >= 1
    assert all(_call_prompt(call).get("model") == model_key for call in decision_calls)
    assert all(_call_prompt(call).get("messages") for call in decision_calls)
    assert all(call.response_raw for call in decision_calls)

    report_call = db_session.get(LlmCallRow, submission_any.report_call_id)
    assert report_call is not None
    assert report_call.purpose == "submission_report"
    assert report_call.response_raw
    assert _call_prompt(report_call).get("model") == model_key

    submission_report_calls = list(
        db_session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.purpose == "submission_report")
            .order_by(LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert len(submission_report_calls) >= 1


def test_tournament_full_workflow_persists_replayable_llm_data(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    market_id = "spot:demo:BTC"
    dataset_start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    total_hours = 24 * 16
    dataset_end = dataset_start + timedelta(hours=total_hours)

    dataset = DatasetRow(
        category="spot",
        source="demo",
        start=dataset_start,
        end=dataset_end,
        params={"market_id": market_id, "base_price": 50000.0},
        status="ready",
        error=None,
        created_at=dataset_start,
        updated_at=dataset_start,
    )
    db_session.add(dataset)
    db_session.flush()
    _seed_hourly_market_events(
        db_session,
        dataset_id=dataset.dataset_id,
        market_id=market_id,
        start=dataset_start,
        n_hours=total_hours,
    )

    with _fake_llm_server() as server:
        monkeypatch.setenv("V4T_LLM_MODEL", "fake-env-gpt")
        monkeypatch.setenv("V4T_LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("V4T_LLM_API_KEY", "test-key")
        monkeypatch.setenv("V4T_CELERY_ALWAYS_EAGER", "1")
        monkeypatch.setenv("V4T_REPLAY_BASE_INTERVAL_SECONDS", "3600")
        monkeypatch.setenv("V4T_REPLAY_MIN_INTERVAL_SECONDS", "3600")
        monkeypatch.setenv("V4T_REPLAY_PRICE_TICK_SECONDS", "3600")
        monkeypatch.setenv("V4T_ARENA_DATASET_IDS", str(dataset.dataset_id))
        get_settings.cache_clear()

        with _fresh_client(db_session) as client:
            submission_res = client.post(
                "/arena/submissions",
                json={
                    "market_id": market_id,
                    "model_key": "fake-env-gpt",
                    "prompt_text": (
                        "Trade BTC hourly. Return ONLY valid JSON with schema_version=2, target, mode, leverage, "
                        "stop_loss_pct, take_profit_pct, next_check_seconds, confidence, key_signals, and rationale."
                    ),
                    "decision_schema_version": 2,
                    "risk_level": 3,
                    "visibility": "public",
                },
            )
            assert submission_res.status_code == 200
            submission_id = UUID(submission_res.json()["submission_id"])

            detail_res = client.get(f"/arena/submissions/{submission_id}")
            assert detail_res.status_code == 200
            detail = detail_res.json()

    assert detail["status"] == "finished"
    assert detail["windows_total"] == 10
    assert detail["windows_completed"] == 10
    assert len(detail["runs"]) == 10

    submission = db_session.get(ArenaSubmissionRow, submission_id)
    assert submission is not None
    submission_any = cast(Any, submission)
    assert submission_any.report_json is not None
    assert submission_any.report_call_id is not None

    links = list(
        db_session.execute(
            select(ArenaSubmissionRunRow)
            .where(ArenaSubmissionRunRow.submission_id == submission_id)
            .order_by(ArenaSubmissionRunRow.scenario_index)
        )
        .scalars()
        .all()
    )
    assert len(links) == 10
    assert all(link.status == "finished" for link in links)
    assert all(link.return_pct is not None for link in links)
    assert all(link.window_start is not None and link.window_end is not None for link in links)
    assert all((link.window_end - link.window_start) == timedelta(hours=168) for link in links)

    run_ids = [UUID(run["run_id"]) for run in detail["runs"]]
    runs = [db_session.get(RunRow, run_id) for run_id in run_ids]
    assert all(run is not None for run in runs)
    concrete_runs = [cast(RunRow, run) for run in runs]
    assert all(run.market_id == market_id for run in concrete_runs)
    assert all(run.model_key == "fake-env-gpt" for run in concrete_runs)
    assert all(run.status == "finished" for run in concrete_runs)

    for run in concrete_runs:
        cfg_row = db_session.get(RunConfigSnapshotRow, run.config_id)
        assert cfg_row is not None
        cfg = RunConfigSnapshot.model_validate(_config_dict(cfg_row))
        assert cfg.market_id == market_id
        assert cfg.model.key == "fake-env-gpt"
        assert cfg.datasets.market_dataset_id == dataset.dataset_id
        assert cfg.decision_schema_version == 2
        assert cfg.risk_level == 3

    decision_calls = list(
        db_session.execute(
            select(LlmCallRow)
            .where(LlmCallRow.run_id.in_(run_ids), LlmCallRow.purpose == "decision")
            .order_by(LlmCallRow.run_id, LlmCallRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert len(decision_calls) >= 10 * 24 * 7
    assert all(_call_prompt(call).get("model") == "fake-env-gpt" for call in decision_calls)
    assert all(_call_prompt(call).get("messages") for call in decision_calls)
    assert all(call.response_raw for call in decision_calls)
    assert all(_call_response_parsed(call) is not None for call in decision_calls)
    assert all(call.error is None for call in decision_calls)
    parsed_decisions = [
        parsed for call in decision_calls if (parsed := _call_response_parsed(call)) is not None
    ]
    assert any(parsed.get("schema_version") == 2 for parsed in parsed_decisions)
    assert any(parsed.get("target") == 1.0 for parsed in parsed_decisions)

    run_decision_counts = {
        run_id: len([call for call in decision_calls if call.run_id == run_id])
        for run_id in run_ids
    }
    assert all(count in {24 * 7, (24 * 7) + 1} for count in run_decision_counts.values())

    decision_events = list(
        db_session.execute(
            select(EventRow)
            .where(EventRow.run_id.in_(run_ids), EventRow.event_type == "llm.decision")
            .order_by(EventRow.run_id, EventRow.observed_at)
        )
        .scalars()
        .all()
    )
    assert len(decision_events) == len(decision_calls)
    decision_call_ids = {call.call_id for call in decision_calls}
    for event in decision_events:
        payload = LlmDecisionPayload.model_validate(_event_payload(event))
        assert payload.llm_call_id in decision_call_ids

    portfolio_events = list(
        db_session.execute(
            select(EventRow).where(
                EventRow.run_id.in_(run_ids), EventRow.event_type == "portfolio.snapshot"
            )
        )
        .scalars()
        .all()
    )
    sim_fill_events = list(
        db_session.execute(
            select(EventRow).where(EventRow.run_id.in_(run_ids), EventRow.event_type == "sim.fill")
        )
        .scalars()
        .all()
    )
    finished_events = list(
        db_session.execute(
            select(EventRow).where(
                EventRow.run_id.in_(run_ids), EventRow.event_type == "run.finished"
            )
        )
        .scalars()
        .all()
    )
    assert len(portfolio_events) >= len(decision_calls)
    assert len(sim_fill_events) >= 10
    assert len(finished_events) == 10

    sample_snapshots = [
        PortfolioSnapshotPayload.model_validate(_event_payload(event))
        for event in portfolio_events[:2]
    ]
    assert sample_snapshots
    for snapshot in sample_snapshots:
        assert snapshot.position_qty_base is not None
        assert re.fullmatch(DECIMAL_STR_RE, snapshot.equity_quote)
        assert re.fullmatch(DECIMAL_STR_RE, snapshot.position_qty_base)

    parsed_fills = [
        SimFillPayload.model_validate(_event_payload(event)) for event in sim_fill_events[:10]
    ]
    assert parsed_fills

    report_call = db_session.get(LlmCallRow, submission_any.report_call_id)
    assert report_call is not None
    assert report_call.purpose == "submission_report"
    assert report_call.response_raw
    assert _call_response_parsed(report_call) is not None
    assert _call_prompt(report_call).get("model") == "fake-env-gpt"

    assert submission_any.report_json["key_metrics"]["decision_count"] == len(decision_calls)
    decision_request_count = 0
    report_request_count = 0
    for request in server.requests:
        messages = request.get("messages", [])
        system_prompt = messages[0].get("content", "") if messages else ""
        if "single-market arena submission" in system_prompt:
            report_request_count += 1
        else:
            decision_request_count += 1
    assert decision_request_count == len(decision_calls)
    assert report_request_count == 1
