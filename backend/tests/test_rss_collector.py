from types import SimpleNamespace

import httpx
import pytest

from app import config
from app.collectors import rss


def test_collect_feed_applies_curated_metadata(monkeypatch):
    metadata = {
        "name": "Reuters",
        "url": "https://www.reutersagency.com/feed/",
        "country": "United Kingdom",
        "lang": "en",
        "tier": "wire",
    }

    parsed = SimpleNamespace(
        bozo=False,
        feed={"title": "Fallback Feed Title", "language": "ignored"},
        entries=[
            {
                "link": "https://example.com/story",
                "title": "Iran nuclear talks resume",
                "summary": "A short summary",
            }
        ],
    )

    # 现在 _parse_feed 先经 httpx 抓字节再解析: 打桩抓取 (不连网) + 解析。
    monkeypatch.setattr(rss, "_fetch_feed_bytes", lambda url: b"<rss/>")
    monkeypatch.setattr(rss.feedparser, "parse", lambda content: parsed)

    items = rss.collect_feed(metadata["url"], metadata=metadata)

    assert len(items) == 1
    assert items[0]["source"] == "Reuters"
    assert items[0]["source_lang"] == "en"
    assert items[0]["source_country"] == "United Kingdom"
    assert items[0]["source_tier"] == "wire"
    assert items[0]["collector"] == "rss"


def test_fetch_feed_bytes_fails_fast_on_network_error(monkeypatch):
    """连不上的源 -> 抛 FeedFetchError, 不无限等 (快速失败)。"""
    calls = {"n": 0}

    class _Client:
        def __init__(self, *a, **k):
            calls.update(k)  # 记录构造参数, 验证 timeout/trust_env 已设
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url):
            raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(rss.httpx, "Client", _Client)
    with pytest.raises(rss.FeedFetchError):
        rss._fetch_feed_bytes("https://news.google.com/rss/search?q=x")
    # 健壮性参数确实传给了 httpx
    assert calls.get("trust_env") is True
    assert calls.get("timeout") == config.RSS_FETCH_TIMEOUT


def test_fetch_feed_bytes_retries_then_succeeds(monkeypatch):
    """轻重试: 第一次失败、第二次成功 -> 返回内容 (RSS_FETCH_RETRIES>=1)。"""
    monkeypatch.setattr(config, "RSS_FETCH_RETRIES", 1)
    attempts = {"n": 0}

    class _Client:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise httpx.ConnectError("first fails")
            return SimpleNamespace(content=b"<rss>ok</rss>", raise_for_status=lambda: None)

    monkeypatch.setattr(rss.httpx, "Client", _Client)
    assert rss._fetch_feed_bytes("https://example.com/feed") == b"<rss>ok</rss>"
    assert attempts["n"] == 2  # 失败一次 + 重试一次


def test_collect_gnews_degrades_per_locale(monkeypatch):
    """一个 locale 连不上 -> 跳过继续; 只要有一个成功, 整体仍返回结果 (不因单语种失败而全挂)。"""
    parsed = SimpleNamespace(
        bozo=False,
        feed={"title": "Google News", "language": "en"},
        entries=[{"link": "https://example.com/a", "title": "headline", "summary": "s"}],
    )
    monkeypatch.setattr(rss.feedparser, "parse", lambda content: parsed)

    def fetch(url):
        if "hl=en-US" in url:
            raise rss.FeedFetchError("en locale unreachable")
        return b"<rss/>"

    monkeypatch.setattr(rss, "_fetch_feed_bytes", fetch)
    items = rss.collect_gnews("中国政府债务")
    # 中文 locale 成功 -> 有结果; 英文 locale 失败被吞掉, 不抛
    assert len(items) == 1
    assert items[0]["url"] == "https://example.com/a"


def test_collect_gnews_raises_only_when_all_locales_fail(monkeypatch):
    """所有 locale 都连不上 -> 抛错 (让上层标 collect 失败, 而非静默返回空)。"""
    monkeypatch.setattr(rss, "_fetch_feed_bytes",
                        lambda url: (_ for _ in ()).throw(rss.FeedFetchError("all down")))
    with pytest.raises(RuntimeError):
        rss.collect_gnews("中国政府债务")
