from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


def _floor_to_hour(dt: datetime) -> datetime:
    dt = dt.astimezone(UTC)
    return dt.replace(minute=0, second=0, microsecond=0)


def main() -> None:
    # Use a temporary SQLite DB so this is safe to run anytime.
    tmp_db = Path(__file__).resolve().parent / "smoke.db"
    os.environ["V4T_DATABASE_URL"] = f"sqlite:///{tmp_db}"
    os.environ["V4T_CELERY_ALWAYS_EAGER"] = "1"

    from v4t.api.app import create_app
    from v4t.db.engine import get_engine, get_sessionmaker
    from v4t.settings import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    app = create_app()

    now = datetime.now(UTC)
    start = _floor_to_hour(now - timedelta(hours=6))
    end = _floor_to_hour(now)

    with TestClient(app) as client:
        spot = client.post(
            "/datasets",
            json={
                "category": "spot",
                "source": "demo",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "params": {"market_id": "spot:demo:DEMO", "base_price": 1.0},
            },
        ).json()
        sent = client.post(
            "/datasets",
            json={
                "category": "sentiment",
                "source": "empty",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "params": {},
            },
        ).json()

        spot2 = client.get(f"/datasets/{spot['dataset_id']}").json()
        sent2 = client.get(f"/datasets/{sent['dataset_id']}").json()
        assert spot2["status"] == "ready", spot2
        assert sent2["status"] == "ready", sent2

        tpl = client.post(
            "/prompt_templates",
            json={
                "name": "smoke",
                "engine": "mustache",
                "system_template": "Output JSON.",
                "user_template": "risk={{risk_style}} market={{market_id}}",
                "vars_schema": {"risk_style": {"type": "string"}},
            },
        ).json()

        run = client.post(
            "/runs",
            json={
                "market_id": "spot:demo:DEMO",
                "model_key": "stub",
                "market_dataset_id": spot["dataset_id"],
                "sentiment_dataset_id": sent["dataset_id"],
                "prompt_template_id": tpl["template_id"],
                "prompt_vars": {"risk_style": "balanced"},
            },
        ).json()

        run2 = client.get(f"/runs/{run['run_id']}").json()
        assert run2["status"] == "finished", run2

        timeline = client.get(f"/runs/{run['run_id']}/timeline").json()
        decisions = client.get(f"/runs/{run['run_id']}/decisions").json()
        summary = client.get(f"/runs/{run['run_id']}/summary").json()

        assert len(timeline) > 0
        assert len(decisions) > 0
        assert summary["summary_text"]

    print("OK: end-to-end smoke run finished")


if __name__ == "__main__":
    main()
