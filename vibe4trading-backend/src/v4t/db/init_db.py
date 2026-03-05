from __future__ import annotations

from sqlalchemy.engine import Engine

from v4t.db import models as _models  # noqa: F401
from v4t.db.base import Base


def init_db(engine: Engine) -> None:
    # MVP bootstrap: create tables if missing. Alembic can take over later.
    Base.metadata.create_all(bind=engine)
