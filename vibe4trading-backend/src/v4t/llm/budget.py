from __future__ import annotations

from collections import OrderedDict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from v4t.db.models import LlmCallRow


class LlmBudgetTracker:
    _MAX_CACHE_SIZE = 10_000

    def __init__(self) -> None:
        self._blocked_runs: OrderedDict[tuple[UUID, str], None] = OrderedDict()
        self._blocked_datasets: OrderedDict[tuple[UUID, str], None] = OrderedDict()
        self._blocked_submissions: OrderedDict[tuple[UUID, str], None] = OrderedDict()

    def _is_blocked(
        self, cache: OrderedDict[tuple[UUID, str], None], key: tuple[UUID, str]
    ) -> bool:
        if key not in cache:
            return False
        cache.move_to_end(key)
        return True

    def _mark_blocked(
        self, cache: OrderedDict[tuple[UUID, str], None], key: tuple[UUID, str]
    ) -> None:
        cache[key] = None
        cache.move_to_end(key)
        if len(cache) > self._MAX_CACHE_SIZE:
            cache.popitem(last=False)

    def exceeded_run(self, session: Session, *, run_id: UUID, purpose: str, limit: int) -> bool:
        if limit <= 0:
            return False
        key = (run_id, purpose)
        if self._is_blocked(self._blocked_runs, key):
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.run_id == run_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._mark_blocked(self._blocked_runs, key)
            return True
        return False

    def exceeded_dataset(
        self, session: Session, *, dataset_id: UUID, purpose: str, limit: int
    ) -> bool:
        if limit <= 0:
            return False
        key = (dataset_id, purpose)
        if self._is_blocked(self._blocked_datasets, key):
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.dataset_id == dataset_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._mark_blocked(self._blocked_datasets, key)
            return True
        return False

    def exceeded_submission(
        self, session: Session, *, submission_id: UUID, purpose: str, limit: int
    ) -> bool:
        if limit <= 0:
            return False
        key = (submission_id, purpose)
        if self._is_blocked(self._blocked_submissions, key):
            return True

        cnt = session.execute(
            select(func.count())
            .select_from(LlmCallRow)
            .where(LlmCallRow.submission_id == submission_id, LlmCallRow.purpose == purpose)
        ).scalar_one()
        if int(cnt) >= limit:
            self._mark_blocked(self._blocked_submissions, key)
            return True
        return False
