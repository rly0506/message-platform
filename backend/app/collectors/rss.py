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
import httpx

from app import config


class FeedFetchError(RuntimeError):
    """抓取 feed 的网络层失败 (超时/连不上/HTTP 错误)。"""


def _fetch_feed_bytes(url: str) -> bytes:
    """用 httpx 抓 feed 原始字节, 再交给 feedparser 解析。

    相比 feedparser 自己发请求, 这样能拿到三件 feedparser 给不了的东西:
      - 超时控制: 连不上的源 (国内直连不上的 Google News) 几秒内失败, 不干等。
      - 代理: trust_env=True 自动读 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY, 本机有代理即走代理。
      - 轻重试: 抖动性失败再试一次。
    """
    last_exc: Exception | None = None
    attempts = max(1, 1 + config.RSS_FETCH_RETRIES)
    # 显式 RSS_PROXY 优先; 留空则靠 trust_env 读环境变量。
    client_kwargs: dict[str, Any] = {
        "timeout": config.RSS_FETCH_TIMEOUT,
        "trust_env": True,
        "follow_redirects": True,
        "headers": {"User-Agent": config.RSS_USER_AGENT},
    }
    if config.RSS_PROXY:
        client_kwargs["proxy"] = config.RSS_PROXY
    for _ in range(attempts):
        try:
            with httpx.Client(**client_kwargs) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPError as exc:
            last_exc = exc
    raise FeedFetchError(str(last_exc) if last_exc else "feed fetch failed")


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
    # 先经 httpx 抓字节 (超时+代理+重试), 再喂给 feedparser 解析。
    content = _fetch_feed_bytes(url)
    parsed = feedparser.parse(content)
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
