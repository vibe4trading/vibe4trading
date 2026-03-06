from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from v4t.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
    if not settings.database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "pool_timeout": settings.db_pool_timeout_seconds,
            }
        )
    return create_engine(settings.database_url, **engine_kwargs)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def new_session() -> Session:
    SessionLocal = get_sessionmaker()
    return SessionLocal()
