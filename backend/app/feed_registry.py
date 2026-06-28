"""Curated RSS feed registry."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "feeds.json"
REQUIRED_FIELDS = {"name", "url", "country", "lang", "tier"}


@lru_cache(maxsize=1)
def curated_feeds() -> list[dict[str, str]]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    feeds = data.get("curated_feeds", data)
    if not isinstance(feeds, list):
        raise ValueError("feeds.json must contain a list or a curated_feeds list")
    return [_validate_feed(feed, index) for index, feed in enumerate(feeds)]


def _validate_feed(feed: Any, index: int) -> dict[str, str]:
    if not isinstance(feed, dict):
        raise ValueError(f"curated feed #{index + 1} must be an object")
    missing = sorted(REQUIRED_FIELDS - set(feed))
    if missing:
        raise ValueError(f"curated feed #{index + 1} missing keys: {', '.join(missing)}")
    out = {field: str(feed[field]).strip() for field in REQUIRED_FIELDS}
    empty = sorted(field for field, value in out.items() if not value)
    if empty:
        raise ValueError(f"curated feed #{index + 1} has empty keys: {', '.join(empty)}")
    if not out["url"].startswith(("http://", "https://")):
        raise ValueError(f"curated feed #{index + 1} has invalid url: {out['url']}")
    return {
        "name": out["name"],
        "url": out["url"],
        "country": out["country"],
        "lang": out["lang"],
        "tier": out["tier"],
    }
