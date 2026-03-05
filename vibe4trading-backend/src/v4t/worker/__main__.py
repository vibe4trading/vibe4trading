from __future__ import annotations

from v4t.observability.logging import configure_logging
from v4t.worker.celery_app import celery_app


def main() -> None:
    configure_logging()
    celery_app.start()


if __name__ == "__main__":
    main()
