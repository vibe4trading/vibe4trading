from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from fce.db.engine import new_session


def get_db() -> Generator[Session, None, None]:
    session = new_session()
    try:
        yield session
    finally:
        session.close()
