"""Hacker News 民间声音采集器测试 —— 打桩 HTTP, 不连网。"""
import httpx
import pytest

from app.collectors import hackernews_sentiment as hn


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _client_returning(search_payload, item_payload=None):
    """造一个假 httpx.Client: search 端点返回 stories, item 端点返回 comments。"""
    class _FakeClient:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url, params=None):
            if url == hn.ALGOLIA_SEARCH:
                return _FakeResp(search_payload)
            return _FakeResp(item_payload or {"children": []})
    return _FakeClient


def test_search_hackernews_normalizes_stories(monkeypatch):
    """story 命中被归一化成统一 post 形状 (platform=hackernews)。"""
    search_payload = {
        "hits": [
            {"objectID": "111", "title": "How China's debt traps work",
             "author": "paulpauper", "points": 240, "num_comments": 88,
             "url": "https://example.com/china-debt", "created_at": "2026-06-01T00:00:00Z"},
        ]
    }
    monkeypatch.setattr(hn.httpx, "Client", _client_returning(search_payload, {"children": []}))
    posts = hn.search_hackernews("china debt", limit=5, comment_post_limit=0)
    assert len(posts) == 1
    p = posts[0]
    assert p["platform"] == "hackernews"
    assert p["kind"] == "post"
    assert p["title"] == "How China's debt traps work"
    assert p["score"] == 240
    assert p["num_comments"] == 88
    assert p["url"] == "https://example.com/china-debt"


def test_search_hackernews_textpost_url_falls_back_to_discussion(monkeypatch):
    """Ask HN 这种无外链的文本帖, url 回退到 HN 讨论页。"""
    search_payload = {"hits": [{"objectID": "222", "title": "Ask HN: thoughts on debt?",
                                "author": "u", "points": 10, "num_comments": 3}]}
    monkeypatch.setattr(hn.httpx, "Client", _client_returning(search_payload))
    posts = hn.search_hackernews("debt", comment_post_limit=0)
    assert posts[0]["url"] == f"{hn.HN_ITEM_URL}222"


def test_search_hackernews_fetches_comments(monkeypatch):
    """高赞 story 会带回顶层非空评论 (HTML 被剥成纯文本)。"""
    search_payload = {"hits": [{"objectID": "333", "title": "Story", "author": "a",
                                "points": 100, "num_comments": 5}]}
    item_payload = {"children": [
        {"id": 9001, "author": "commenter", "points": 12,
         "text": "<p>This is a <i>useful</i> comment &amp; link.</p>"},
        {"id": 9002, "author": "empty", "text": ""},  # 空评论应被跳过
    ]}
    monkeypatch.setattr(hn.httpx, "Client", _client_returning(search_payload, item_payload))
    posts = hn.search_hackernews("x", comment_post_limit=1, comments_per_post=8)
    comments = [p for p in posts if p["kind"] == "comment"]
    assert len(comments) == 1
    assert comments[0]["platform"] == "hackernews"
    assert "useful" in comments[0]["selftext_snippet"]
    assert "<" not in comments[0]["selftext_snippet"]  # HTML 已剥
    assert "&amp;" not in comments[0]["selftext_snippet"]  # 实体已解码


def test_search_hackernews_empty_query_no_call(monkeypatch):
    """空 query 直接返回 [], 不发请求。"""
    def _boom(*a, **k):
        raise AssertionError("should not construct a client for empty query")
    monkeypatch.setattr(hn.httpx, "Client", _boom)
    assert hn.search_hackernews("   ") == []


def test_search_hackernews_network_error_raises(monkeypatch):
    """网络失败 -> HackerNewsError (调用方按平台隔离, 不连累其它平台)。"""
    class _Boom:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url, params=None):
            raise httpx.ConnectTimeout("down")
    monkeypatch.setattr(hn.httpx, "Client", _Boom)
    with pytest.raises(hn.HackerNewsError):
        hn.search_hackernews("china debt")


def test_search_hackernews_json_error_raises(monkeypatch):
    """JSON 解析失败 (ValueError) 也包成 HackerNewsError, 不漏出 (审核 Medium 修复)。"""
    class _BadJson:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url, params=None):
            class _R:
                def raise_for_status(self):
                    pass
                def json(self):
                    raise ValueError("not json")
            return _R()
    monkeypatch.setattr(hn.httpx, "Client", _BadJson)
    with pytest.raises(hn.HackerNewsError):
        hn.search_hackernews("china debt")


def test_strip_html_uses_unescape(monkeypatch):
    """_strip_html 用 html.unescape: 数字实体 / &nbsp; 都能解 (审核 Low 修复)。"""
    out = hn._strip_html("<p>a&nbsp;b &#39;c&#39; &amp; &#x2764;</p>")
    assert "&nbsp;" not in out and "&#39;" not in out and "&amp;" not in out
    assert "'c'" in out  # 数字实体解成单引号
    assert "<" not in out


def test_search_all_platforms_isolates_hackernews_failure(monkeypatch):
    """HN 失败不连累其它平台: 进 errors, 不抛 (民间层红线: 单平台挂不拖垮整体)。"""
    from app.collectors import reddit_sentiment

    # 所有 OpenCLI 平台都失败
    def fail_platform(platform, query, limit=25, timeout=45):
        raise reddit_sentiment.RedditSentimentError(f"{platform} unavailable")
    monkeypatch.setattr(reddit_sentiment, "search_platform", fail_platform)

    # HN 也失败
    from app.collectors import hackernews_sentiment
    def fail_hn(*a, **k):
        raise hackernews_sentiment.HackerNewsError("hn down")
    monkeypatch.setattr(hackernews_sentiment, "search_hackernews", fail_hn)

    result = reddit_sentiment.search_all_platforms(reddit_query="q", chinese_query="q")
    # 不抛, 各平台失败都进 errors
    assert any(e["platform"] == "hackernews" for e in result["errors"])
    assert "hackernews" in result["platforms"]


def test_search_all_platforms_can_disable_hackernews(monkeypatch):
    """hackernews=False 时不采 HN (留个关闭口)。"""
    from app.collectors import reddit_sentiment
    monkeypatch.setattr(reddit_sentiment, "search_platform",
                        lambda *a, **k: [])
    monkeypatch.setattr(reddit_sentiment, "fetch_comments_for_posts",
                        lambda *a, **k: ([], []))
    result = reddit_sentiment.search_all_platforms(
        reddit_query="q", chinese_query="q", hackernews=False)
    assert "hackernews" not in result["platforms"]
