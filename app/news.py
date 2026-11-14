"""Small shared RSS cache. Fixed sources, bounded downloads, no scraping or AI."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["news"])
SOURCES = (
    ("Le Monde", "https://www.lemonde.fr/rss/une.xml", "www.lemonde.fr"),
    ("France 24", "https://www.france24.com/fr/rss", "www.france24.com"),
)
_lock = threading.Lock()
_items = []
_updated = None
_next_refresh = 0


def parse_feed(data, source, host, now):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Unsupported XML declarations")
    root = ET.fromstring(data)
    items = []
    for entry in root.findall("./channel/item")[:50]:
        title = " ".join(unescape(re.sub(r"<[^>]*>", "", entry.findtext("title", ""))).split())
        url = entry.findtext("link", "").strip()
        parts = urlsplit(url)
        if not title or len(title) > 400 or parts.scheme != "https" or parts.netloc != host:
            continue
        try:
            date = parsedate_to_datetime(entry.findtext("pubDate", ""))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            published = date.timestamp()
        except (ValueError, TypeError, OverflowError):
            continue
        if not now - 86400 <= published <= now + 300:
            continue
        items.append({"title": title, "url": url, "source": source, "published_at": published})
    return sorted(items, key=lambda item: item["published_at"], reverse=True)[:4]


def snapshot():
    now = time.time()
    items = [dict(item) for item in _items if now - 86400 <= item["published_at"] <= now + 300]
    return {"items": items, "updated_at": _updated, "stale": bool(_updated and now - _updated > 1800)}


@router.get("/news")
def headlines():
    global _items, _updated, _next_refresh
    if time.monotonic() < _next_refresh or not _lock.acquire(blocking=False):
        return snapshot()
    try:
        # Recheck after acquiring: another request may have just refreshed the cache.
        if time.monotonic() < _next_refresh:
            return snapshot()
        fresh = []
        successful = set()
        now = time.time()
        for source, url, host in SOURCES:
            try:
                request = Request(url, headers={"User-Agent": "Toolbox/1.0 RSS reader"})
                with urlopen(request, timeout=4) as response:
                    data = response.read(512_001)
                if len(data) > 512_000:
                    raise ValueError("Feed too large")
                fresh.extend(parse_feed(data, source, host, now))
                successful.add(source)
            except Exception:
                # A missing feed must never break the site or trigger repeated fetches.
                continue
        if successful:
            fresh.extend(item for item in _items if item["source"] not in successful)
            unique = {item["url"]: item for item in fresh}
            _items = sorted(unique.values(), key=lambda item: item["published_at"], reverse=True)[:8]
            _updated = now
        _next_refresh = time.monotonic() + (900 if len(successful) == len(SOURCES) else 60)
        return snapshot()
    finally:
        _lock.release()
