from app import topic_ops
from app.db import Article, SourceRegistry, Topic, TopicArticle, engine, init_db
from sqlmodel import Session, select


def test_query_variants_for_chinese_and_english():
    assert topic_ops.query_variants("美伊战争") == ["美伊战争", "美伊战争 最新 影响"]
    assert topic_ops.query_variants("DeepSeek") == ["DeepSeek", "DeepSeek latest impact"]
    assert topic_ops.query_variants("  ") == []


def test_gnews_hint_on_network_error():
    """网络/代理类错误 -> 追加可操作提示 (开 VPN / 设 RSS_PROXY)。"""
    from app.collectors.rss import FeedFetchError
    hint = topic_ops._gnews_hint(FeedFetchError("ConnectTimeout: timed out"))
    assert "RSS_PROXY" in hint and "VPN" in hint
    # 非网络错误 (如解析错误) 不追加提示, 避免误导
    assert topic_ops._gnews_hint(ValueError("bad value")) == ""


def test_gnews_network_error_surfaces_hint_in_diagnostics(monkeypatch):
    """gnews 因网络失败时, 采集诊断里的 error 带上代理提示。"""
    from app.collectors.rss import FeedFetchError
    init_db()

    def fail_gnews(query):
        raise FeedFetchError("ConnectTimeout: proxy unreachable")

    monkeypatch.setattr(topic_ops.rss, "collect_gnews", fail_gnews)
    with Session(engine) as session:
        topic = Topic(name="代理失败测试", queries=["代理失败测试"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            stats = topic_ops.collect_topic(session, topic, gnews=True)
            assert stats["raw"] == 0
            assert any("RSS_PROXY" in e for e in stats["errors"])
        finally:
            session.delete(topic)
            session.commit()



def test_collect_topic_returns_request_diagnostics(monkeypatch):
    init_db()

    def fake_collect_gnews(query):
        return [
            {
                "url": f"https://example.com/{query}/1",
                "title": f"{query} 采集诊断测试",
                "source": "Reuters",
                "source_lang": "zh",
                "source_country": "",
                "published_at": None,
                "snippet": "采集诊断测试",
                "collector": "gnews",
            }
        ]

    monkeypatch.setattr(topic_ops.rss, "collect_gnews", fake_collect_gnews)

    with Session(engine) as session:
        topic = Topic(name="采集诊断测试", queries=["采集诊断测试"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            stats = topic_ops.collect_topic(session, topic, gnews=True)

            assert stats["raw"] == 1
            assert stats["kept"] == 1
            assert stats["source_count"] == 1
            assert stats["collector_counts"] == {"gnews": 1}
            assert stats["requests"][0]["collector"] == "gnews"
            assert stats["requests"][0]["raw_count"] == 1
            assert stats["requests"][0]["kept_count"] == 1
            assert stats["requests"][0]["status"] == "ok"
        finally:
            links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic.id)).all()
            article_ids = [link.article_id for link in links]
            for link in links:
                session.delete(link)
            for article_id in article_ids:
                article = session.get(Article, article_id)
                if article:
                    session.delete(article)
            session.delete(topic)
            session.commit()


def test_collect_topic_curated_feed_adds_metadata_and_filters_by_relevance(monkeypatch):
    init_db()

    curated_feed = {
        "name": "Example Wire",
        "url": "https://example.com/wire/rss",
        "country": "United Kingdom",
        "lang": "en",
        "tier": "wire",
    }

    monkeypatch.setattr(topic_ops.feed_registry, "curated_feeds", lambda: [curated_feed])

    seen = []

    def fake_collect_feed(url, metadata=None):
        seen.append((url, metadata))
        return [
            {
                "url": "https://example.com/relevant",
                "title": "Battery supply chain disruption",
                "source": metadata["name"],
                "source_lang": metadata["lang"],
                "source_country": metadata["country"],
                "published_at": None,
                "snippet": "Battery supply chain disruption affects markets.",
                "collector": "rss",
                "source_tier": metadata["tier"],
            },
            {
                "url": "https://example.com/irrelevant",
                "title": "Local football results",
                "source": metadata["name"],
                "source_lang": metadata["lang"],
                "source_country": metadata["country"],
                "published_at": None,
                "snippet": "Sports results and entertainment.",
                "collector": "rss",
                "source_tier": metadata["tier"],
            },
        ]

    monkeypatch.setattr(topic_ops.rss, "collect_feed", fake_collect_feed)

    with Session(engine) as session:
        for source in session.exec(select(SourceRegistry)).all():
            session.delete(source)
        session.commit()
        topic = Topic(name="Battery supply chain", queries=["Battery supply chain"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            stats = topic_ops.collect_topic(
                session,
                topic,
                gnews=False,
                use_curated_feeds=True,
                min_rel=0.2,
            )

            assert seen == [(curated_feed["url"], curated_feed)]
            assert stats["raw"] == 2
            assert stats["kept"] == 1
            assert stats["requests"][0]["collector"] == "rss"
            assert stats["requests"][0]["query"] == curated_feed["url"]
            assert stats["requests"][0]["kept_count"] == 1

            links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic.id)).all()
            assert len(links) == 1
            article = session.get(Article, links[0].article_id)
            assert article is not None
            assert article.source == "Example Wire"
            assert article.source_country == "United Kingdom"
            assert article.source_lang == "en"
            assert article.collector == "rss"
        finally:
            links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic.id)).all()
            article_ids = [link.article_id for link in links]
            for link in links:
                session.delete(link)
            for article_id in article_ids:
                article = session.get(Article, article_id)
                if article:
                    session.delete(article)
            session.delete(topic)
            session.commit()
