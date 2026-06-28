"""Reddit 官方 API 采集 (无浏览器, application-only OAuth)。

与 reddit_sentiment(OpenCLI)的区别:
- OpenCLI 路线: 驱动本机 Chrome + 已登录会话去模拟真人浏览。重、要记得开浏览器、登录态会掉。
- 本模块: Reddit 官方 API + application-only OAuth (client_credentials)。纯 HTTP, 无浏览器, 无需登录。
  代价: 你需在 https://www.reddit.com/prefs/apps 注册一个 "script" 应用拿 client_id/secret。

定位同其它民间源: 这是**民间情绪**, 不是事实源。

优雅降级: 没配 REDDIT_CLIENT_ID/SECRET -> is_configured()=False, 调用方回退到 OpenCLI 路线。
"""
from __future__ import annotations

from typing import Any

import httpx

from app import config

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/search"


class RedditApiError(RuntimeError):
    """Reddit 官方 API 网络/鉴权失败。"""


def is_configured() -> bool:
    """是否配齐了官方 API 凭据 (决定走 API 还是回退 OpenCLI)。"""
    return bool(config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET)


def _client_kwargs() -> dict[str, Any]:
    # 与 rss.py 一致: 显式 RSS_PROXY 优先, 否则 trust_env。Reddit 国内多半也需代理。
    kwargs: dict[str, Any] = {
        "timeout": config.RSS_FETCH_TIMEOUT,
        "trust_env": True,
        "follow_redirects": True,
        # Reddit 强制要求有辨识度的 User-Agent, 否则 429/封禁。
        "headers": {"User-Agent": config.REDDIT_USER_AGENT},
    }
    if config.RSS_PROXY:
        kwargs["proxy"] = config.RSS_PROXY
    return kwargs


def _get_token(client: httpx.Client) -> str:
    """application-only OAuth: 用 client_id/secret 换一个只读 access token。"""
    resp = client.post(
        TOKEN_URL,
        auth=(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RedditApiError("Reddit token response had no access_token")
    return str(token)


def search_reddit_api(query: str, limit: int = 25) -> list[dict[str, Any]]:
    """用官方 API 搜 Reddit 帖子, 返回归一化 posts。

    未配置 -> 返回 [] (调用方应先用 is_configured() 判定是否走此路)。
    网络/鉴权失败 -> 抛 RedditApiError (调用方按平台隔离)。
    """
    query = (query or "").strip()
    if not query or not is_configured():
        return []
    try:
        with httpx.Client(**_client_kwargs()) as client:
            token = _get_token(client)
            resp = client.get(
                SEARCH_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "limit": max(1, limit), "sort": "relevance", "type": "link"},
            )
            resp.raise_for_status()
            children = resp.json().get("data", {}).get("children", [])
    except (httpx.HTTPError, ValueError) as exc:
        # ValueError 含 JSON 解析失败 (resp.json() / token 解析); 一并包成平台错误。
        raise RedditApiError(f"Reddit API failed: {exc}") from exc

    return [_normalize(c.get("data", {})) for c in children if c.get("data")]


def _normalize(d: dict[str, Any]) -> dict[str, Any]:
    """对齐其它民间源的 post 形状 (platform=reddit)。"""
    permalink = d.get("permalink") or ""
    url = f"https://www.reddit.com{permalink}" if permalink else str(d.get("url") or "")
    return {
        "platform": "reddit",
        "kind": "post",
        "id": str(d.get("id") or ""),
        "parent_post_id": "",
        "subreddit": str(d.get("subreddit") or "reddit"),
        "title": str(d.get("title") or ""),
        "author": str(d.get("author") or ""),
        "score": _int(d.get("score")),
        "num_comments": _int(d.get("num_comments")),
        "url": url,
        "created_utc": str(d.get("created_utc") or ""),
        "selftext_snippet": _snippet(str(d.get("selftext") or "")),
    }


def _snippet(text: str, length: int = 280) -> str:
    return (text or "").strip()[:length]


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
