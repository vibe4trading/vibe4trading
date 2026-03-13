from __future__ import annotations

from uuid import uuid4

from starlette.testclient import TestClient


def test_create_run_rejects_removed_risk_fields(client: TestClient) -> None:
    res = client.post(
        "/runs",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "market_dataset_id": str(uuid4()),
            "sentiment_dataset_id": str(uuid4()),
            "risk_level": 3,
            "holding_period": "swing",
        },
    )

    assert res.status_code == 422


def test_start_live_run_rejects_removed_risk_fields(client: TestClient) -> None:
    res = client.post(
        "/live/run",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "live_source": "demo",
            "base_price": 1.0,
            "risk_level": 3,
            "holding_period": "swing",
        },
    )

    assert res.status_code == 422


def test_create_submission_rejects_removed_risk_fields(client: TestClient) -> None:
    res = client.post(
        "/arena/submissions",
        json={
            "market_id": "spot:demo:DEMO",
            "model_key": "stub",
            "prompt_text": "Analyze market data.",
            "risk_level": 3,
            "holding_period": "swing",
            "visibility": "public",
        },
    )

    assert res.status_code == 422
