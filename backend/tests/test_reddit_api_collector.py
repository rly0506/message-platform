"""Reddit 官方 API 采集器测试 —— 打桩 HTTP, 不连网。"""
import httpx
import pytest

from app import config
from app.collectors import reddit_api


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_is_configured_reflects_keys(monkeypatch):
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "")
    assert reddit_api.is_configured() is False
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "sec")
    assert reddit_api.is_configured() is True


def test_search_reddit_api_empty_or_unconfigured_returns_empty(monkeypatch):
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "")
    assert reddit_api.search_reddit_api("anything") == []
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "sec")
    assert reddit_api.search_reddit_api("   ") == []


def test_search_reddit_api_normalizes(monkeypatch):
    """token 换取 + 搜索结果归一化成统一 post 形状。"""
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "sec")

    search_payload = {"data": {"children": [
        {"data": {"id": "t3_1", "title": "US Iran tensions", "subreddit": "worldnews",
                  "author": "obs", "score": 128, "num_comments": 37,
                  "permalink": "/r/worldnews/comments/t3_1/x", "selftext": "vibes mostly"}},
    ]}}

    class _Client:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, url, auth=None, data=None):
            return _Resp({"access_token": "tok"})
        def get(self, url, headers=None, params=None):
            assert headers.get("Authorization") == "Bearer tok"  # 用上了 token
            return _Resp(search_payload)

    monkeypatch.setattr(reddit_api.httpx, "Client", _Client)
    posts = reddit_api.search_reddit_api("US Iran war", limit=5)
    assert len(posts) == 1
    p = posts[0]
    assert p["platform"] == "reddit"
    assert p["title"] == "US Iran tensions"
    assert p["score"] == 128
    assert p["url"] == "https://www.reddit.com/r/worldnews/comments/t3_1/x"


def test_search_reddit_api_network_error_raises(monkeypatch):
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "sec")

    class _Boom:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, *a, **k):
            raise httpx.ConnectTimeout("down")

    monkeypatch.setattr(reddit_api.httpx, "Client", _Boom)
    with pytest.raises(reddit_api.RedditApiError):
        reddit_api.search_reddit_api("x")


def test_search_reddit_api_json_error_raises(monkeypatch):
    """JSON 解析失败 (ValueError) 也包成 RedditApiError, 不漏出 (审核 Medium 修复)。"""
    monkeypatch.setattr(config, "REDDIT_CLIENT_ID", "id")
    monkeypatch.setattr(config, "REDDIT_CLIENT_SECRET", "sec")

    class _BadJson:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, url, auth=None, data=None):
            class _R:
                def raise_for_status(self):
                    pass
                def json(self):
                    raise ValueError("not json")
            return _R()

    monkeypatch.setattr(reddit_api.httpx, "Client", _BadJson)
    with pytest.raises(reddit_api.RedditApiError):
        reddit_api.search_reddit_api("china debt")


def test_search_all_platforms_uses_api_when_configured(monkeypatch):
    """配了 Reddit API key -> Reddit 走 API, 不调 OpenCLI subprocess。"""
    from app.collectors import reddit_sentiment, reddit_api as rapi

    monkeypatch.setattr(rapi, "is_configured", lambda: True)
    monkeypatch.setattr(rapi, "search_reddit_api",
                        lambda q, limit=25: [{"platform": "reddit", "kind": "post", "id": "1",
                                              "title": "via api", "score": 1, "num_comments": 0,
                                              "url": "u", "author": "a", "subreddit": "s",
                                              "created_utc": "", "selftext_snippet": "", "parent_post_id": ""}])

    def boom_opencli(*a, **k):
        raise AssertionError("OpenCLI should not be called when API is configured")
    monkeypatch.setattr(reddit_sentiment, "search_platform", boom_opencli)

    result = reddit_sentiment.search_all_platforms(
        reddit_query="q", chinese_query="q", platforms=("reddit",), hackernews=False)
    assert any(p["title"] == "via api" for p in result["posts"])


def test_search_all_platforms_falls_back_to_opencli_without_keys(monkeypatch):
    """没配 key -> Reddit 仍走 OpenCLI (向后兼容)。"""
    from app.collectors import reddit_sentiment, reddit_api as rapi

    monkeypatch.setattr(rapi, "is_configured", lambda: False)
    called = {"opencli": False}

    def fake_opencli(platform, query, limit=25, timeout=45):
        called["opencli"] = True
        return []
    monkeypatch.setattr(reddit_sentiment, "search_platform", fake_opencli)
    monkeypatch.setattr(reddit_sentiment, "fetch_comments_for_posts", lambda *a, **k: ([], []))

    reddit_sentiment.search_all_platforms(
        reddit_query="q", chinese_query="q", platforms=("reddit",), hackernews=False)
    assert called["opencli"] is True


def test_browser_hint_in_opencli_failure(monkeypatch):
    """A: OpenCLI 失败时, 错误带上'开浏览器'提示, 且安抚 HN 不受影响。"""
    import subprocess
    from app.collectors import reddit_sentiment

    def fail_run(*a, **k):
        return subprocess.CompletedProcess(a[0] if a else [], 1, stdout="", stderr="chrome not found")
    monkeypatch.setattr(reddit_sentiment.subprocess, "run", fail_run)
    monkeypatch.setattr(reddit_sentiment.config, "OPENCLI_COMMAND", "opencli")
    with pytest.raises(reddit_sentiment.RedditSentimentError) as exc:
        reddit_sentiment.search_platform("bilibili", "x")
    msg = str(exc.value)
    assert "Chrome" in msg and "Hacker News" in msg
