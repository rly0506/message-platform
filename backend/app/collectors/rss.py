"""RSS 采集器 —— 持续增量 (往后追踪)。

两种用法:
1. Google News RSS 检索式: 围绕主题检索词、跨多语种 locale 抓取，
   覆盖大量来源，是个人工具最省事的多语种增量源。
2. 显式 feed URL: 你信任的优质源的原生 RSS。

注意: RSS 只给"从现在往后"的增量，历史回填请用 GDELT。
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime
from time import mktime
from typing import Any

import feedparser

from app import config


def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None) or entry.get(key)
        if t:
            try:
                return datetime.fromtimestamp(mktime(t))
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def _parse_feed(
    url: str,
    collector: str,
    default_lang: str = "",
    metadata: dict[str, Any] | None = None,
) -> list[dict]:
    metadata = metadata or {}
    parsed = feedparser.parse(url, agent=config.RSS_USER_AGENT)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        exc = getattr(parsed, "bozo_exception", None)
        raise RuntimeError(str(exc) if exc else "feed parse failed")
    out: list[dict] = []
    for e in parsed.entries:
        link = e.get("link", "")
        if not link:
            continue
        # Google News RSS 的 source 在 e.source.title；普通 feed 取 feed 标题
        source = ""
        if "source" in e and isinstance(e.source, dict):
            source = e.source.get("title", "")
        if not source:
            source = parsed.feed.get("title", "")
        source = str(metadata.get("name") or source)
        out.append({
            "url": link,
            "title": e.get("title", ""),
            "source": source,
            "source_lang": metadata.get("lang") or parsed.feed.get("language", default_lang),
            "source_country": metadata.get("country", ""),
            "source_tier": metadata.get("tier", ""),
            "published_at": _entry_datetime(e),
            "snippet": e.get("summary", "")[:1000],
            "collector": collector,
        })
    return out


def collect_gnews(query: str) -> list[dict]:
    """对单个检索词，跨配置的多语种 locale 抓 Google News RSS。"""
    out: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []
    for hl, gl, ceid in config.GNEWS_LOCALES:
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
        try:
            items = _parse_feed(url, collector="gnews", default_lang=hl.split("-")[0])
        except Exception as e:  # feedparser 极少抛错，但网络层可能
            errors.append(f"{hl}: {e}")
            items = []
        for it in items:
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            out.append(it)
    if errors and not out:
        raise RuntimeError("; ".join(errors))
    return out


def collect_feed(url: str, metadata: dict[str, Any] | None = None) -> list[dict]:
    """抓取一个显式 RSS feed。"""
    return _parse_feed(url, collector="rss", metadata=metadata)
