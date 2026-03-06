from __future__ import annotations

from datetime import datetime

from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from v4t.auth.quota import check_quota, claim_quota, get_quota_date, increment_quota
from v4t.db.models import UserQuotaRow, UserRow


def test_get_quota_date_returns_midnight_utc() -> None:
    quota_date = get_quota_date()
    assert isinstance(quota_date, datetime)
    assert quota_date.hour == 0
    assert quota_date.minute == 0
    assert quota_date.second == 0
    assert quota_date.microsecond == 0


def test_check_quota_returns_default_if_missing(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    from v4t.settings import get_settings

    monkeypatch.setenv("V4T_DAILY_RUN_LIMIT", "5")
    get_settings.cache_clear()

    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    has_quota, used, limit = check_quota(db_session, user.user_id)
    assert has_quota is True
    assert used == 0
    assert limit == 5
    assert db_session.get(UserQuotaRow, (user.user_id, get_quota_date())) is None


def test_check_quota_returns_existing_row(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    from v4t.settings import get_settings

    monkeypatch.setenv("V4T_DAILY_RUN_LIMIT", "3")
    get_settings.cache_clear()

    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    quota_row = UserQuotaRow(
        user_id=user.user_id,
        quota_date=get_quota_date(),
        runs_used=2,
        runs_limit=3,
    )
    db_session.add(quota_row)
    db_session.commit()

    has_quota, used, limit = check_quota(db_session, user.user_id)
    assert has_quota is True
    assert used == 2
    assert limit == 3


def test_check_quota_exhausted(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    from v4t.settings import get_settings

    monkeypatch.setenv("V4T_DAILY_RUN_LIMIT", "3")
    get_settings.cache_clear()

    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    quota_row = UserQuotaRow(
        user_id=user.user_id,
        quota_date=get_quota_date(),
        runs_used=3,
        runs_limit=3,
    )
    db_session.add(quota_row)
    db_session.commit()

    has_quota, used, limit = check_quota(db_session, user.user_id)
    assert has_quota is False
    assert used == 3
    assert limit == 3


def test_increment_quota_creates_row(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    from v4t.settings import get_settings

    monkeypatch.setenv("V4T_DAILY_RUN_LIMIT", "5")
    get_settings.cache_clear()

    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    increment_quota(db_session, user.user_id)

    _, used, limit = check_quota(db_session, user.user_id)
    assert used == 1
    assert limit == 5


def test_increment_quota_increments_existing(db_session: Session, monkeypatch: MonkeyPatch) -> None:
    from v4t.settings import get_settings

    monkeypatch.setenv("V4T_DAILY_RUN_LIMIT", "5")
    get_settings.cache_clear()

    user = UserRow(
        oidc_issuer="test",
        oidc_sub="test-sub",
        email="test@example.com",
        display_name="Test User",
    )
    db_session.add(user)
    db_session.commit()

    increment_quota(db_session, user.user_id)
    increment_quota(db_session, user.user_id)

    _, used, limit = check_quota(db_session, user.user_id)
    assert used == 2
    assert limit == 5


def test_claim_quota_is_atomic_for_create_run(
    db_session: Session, monkeypatch: MonkeyPatch
) -> None:
    from v4t.settings import get_settings

    monkeypatch.setenv("V4T_DAILY_RUN_LIMIT", "2")
    get_settings.cache_clear()

    user = UserRow(
        oidc_issuer="test",
        oidc_sub="claim-sub",
        email="claim@example.com",
        display_name="Claim User",
    )
    db_session.add(user)
    db_session.commit()

    assert claim_quota(db_session, user.user_id) == (True, 1, 2)
    assert claim_quota(db_session, user.user_id) == (True, 2, 2)
    assert claim_quota(db_session, user.user_id) == (False, 2, 2)

    quota_row = db_session.execute(
        select(UserQuotaRow).where(
            UserQuotaRow.user_id == user.user_id,
            UserQuotaRow.quota_date == get_quota_date(),
        )
    ).scalar_one()
    assert quota_row.runs_used == 2
