"""Public sentiment collectors via local OpenCLI."""
from __future__ import annotations

import os
import subprocess
from typing import Any

from app import config
from app.services import opencli_diagnostics


class RedditSentimentError(RuntimeError):
    """Raised when local Reddit/OpenCLI collection cannot complete."""


CHINESE_PLATFORMS = ("bilibili", "xiaohongshu", "xueqiu")
COMMENT_COMMANDS = {
    "reddit": "read",
    "bilibili": "comments",
    "xiaohongshu": "comments",
    "xueqiu": "comments",
}


def _browser_hint() -> str:
    """OpenCLI 失败多半是 Chrome 没开 / 登录态失效。给一句可操作提示, 并安抚: HN 不受影响。"""
    return ("　← 该平台经本机浏览器采集, 请确认 Chrome 已打开并登录对应平台后重试。"
            "(Hacker News 走公开 API, 不受此影响, 已照常采集。)")


def _opencli_missing_message(command: str) -> str:
    recommended = opencli_diagnostics.recommended_command()
    base = opencli_diagnostics.diagnostic_message(command, "", recommended)
    return f"{base} Chrome 登录态不是当前阻塞点；请先让后端能启动 OpenCLI。"


def _opencli_args(command: str, args: list[str]) -> list[str]:
    if os.name == "nt" and command.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", command, *args]
    return [command, *args]


def _run_opencli(command: str, args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _opencli_args(command, args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _opencli_start_error(platform: str, action: str, exc: OSError) -> str:
    detail = str(exc).strip() or exc.__class__.__name__
    return f"OpenCLI {platform} {action} could not start: {detail}. 请检查 OPENCLI_COMMAND 是否指向可执行的 opencli/opencli.cmd。"



def search_reddit(query: str, limit: int = 25, timeout: int = 45) -> list[dict[str, Any]]:
    """Search Reddit through OpenCLI and normalize posts.

    This is a local-only collector. It requires OpenCLI, Chrome, the extension,
    and an already logged-in Reddit session.
    """
    return search_platform("reddit", query, limit=limit, timeout=timeout)


def search_chinese_platforms(query: str, limit: int = 25, timeout: int = 45) -> list[dict[str, Any]]:
    """Search Chinese OpenCLI platforms with the original Chinese topic query."""
    posts: list[dict[str, Any]] = []
    for platform in CHINESE_PLATFORMS:
        posts.extend(search_platform(platform, query, limit=limit, timeout=timeout))
    return posts


def search_all_platforms(
    *,
    reddit_query: str,
    chinese_query: str,
    limit: int = 25,
    timeout: int = 45,
    platforms: tuple[str, ...] = ("reddit", "bilibili", "xiaohongshu", "xueqiu"),
    comment_post_limit: int = 5,
    comments_per_post: int = 10,
    hackernews: bool = True,
) -> dict[str, Any]:
    """Search all configured platforms, keeping failures isolated by platform.

    Hacker News runs over plain HTTP (no OpenCLI), so it's collected separately and
    succeeds even when the OpenCLI platforms are unavailable. It uses the English
    (reddit) query since HN is an English-language community.
    """
    posts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for platform in platforms:
        # Reddit: 配了官方 API 就走 API (无浏览器); 否则回退 OpenCLI (需 Chrome+登录)。
        if platform == "reddit":
            from app.collectors import reddit_api
            if reddit_api.is_configured():
                try:
                    posts.extend(reddit_api.search_reddit_api(reddit_query, limit=limit))
                except reddit_api.RedditApiError as exc:
                    errors.append({"platform": "reddit", "error": str(exc)})
                continue  # 已走 API, 跳过 OpenCLI 路线
        query = reddit_query if platform == "reddit" else chinese_query
        try:
            platform_posts = search_platform(platform, query, limit=limit, timeout=timeout)
            posts.extend(platform_posts)
            comments, comment_errors = fetch_comments_for_posts(
                platform,
                platform_posts,
                post_limit=comment_post_limit,
                comments_per_post=comments_per_post,
                timeout=timeout,
            )
            posts.extend(comments)
            errors.extend(comment_errors)
        except RedditSentimentError as exc:
            errors.append({"platform": platform, "error": str(exc)})

    # Hacker News: 公开 API, 零配置, 与 OpenCLI 平台失败相互隔离。
    if hackernews:
        from app.collectors import hackernews_sentiment
        try:
            posts.extend(hackernews_sentiment.search_hackernews(
                reddit_query,
                limit=limit,
                comment_post_limit=comment_post_limit,
                comments_per_post=comments_per_post,
            ))
        except hackernews_sentiment.HackerNewsError as exc:
            errors.append({"platform": "hackernews", "error": str(exc)})

    used_platforms = list(platforms) + (["hackernews"] if hackernews else [])
    return {
        "posts": posts,
        "errors": errors,
        "queries": {"reddit": reddit_query, "chinese": chinese_query},
        "platforms": used_platforms,
    }


def search_platform(platform: str, query: str, limit: int = 25, timeout: int = 45) -> list[dict[str, Any]]:
    """Search one OpenCLI platform and normalize posts."""
    command = config.OPENCLI_COMMAND or "opencli"
    try:
        completed = _run_opencli(command, [platform, "search", query, "-f", "yaml"], timeout)
    except FileNotFoundError as exc:
        raise RedditSentimentError(_opencli_missing_message(command)) from exc
    except subprocess.TimeoutExpired as exc:
        raise RedditSentimentError(
            f"OpenCLI {platform} search timed out after {timeout}s.{_browser_hint()}"
        ) from exc
    except OSError as exc:
        raise RedditSentimentError(_opencli_start_error(platform, "search", exc)) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RedditSentimentError(
            f"OpenCLI {platform} search failed: {detail or completed.returncode}{_browser_hint()}"
        )

    return [_normalize_post(item, platform=platform) for item in _load_yaml_list(completed.stdout)[: max(1, limit)]]


def fetch_comments_for_posts(
    platform: str,
    posts: list[dict[str, Any]],
    *,
    post_limit: int = 5,
    comments_per_post: int = 10,
    timeout: int = 45,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Fetch comments for top posts in platform default order.

    We intentionally do not pass a sort argument: comment order follows each
    platform/OpenCLI adapter's default ordering.
    """
    comments: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for post in posts[: max(0, post_limit)]:
        post_id = str(post.get("id") or "").strip()
        if not post_id:
            continue
        try:
            comments.extend(
                search_comments(
                    platform,
                    post_id,
                    limit=comments_per_post,
                    timeout=timeout,
                )
            )
        except RedditSentimentError as exc:
            errors.append({"platform": platform, "post_id": post_id, "error": str(exc)})
            continue
    return comments, errors


def search_comments(platform: str, post_id: str, limit: int = 10, timeout: int = 45) -> list[dict[str, Any]]:
    command_name = COMMENT_COMMANDS.get(platform)
    if not command_name:
        return []
    command = config.OPENCLI_COMMAND or "opencli"
    try:
        completed = _run_opencli(command, [platform, command_name, post_id, "-f", "yaml"], timeout)
    except FileNotFoundError as exc:
        raise RedditSentimentError(_opencli_missing_message(command)) from exc
    except subprocess.TimeoutExpired as exc:
        raise RedditSentimentError(f"OpenCLI {platform} {command_name} timed out after {timeout}s.") from exc
    except OSError as exc:
        raise RedditSentimentError(_opencli_start_error(platform, command_name, exc)) from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RedditSentimentError(f"OpenCLI {platform} {command_name} failed: {detail or completed.returncode}")

    return [
        _normalize_comment(item, platform=platform, parent_post_id=post_id)
        for item in _load_comment_items(completed.stdout)[: max(1, limit)]
    ]


def _load_comment_items(text: str) -> list[dict[str, Any]]:
    loaded = _load_yaml_list(text)
    if len(loaded) == 1 and isinstance(loaded[0].get("comments"), list):
        return [item for item in loaded[0]["comments"] if isinstance(item, dict)]
    comments: list[dict[str, Any]] = []
    for item in loaded:
        nested = item.get("comments")
        if isinstance(nested, list):
            comments.extend([child for child in nested if isinstance(child, dict)])
        else:
            comments.append(item)
    return comments


def _load_yaml_list(text: str) -> list[dict[str, Any]]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - environment guard
        raise RedditSentimentError("PyYAML is required to parse OpenCLI YAML output.") from exc
    try:
        loaded = yaml.safe_load(text) if text.strip() else []
    except Exception as exc:
        raise RedditSentimentError(f"Could not parse OpenCLI YAML output: {exc}") from exc
    if loaded is None:
        return []
    if isinstance(loaded, dict):
        loaded = loaded.get("items") or loaded.get("results") or [loaded]
    if not isinstance(loaded, list):
        raise RedditSentimentError("OpenCLI YAML output was not a list of Reddit posts.")
    return [item for item in loaded if isinstance(item, dict)]


def _normalize_post(item: dict[str, Any], *, platform: str = "reddit") -> dict[str, Any]:
    comments = item.get("num_comments", item.get("comments", item.get("comment_count", 0)))
    body = item.get("selftext") or item.get("selftext_snippet") or item.get("desc") or item.get("content") or item.get("text") or ""
    created = item.get("created_utc", item.get("created_at", item.get("time", "")))
    return {
        "platform": platform,
        "kind": "post",
        "id": str(item.get("id") or ""),
        "parent_post_id": "",
        "subreddit": str(item.get("subreddit") or item.get("channel") or item.get("community") or platform),
        "title": str(item.get("title") or ""),
        "author": str(item.get("author") or ""),
        "score": _int_value(item.get("score", item.get("likes", item.get("like_count", 0)))),
        "num_comments": _int_value(comments),
        "url": str(item.get("url") or ""),
        "created_utc": str(created or ""),
        "selftext_snippet": _snippet(str(body)),
    }


def _normalize_comment(item: dict[str, Any], *, platform: str, parent_post_id: str) -> dict[str, Any]:
    body = item.get("body") or item.get("text") or item.get("content") or item.get("comment") or item.get("message") or ""
    created = item.get("created_utc", item.get("created_at", item.get("time", "")))
    return {
        "platform": platform,
        "kind": "comment",
        "id": str(item.get("id") or item.get("comment_id") or ""),
        "parent_post_id": parent_post_id,
        "subreddit": str(item.get("subreddit") or item.get("channel") or item.get("community") or platform),
        "title": _snippet(str(body)),
        "author": str(item.get("author") or item.get("user") or ""),
        "score": _int_value(item.get("score", item.get("likes", item.get("like_count", 0)))),
        "num_comments": 0,
        "url": str(item.get("url") or ""),
        "created_utc": str(created or ""),
        "selftext_snippet": _snippet(str(body)),
    }


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _snippet(text: str, limit: int = 500) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[:limit]
