from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx

from v4t.settings import get_settings, parse_csv_set

_TAG_RE = re.compile(r"<[^>]+>")


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _strip_html(text: str) -> str:
    text = _TAG_RE.sub(" ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip()
    # RSS pubDate is commonly RFC 2822.
    try:
        return _as_utc(parsedate_to_datetime(v))
    except Exception:
        pass

    # Atom updated/published is typically ISO 8601.
    try:
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        return _as_utc(datetime.fromisoformat(v))
    except Exception:
        return None


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _hash_external_id(*, feed_url: str, ident: str) -> str:
    h = hashlib.sha256()
    h.update(feed_url.encode("utf-8"))
    h.update(b"|")
    h.update((ident or "").encode("utf-8"))
    return h.hexdigest()[:32]


@dataclass(frozen=True)
class RssItem:
    external_id: str
    item_time: datetime
    title: str
    text: str
    url: str | None
    feed_url: str


def _iter_rss_items(*, feed_url: str, xml_bytes: bytes) -> Iterable[RssItem]:
    # defusedxml blocks common XML bombs (entity expansion, DTDs, etc.).
    from defusedxml import ElementTree as ET

    root = ET.fromstring(xml_bytes)

    # RSS 2.0: <rss><channel><item>...
    root_name = _local_name(root.tag).lower()
    if root_name in {"rss", "rdf"}:
        channel = None
        for child in list(root):
            if _local_name(child.tag) == "channel":
                channel = child
                break
        if channel is None:
            return []

        out: list[RssItem] = []
        for item in list(channel):
            if _local_name(item.tag) != "item":
                continue

            title = _strip_html("".join((item.findtext("title") or "").splitlines()))
            link = (item.findtext("link") or "").strip() or None
            guid = (item.findtext("guid") or "").strip()
            desc = item.findtext("description") or ""
            pub = _parse_dt(item.findtext("pubDate"))

            if pub is None:
                continue

            ident = guid or link or title or pub.isoformat()
            external_id = _hash_external_id(feed_url=feed_url, ident=ident)
            text = _strip_html(desc)
            full = (title + "\n" + text).strip() if title else text
            out.append(
                RssItem(
                    external_id=external_id,
                    item_time=pub,
                    title=title,
                    text=full,
                    url=link,
                    feed_url=feed_url,
                )
            )
        return out

    # Atom: <feed><entry>...
    if _local_name(root.tag) == "feed":
        out2: list[RssItem] = []
        for entry in list(root):
            if _local_name(entry.tag) != "entry":
                continue

            title = _strip_html("".join((entry.findtext("title") or "").splitlines()))
            ident = (entry.findtext("id") or "").strip()
            updated = _parse_dt(entry.findtext("updated") or entry.findtext("published"))
            summary = entry.findtext("summary") or entry.findtext("content") or ""

            link = None
            for child in list(entry):
                if _local_name(child.tag) == "link":
                    href = child.attrib.get("href")
                    if href:
                        link = href
                        break

            if updated is None:
                continue

            ident2 = ident or link or title or updated.isoformat()
            external_id = _hash_external_id(feed_url=feed_url, ident=ident2)
            text = _strip_html(summary)
            full = (title + "\n" + text).strip() if title else text
            out2.append(
                RssItem(
                    external_id=external_id,
                    item_time=updated,
                    title=title,
                    text=full,
                    url=link,
                    feed_url=feed_url,
                )
            )
        return out2

    return []


def _host_matches_allowlist(host: str, *, allowed: set[str]) -> bool:
    host = (host or "").strip().lower()
    if not host:
        return False
    for a in allowed:
        aa = a.strip().lower()
        if not aa:
            continue
        if host == aa or host.endswith("." + aa):
            return True
    return False


def _assert_public_host(host: str, *, port: int) -> None:
    # Treat any host that isn't globally routable as disallowed.
    h = (host or "").strip().lower()
    if not h:
        raise ValueError("missing host")
    if h == "localhost":
        raise ValueError("localhost is not allowed")

    # IP literal.
    try:
        ip = ipaddress.ip_address(h.strip("[]"))
        if not ip.is_global:
            raise ValueError(f"host is not globally routable: {ip}")
        return
    except ValueError:
        pass

    # Hostname: resolve and ensure all results are globally routable.
    infos = socket.getaddrinfo(h, port, type=socket.SOCK_STREAM)
    addrs = {info[4][0] for info in infos if info and info[4]}
    if not addrs:
        raise ValueError("host did not resolve")
    for addr in sorted(addrs):
        ip = ipaddress.ip_address(addr)
        if not ip.is_global:
            raise ValueError(f"host resolves to non-public address: {addr}")


def _validate_feed_url(raw_url: str) -> str:
    settings = get_settings()
    url = (raw_url or "").strip()
    if not url:
        raise ValueError("empty url")

    schemes = parse_csv_set(settings.sentiment_rss_allowed_schemes) or {"https", "http"}

    p = urlparse(url)
    scheme = (p.scheme or "").lower()
    if scheme not in {s.lower() for s in schemes}:
        raise ValueError(f"unsupported scheme: {scheme}")
    if not p.netloc or p.hostname is None:
        raise ValueError("missing host")
    if p.username or p.password:
        raise ValueError("userinfo in url is not allowed")

    host = p.hostname
    port = p.port or (443 if scheme == "https" else 80)

    allowed_hosts = parse_csv_set(settings.sentiment_rss_allowed_hosts)
    if allowed_hosts is not None and not _host_matches_allowlist(host, allowed=allowed_hosts):
        raise ValueError(f"host not allowed: {host}")

    if not settings.sentiment_rss_allow_private_hosts:
        _assert_public_host(host, port=port)

    return url


def _download_bytes(*, url: str, timeout: float, max_bytes: int) -> bytes:
    max_bytes = max(1, int(max_bytes))
    with httpx.Client(timeout=timeout, follow_redirects=True, trust_env=False) as client:
        with client.stream("GET", url) as r:
            r.raise_for_status()
            cl = r.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > max_bytes:
                raise ValueError(f"feed too large (content-length={cl} > max_bytes={max_bytes})")

            buf = bytearray()
            for chunk in r.iter_bytes():
                if not chunk:
                    continue
                buf.extend(chunk)
                if len(buf) > max_bytes:
                    raise ValueError(f"feed too large (> max_bytes={max_bytes})")

    return bytes(buf)


def fetch_rss_items(
    *,
    feeds: list[str],
    start: datetime,
    end: datetime,
    max_items: int = 50,
) -> tuple[list[RssItem], list[str]]:
    """Fetch and parse RSS/Atom feeds.

    Returns (items, errors). Items are sorted by item_time ascending.
    """

    start = _as_utc(start)
    end = _as_utc(end)
    max_items = max(0, int(max_items))

    settings = get_settings()
    timeout = float(settings.sentiment_rss_timeout_seconds)
    max_bytes = int(settings.sentiment_rss_max_bytes)

    items: list[RssItem] = []
    errors: list[str] = []
    for url in feeds:
        u = (url or "").strip()
        if not u:
            continue
        try:
            safe_url = _validate_feed_url(u)
            xml_bytes = _download_bytes(url=safe_url, timeout=timeout, max_bytes=max_bytes)
            parsed = list(_iter_rss_items(feed_url=safe_url, xml_bytes=xml_bytes))
            items.extend(parsed)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{u}: {repr(exc)}")

    # Filter + sort.
    items = [it for it in items if start <= it.item_time <= end]
    items.sort(key=lambda it: it.item_time)

    if max_items and len(items) > max_items:
        items = items[-max_items:]

    return items, errors
