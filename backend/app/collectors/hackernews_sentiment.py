"""Hacker News 民间声音采集 (公开 API, 零配置)。

与 reddit_sentiment 的区别: Reddit 走本地 OpenCLI (需 Chrome + 登录态), 重且依赖环境;
HN 是纯 HTTP 公开 API, 无需 key / 登录 / 代理 —— 谁都能用, 是最稳的一条民间声部。

定位同 Reddit: 这是**民间情绪**, 不是事实源。HN 偏英语科技/创业圈, 立场滤镜独特。

两个端点各司其职:
- Algolia search (hn.algolia.com): 按主题搜历史讨论 —— 事件追踪要的是这个。
- items/{id}: 取某讨论的高赞评论 —— 补"讨论质感"。
(官方 Firebase API 只给"当下热榜", 无主题搜索, 故发现层用它、这里不用。)
"""
from __future__ import annotations

from typing import Any

import httpx

from app import config

ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
ALGOLIA_ITEM = "https://hn.algolia.com/api/v1/items"
HN_ITEM_URL = "https://news.ycombinator.com/item?id="


class HackerNewsError(RuntimeError):
    """HN 采集网络/解析失败。"""


def _client_kwargs() -> dict[str, Any]:
    # 与 rss.py 一致: 显式 RSS_PROXY 优先, 否则 trust_env。HN 直连即可, 但尊重用户代理设置。
    kwargs: dict[str, Any] = {
        "timeout": config.RSS_FETCH_TIMEOUT,
        "trust_env": True,
        "follow_redirects": True,
        "headers": {"User-Agent": config.RSS_USER_AGENT},
    }
    if config.RSS_PROXY:
        kwargs["proxy"] = config.RSS_PROXY
    return kwargs


def search_hackernews(
    query: str,
    limit: int = 25,
    comment_post_limit: int = 5,
    comments_per_post: int = 8,
) -> list[dict[str, Any]]:
    """搜 HN 上关于 query 的讨论, 返回归一化的 posts (+ 高赞 stories 的评论)。

    无网络/失败 -> 抛 HackerNewsError (调用方按平台隔离, 不影响其它平台)。
    """
    query = (query or "").strip()
    if not query:
        return []

    try:
        with httpx.Client(**_client_kwargs()) as client:
            resp = client.get(
                ALGOLIA_SEARCH,
                params={"query": query, "tags": "story", "hitsPerPage": max(1, limit)},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            posts = [_normalize_story(h) for h in hits if h.get("objectID")]

            # 给前 N 条高赞 story 取几条高赞评论, 补讨论质感 (与 Reddit 行为对齐)。
            for story in sorted(posts, key=lambda p: p["score"], reverse=True)[:comment_post_limit]:
                posts.extend(_fetch_comments(client, story["id"], comments_per_post))
    except (httpx.HTTPError, ValueError) as exc:
        # ValueError 含 JSON 解析失败 (resp.json()); 一并包成平台错误, 守住"单平台失败不拖垮整体"。
        raise HackerNewsError(f"Hacker News API failed: {exc}") from exc

    return posts


def _fetch_comments(client: httpx.Client, story_id: str, limit: int) -> list[dict[str, Any]]:
    """取某 story 的顶层评论 (取前 limit 条非空)。单条失败不影响整体。"""
    try:
        resp = client.get(f"{ALGOLIA_ITEM}/{story_id}")
        resp.raise_for_status()
        children = resp.json().get("children", []) or []
    except (httpx.HTTPError, ValueError):
        return []
    out: list[dict[str, Any]] = []
    for child in children:
        text = _strip_html(child.get("text") or "")
        if not text:
            continue
        out.append(_normalize_comment(child, story_id, text))
        if len(out) >= limit:
            break
    return out


def _normalize_story(hit: dict[str, Any]) -> dict[str, Any]:
    object_id = str(hit.get("objectID") or "")
    # story 可能是外链, 也可能是 Ask HN 文本帖; url 缺省回退到 HN 讨论页。
    url = str(hit.get("url") or "") or f"{HN_ITEM_URL}{object_id}"
    return {
        "platform": "hackernews",
        "kind": "post",
        "id": object_id,
        "parent_post_id": "",
        "subreddit": "Hacker News",
        "title": str(hit.get("title") or ""),
        "author": str(hit.get("author") or ""),
        "score": _int(hit.get("points")),
        "num_comments": _int(hit.get("num_comments")),
        "url": url,
        "created_utc": str(hit.get("created_at") or ""),
        "selftext_snippet": _snippet(_strip_html(hit.get("story_text") or "")),
    }


def _normalize_comment(child: dict[str, Any], parent_id: str, text: str) -> dict[str, Any]:
    return {
        "platform": "hackernews",
        "kind": "comment",
        "id": str(child.get("id") or ""),
        "parent_post_id": parent_id,
        "subreddit": "Hacker News",
        "title": _snippet(text),
        "author": str(child.get("author") or ""),
        "score": _int(child.get("points")),
        "num_comments": 0,
        "url": f"{HN_ITEM_URL}{child.get('id')}",
        "created_utc": str(child.get("created_at") or ""),
        "selftext_snippet": _snippet(text),
    }


def _strip_html(text: str) -> str:
    """HN 评论是 HTML 片段, 去标签 + 解实体留纯文本 (轻量, 不引依赖)。"""
    import html
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)  # stdlib: 覆盖 &nbsp;/数字实体等, 比手写替换稳
    return " ".join(text.split())


def _snippet(text: str, length: int = 280) -> str:
    text = (text or "").strip()
    return text[:length]


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
