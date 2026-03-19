from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from v4t.i18n import set_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    """Parse Accept-Language header and store locale in request state."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        locale = self._get_locale(request)
        request.state.locale = locale
        set_locale(locale)
        response = await call_next(request)
        return response

    def _get_locale(self, request: Request) -> str:
        """Get locale from query param or Accept-Language header."""
        query_lang = request.query_params.get("lang")
        if query_lang:
            return query_lang.strip()
        return self._parse_accept_language(request.headers.get("accept-language", ""))

    def _parse_accept_language(self, header: str) -> str:
        """Parse Accept-Language with quality values, return best match or 'en'."""
        if not header:
            return "en"

        locales: list[tuple[str, float]] = []
        for part in header.split(","):
            part = part.strip()
            if not part:
                continue
            if ";" in part:
                lang, q = part.split(";", 1)
                try:
                    quality = float(q.split("=")[1])
                except (IndexError, ValueError):
                    quality = 1.0
            else:
                lang = part
                quality = 1.0
            locales.append((lang.strip(), quality))

        if not locales:
            return "en"

        locales.sort(key=lambda x: x[1], reverse=True)

        for lang, _ in locales:
            if lang:
                return lang
            if "-" in lang:
                base = lang.split("-")[0]
                if base:
                    return base

        return "en"
