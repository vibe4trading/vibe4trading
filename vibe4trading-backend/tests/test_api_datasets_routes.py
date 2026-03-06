from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.db.models import DatasetRow, JobRow
from v4t.jobs.types import JOB_TYPE_DATASET_IMPORT


def test_create_dataset_validates_time_window(client: TestClient) -> None:
    now = datetime.now(UTC)
    res = client.post(
        "/datasets",
        json={
            "category": "spot",
            "source": "demo",
            "start": now.isoformat(),
            "end": now.isoformat(),
            "params": {"market_id": "spot:demo:DEMO"},
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "end must be after start"


def test_create_dataset_enqueues_import_job(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    def _fake_dispatch_job(*, job: JobRow) -> str:
        assert job.job_type == JOB_TYPE_DATASET_IMPORT
        return "task-123"

    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", _fake_dispatch_job)

    now = datetime.now(UTC)
    res = client.post(
        "/datasets",
        json={
            "category": "spot",
            "source": "demo",
            "start": (now - timedelta(hours=2)).isoformat(),
            "end": now.isoformat(),
            "params": {"market_id": "spot:demo:DEMO", "base_price": 1.0},
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["category"] == "spot"
    assert payload["status"] == "pending"
    assert payload["dataset_id"]

    dataset_id = UUID(payload["dataset_id"])
    row = db_session.get(DatasetRow, dataset_id)
    assert row is not None
    assert row.category == "spot"
    assert row.source == "demo"
    assert row.status == "pending"

    jobs = list(
        db_session.execute(select(JobRow).where(JobRow.dataset_id == row.dataset_id))
        .scalars()
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].job_type == JOB_TYPE_DATASET_IMPORT
    assert jobs[0].status == "pending"
    assert isinstance(jobs[0].payload, dict)
    payload = cast(dict[str, object], jobs[0].payload)
    celery_task_id = payload.get("celery_task_id")
    assert celery_task_id == "task-123"


def test_list_and_get_datasets(
    db_session: Session, client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    def _dispatch_job(*, job: JobRow) -> str:
        return "t"

    monkeypatch.setattr("v4t.worker.dispatch.dispatch_job", _dispatch_job)
    now = datetime.now(UTC)

    res1 = client.post(
        "/datasets",
        json={
            "category": "spot",
            "source": "demo",
            "start": (now - timedelta(hours=2)).isoformat(),
            "end": (now - timedelta(hours=1)).isoformat(),
            "params": {"market_id": "spot:demo:DEMO"},
        },
    )
    res2 = client.post(
        "/datasets",
        json={
            "category": "sentiment",
            "source": "empty",
            "start": (now - timedelta(hours=2)).isoformat(),
            "end": now.isoformat(),
            "params": {"market_id": "spot:demo:DEMO"},
        },
    )
    assert res1.status_code == 200
    assert res2.status_code == 200

    list_res = client.get("/datasets")
    assert list_res.status_code == 200
    out = list_res.json()
    assert out["total"] >= 2
    assert out["has_more"] is False
    assert len(out["items"]) >= 2
    assert out["items"][0]["dataset_id"] == res2.json()["dataset_id"]

    get_res = client.get(f"/datasets/{res1.json()['dataset_id']}")
    assert get_res.status_code == 200
    assert get_res.json()["dataset_id"] == res1.json()["dataset_id"]

    missing = client.get("/datasets/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "dataset not found"
