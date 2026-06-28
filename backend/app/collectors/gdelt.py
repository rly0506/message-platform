"""GDELT DOC 2.0 采集器 —— 历史回填 (免费 / 无 key / 全球 / 多语种)。

GDELT 只提供元数据 (标题/链接/域名/语言/时间)，不含正文与摘要，
正好契合"只存标题+链接"的版权策略。

文档: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app import config

API = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_seendate(s: str) -> Optional[datetime]:
    # GDELT 形如 "20240115T123000Z"
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ")
    except (ValueError, TypeError):
        return None


def _fetch_window(client: httpx.Client, query: str, start: datetime, end: datetime,
                  retries: int = 3) -> list[dict]:
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": config.GDELT_MAX_RECORDS,
        "sort": "DateDesc",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    # GDELT 对高频请求返回 429，指数退避重试 (真实使用也会遇到，需自我限流)
    for attempt in range(retries):
        r = client.get(API, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        try:
            data = r.json()
        except ValueError:
            # GDELT 在查询非法/无结果时可能返回非 JSON 文本
            return []
        return data.get("articles", []) or []
    raise httpx.HTTPError("429 Too Many Requests (retries exhausted)")


def collect(query: str, start: datetime, end: datetime, window_days: int = 30) -> list[dict]:
    """按时间窗口分段抓取 [start, end]，返回标准化文章 dict 列表。

    分窗的原因: GDELT 单次最多 250 条且按时间倒序，
    跨年回填必须切成小窗口，否则只拿到最近的 250 条。
    """
    out: list[dict] = []
    seen_urls: set[str] = set()
    with httpx.Client(headers={"User-Agent": config.RSS_USER_AGENT}) as client:
        cur = start
        while cur < end:
            win_end = min(cur + timedelta(days=window_days), end)
            try:
                raw = _fetch_window(client, query, cur, win_end)
            except httpx.HTTPError as e:
                print(f"  [gdelt] 窗口 {cur.date()}~{win_end.date()} 失败: {e}")
                raw = []
            for a in raw:
                url = a.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                out.append({
                    "url": url,
                    "title": a.get("title", ""),
                    "source": a.get("domain", ""),
                    "source_lang": a.get("language", ""),
                    "source_country": a.get("sourcecountry", ""),
                    "published_at": _parse_seendate(a.get("seendate", "")),
                    "snippet": "",
                    "collector": "gdelt",
                })
            cur = win_end
            time.sleep(5)  # GDELT 要求每 5 秒最多 1 次请求，避免窗口回填持续 429
    return out
