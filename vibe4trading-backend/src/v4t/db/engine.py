from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from v4t.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def new_session() -> Session:
    SessionLocal = get_sessionmaker()
    return SessionLocal()
