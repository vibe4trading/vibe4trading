from __future__ import annotations

import os
from pathlib import Path

import pytest

from fce.db.engine import get_engine, get_sessionmaker
from fce.db.init_db import init_db
from fce.settings import get_settings


@pytest.fixture()
def sqlite_db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture()
def db_session(sqlite_db_url: str):
    os.environ["FCE_DATABASE_URL"] = sqlite_db_url
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    engine = get_engine()
    init_db(engine)
    SessionLocal = get_sessionmaker()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
