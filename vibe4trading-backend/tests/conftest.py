from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from v4t.api.app import create_app
from v4t.api.deps import get_db
from v4t.db.engine import get_engine, get_sessionmaker
from v4t.db.init_db import init_db
from v4t.settings import get_settings


@pytest.fixture()
def sqlite_db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture()
def db_session(sqlite_db_url: str):
    os.environ["V4T_DATABASE_URL"] = sqlite_db_url
    os.environ["V4T_BYPASS_AUTH"] = "1"
    os.environ["V4T_ARENA_DATASET_IDS"] = ""
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


@pytest.fixture()
def app(db_session, request: pytest.FixtureRequest) -> FastAPI:  # noqa: ANN001
    application = create_app()

    def _override_get_db():  # noqa: ANN001
        yield db_session

    application.dependency_overrides[get_db] = _override_get_db
    request.addfinalizer(application.dependency_overrides.clear)
    return application


@pytest.fixture()
def client(app: FastAPI, request: pytest.FixtureRequest) -> TestClient:
    c = TestClient(app)
    c.__enter__()

    def _close() -> None:
        c.__exit__(None, None, None)

    request.addfinalizer(_close)
    return c
