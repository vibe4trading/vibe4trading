from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from v4t.db.models import LlmCallRow


class LlmBudgetTracker:
    def __init__(self) -> None:
        self._blocked_runs: set[tuple[UUID, str]] = set()
        self._blocked_datasets: set[tuple[UUID, str]] = set()

    def exceeded_run(self, session: Session, *, run_id: UUID, purpose: str, limit: int) -> bool:
        if limit <= 0:
            return False
        key = (run_id, purpose)
        if key in self._blocked_runs:
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.run_id == run_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._blocked_runs.add(key)
            return True
        return False

    def exceeded_dataset(
        self, session: Session, *, dataset_id: UUID, purpose: str, limit: int
    ) -> bool:
        if limit <= 0:
            return False
        key = (dataset_id, purpose)
        if key in self._blocked_datasets:
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.dataset_id == dataset_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._blocked_datasets.add(key)
            return True
        return False
