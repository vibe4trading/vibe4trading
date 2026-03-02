from __future__ import annotations

import logging
import sys

import structlog

from fce.settings import get_settings


def configure_logging() -> None:
    """Configure stdlib logging + structlog.

    This is intentionally lightweight for MVP: JSON logs with stable keys.
    """

    settings = get_settings()
    level_name = (settings.log_level or "info").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
