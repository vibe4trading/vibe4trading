from __future__ import annotations

from uuid import UUID, uuid4

import v4t.worker.dispatch as dispatch_mod
from v4t.jobs.types import (
    JOB_TYPE_ARENA_EXECUTE_SUBMISSION,
    JOB_TYPE_DATASET_IMPORT,
    JOB_TYPE_RUN_EXECUTE_LIVE,
    JOB_TYPE_RUN_EXECUTE_REPLAY,
)


def test_dispatch_job_id_routes_to_correct_task(monkeypatch) -> None:  # noqa: ANN001
    calls: list[tuple[str, list[str]]] = []

    class _Res:
        def __init__(self, id_: str) -> None:
            self.id = id_

    def _send_task(name: str, args: list[str]):
        calls.append((name, args))
        return _Res("id-1")

    monkeypatch.setattr(dispatch_mod.celery_app, "send_task", _send_task)

    job_id = uuid4()
    assert dispatch_mod.dispatch_job_id(job_id=job_id, job_type=JOB_TYPE_DATASET_IMPORT) == "id-1"
    assert (
        dispatch_mod.dispatch_job_id(job_id=job_id, job_type=JOB_TYPE_RUN_EXECUTE_REPLAY) == "id-1"
    )
    assert dispatch_mod.dispatch_job_id(job_id=job_id, job_type=JOB_TYPE_RUN_EXECUTE_LIVE) == "id-1"
    assert (
        dispatch_mod.dispatch_job_id(job_id=job_id, job_type=JOB_TYPE_ARENA_EXECUTE_SUBMISSION)
        == "id-1"
    )

    assert [c[0] for c in calls] == [
        "v4t.worker.tasks.dataset_import_job",
        "v4t.worker.tasks.run_execute_replay_job",
        "v4t.worker.tasks.run_execute_live_job",
        "v4t.worker.tasks.arena_execute_submission_job",
    ]
    assert all(args == [str(job_id)] for _, args in calls)


def test_dispatch_job_id_rejects_unknown_job_type() -> None:
    job_id = UUID("00000000-0000-0000-0000-000000000001")
    try:
        dispatch_mod.dispatch_job_id(job_id=job_id, job_type="nope")
    except ValueError as exc:
        assert "Unknown job_type" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
