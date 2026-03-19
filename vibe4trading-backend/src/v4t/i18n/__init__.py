from __future__ import annotations

import json
from contextvars import ContextVar
from pathlib import Path

_locale_context: ContextVar[str] = ContextVar("locale", default="en")
_translations: dict[str, dict] = {}


def _load_translations() -> None:
    """Load translation files from locales directory."""
    locales_dir = Path(__file__).parent / "locales"
    for locale_file in locales_dir.glob("*.json"):
        locale = locale_file.stem
        with locale_file.open() as f:
            _translations[locale] = json.load(f)


def get_locale() -> str:
    """Get current request locale from context."""
    return _locale_context.get()


def set_locale(locale: str) -> None:
    """Set locale in context (used by middleware)."""
    _locale_context.set(locale)


def get_translation(key: str, locale: str | None = None, **kwargs: str | int | float) -> str:
    """Get translation for key with optional formatting."""
    if not _translations:
        _load_translations()

    target_locale = locale or get_locale()
    translations = _translations.get(target_locale, _translations.get("en", {}))

    keys = key.split(".")
    value = translations
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return key

    if isinstance(value, str) and kwargs:
        return value.format(**kwargs)

    return value if isinstance(value, str) else key
