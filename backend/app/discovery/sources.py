"""发现层数据源 —— 拉"注意力前沿"并归一为统一结构。

每个源借一群聪明人已经筛过一遍的注意力:
- Hacker News front_page: 技术圈最早冒头的东西 (Algolia API, 稳定开放)
- arXiv 最新论文: 想法刚被同行注意到的最早信号 (export API)
- 策展 RSS (智库/央行/科技媒体): 各领域专业人替你过滤过的前沿

源清单外置在 backend/config/frontier_sources.json, 可按领域增删, 不必改代码。
归一后的 DiscoveryItem 是快照存储和加速计算的基本单位。
external_id 是跨天比对的稳定键 —— 必须在多次运行间保持一致。
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any

import feedparser

from app import config

# 拉取超时 (秒)。源不可达时不阻塞整条链路。
_FETCH_TIMEOUT = 25
_USER_AGENT = config.RSS_USER_AGENT

# 前沿源配置文件 (sources.py 在 backend/app/discovery/, 上溯 3 层到 backend/)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_DIR = os.path.join(_BACKEND_DIR, "config")
FRONTIER_CONFIG = os.path.join(_CONFIG_DIR, "frontier_sources.json")


@dataclass
class DiscoveryItem:
    """一条发现候选 —— 来自某个注意力前沿的单个条目。

    signal: 加速检测的核心量纲。HN 用 points; arXiv/RSS 无投票, 用 0
            (它们的"信号"是"是否新出现", 由快照层的 first_seen 承担)。
    engagement: 互动量 (HN 评论数), 作为辅助信号。
    domain: 粗领域桶 (tech/finance/geopolitics/...), 用于报告分组、突破技术圈。
    """
    source: str                     # hackernews / arxiv / 源名
    external_id: str                # 跨天比对的稳定键
    title: str
    url: str
    signal: int = 0                 # 主信号 (HN points)
    engagement: int = 0             # 辅助信号 (评论数)
    category: str = ""              # 源内分类 (arXiv 的 cs.AI 等)
    domain: str = "tech"            # 领域桶
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        return resp.read()


def fetch_hackernews(limit: int = 30, domain: str = "tech") -> list[DiscoveryItem]:
    """HN 当日 front_page。Algolia API, 无需 key, 稳定。

    signal = points, engagement = num_comments。
    external_id = HN objectID (story id), 跨天稳定。
    """
    q = urllib.parse.urlencode({"tags": "front_page", "hitsPerPage": limit})
    url = f"https://hn.algolia.com/api/v1/search?{q}"
    raw = _http_get(url)
    data = json.loads(raw)
    out: list[DiscoveryItem] = []
    for hit in data.get("hits", []):
        oid = hit.get("objectID")
        title = hit.get("title") or ""
        if not oid or not title:
            continue
        story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
        out.append(DiscoveryItem(
            source="hackernews",
            external_id=str(oid),
            title=title,
            url=story_url,
            signal=int(hit.get("points") or 0),
            engagement=int(hit.get("num_comments") or 0),
            category="",
            domain=domain,
            meta={"author": hit.get("author", "")},
        ))
    return out


# arXiv 分类: 技术圈的不同角落。可按需扩展到 physics / q-bio / econ 等覆盖更多领域。
ARXIV_CATEGORIES = ("cs.AI", "cs.LG", "cs.CL")


def fetch_arxiv(
    categories: tuple[str, ...] = ARXIV_CATEGORIES,
    per_cat: int = 10,
    domain: str = "tech",
) -> list[DiscoveryItem]:
    """arXiv 各分类最新提交。export API + feedparser 解析 Atom。

    arXiv 无投票信号 -> signal=0; 它的"加速"由快照层 first_seen 判定
    (一篇论文从无到有地出现 = 新苗头)。
    external_id = arXiv id (去版本号), 跨天稳定。
    """
    out: list[DiscoveryItem] = []
    seen: set[str] = set()
    for cat in categories:
        q = urllib.parse.urlencode({
            "search_query": f"cat:{cat}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": per_cat,
        })
        url = f"http://export.arxiv.org/api/query?{q}"
        try:
            raw = _http_get(url)
        except Exception:
            # 单个分类拉取失败不影响其余 (网络容错)
            continue
        parsed = feedparser.parse(raw)
        for e in parsed.entries:
            link = e.get("id", "") or e.get("link", "")
            arxiv_id = _arxiv_id(link)
            if not arxiv_id or arxiv_id in seen:
                continue
            seen.add(arxiv_id)
            title = (e.get("title", "") or "").replace("\n", " ").strip()
            if not title:
                continue
            out.append(DiscoveryItem(
                source="arxiv",
                external_id=arxiv_id,
                title=title,
                url=link,
                signal=0,
                engagement=0,
                category=cat,
                domain=domain,
                meta={"summary": (e.get("summary", "") or "")[:500].replace("\n", " ").strip()},
            ))
    return out


def _arxiv_id(link: str) -> str:
    """从 arXiv URL 提取去版本号的稳定 id。

    http://arxiv.org/abs/2406.01234v2 -> 2406.01234
    """
    if not link:
        return ""
    tail = link.rstrip("/").split("/")[-1]
    # 去掉 vN 版本后缀, 让同一篇论文跨天对齐
    if "v" in tail:
        base, _, ver = tail.rpartition("v")
        if base and ver.isdigit():
            return base
    return tail


def fetch_rss_feed(name: str, url: str, domain: str = "tech") -> list[DiscoveryItem]:
    """策展 RSS 源 (智库/央行/科技媒体)。这些是各领域专业人筛过的前沿。

    RSS 无投票信号 -> signal=0; "加速"= 新出现 (first_seen), 同 arXiv。
    external_id = 条目链接 (RSS 的 guid/link 跨天稳定)。
    """
    parsed = feedparser.parse(url, agent=_USER_AGENT)
    out: list[DiscoveryItem] = []
    for e in parsed.entries:
        link = e.get("link", "") or e.get("id", "")
        title = (e.get("title", "") or "").replace("\n", " ").strip()
        if not link or not title:
            continue
        out.append(DiscoveryItem(
            source=name,
            external_id=link,
            title=title,
            url=link,
            signal=0,
            engagement=0,
            category="",
            domain=domain,
            meta={"summary": (e.get("summary", "") or "")[:500].replace("\n", " ").strip()},
        ))
    return out


def load_frontier_config(path: str = FRONTIER_CONFIG) -> list[dict]:
    """读前沿源清单, 只返回 enabled 的源。文件缺失时退回内置 HN+arXiv。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [s for s in data.get("sources", []) if s.get("enabled", True)]
    except (FileNotFoundError, json.JSONDecodeError):
        return [
            {"name": "Hacker News", "type": "hackernews", "domain": "tech", "limit": 30},
            {"name": "arXiv", "type": "arxiv", "domain": "tech",
             "categories": list(ARXIV_CATEGORIES), "per_cat": 10},
        ]


def fetch_one(src: dict) -> list[DiscoveryItem]:
    """按配置项拉单个源。未知 type 返回空。"""
    stype = src.get("type")
    domain = src.get("domain", "tech")
    if stype == "hackernews":
        return fetch_hackernews(limit=src.get("limit", 30), domain=domain)
    if stype == "arxiv":
        cats = tuple(src.get("categories", ARXIV_CATEGORIES))
        return fetch_arxiv(categories=cats, per_cat=src.get("per_cat", 10), domain=domain)
    if stype == "rss":
        url = src.get("url", "")
        if not url:
            return []
        return fetch_rss_feed(name=src.get("name", "rss"), url=url, domain=domain)
    return []


def fetch_all(config_path: str = FRONTIER_CONFIG) -> list[DiscoveryItem]:
    """按配置拉全部 enabled 源。单源失败不阻塞整体 (返回能拿到的部分)。"""
    items: list[DiscoveryItem] = []
    for src in load_frontier_config(config_path):
        try:
            items.extend(fetch_one(src))
        except Exception:
            # 源级容错: 一个源挂了, 其余照常
            continue
    return items
