"""Curated RSS feed registry."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlmodel import Session, select


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "feeds.json"
REQUIRED_FIELDS = {"name", "url", "country", "lang", "tier"}
# coverage: 能不能抓/新鲜度 (fresh_rss/summary_only/zombie/proxy_only)
# access: 访问方式 (public/paywalled/api_license/anti_bot)
# coverage_reason: 一句人话解释当前状态 (前端直接显示)
# last_tested: 实测新鲜度日期, 判 zombie
OPTIONAL_FIELDS = {"source_type", "enabled", "requires_login", "fulltext_support", "notes",
                   "coverage", "access", "coverage_reason", "last_tested", "state_media"}


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
    result = {
        "name": out["name"],
        "url": out["url"],
        "country": out["country"],
        "lang": out["lang"],
        "tier": out["tier"],
    }
    for field in OPTIONAL_FIELDS:
        if field in feed:
            result[field] = str(feed[field]).strip()
    return result


def enabled_registry_feeds(session: Session) -> list[dict[str, Any]]:
    from app.db import SourceRegistry

    rows = session.exec(
        select(SourceRegistry)
        .where(SourceRegistry.enabled == True)  # noqa: E712
        .where(SourceRegistry.source_type == "rss")
        .order_by(SourceRegistry.id)
    ).all()
    return [source_feed_metadata(source) for source in rows]


def has_registry_sources(session: Session) -> bool:
    from app.db import SourceRegistry

    return session.exec(select(SourceRegistry.id).limit(1)).first() is not None


def source_feed_metadata(source: Any) -> dict[str, Any]:
    return {
        "source_id": source.id,
        "name": source.name,
        "url": source.url,
        "country": source.country,
        "lang": source.language,
        "tier": source.quality_tier,
        "source_type": source.source_type,
    }
