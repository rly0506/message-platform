from datetime import datetime

from fastapi.testclient import TestClient

from app import api, topic_ops
from app.db import Analysis, Article, SourceFraming, SourceRegistry, TimelineEvent, Topic, TopicArticle, engine, init_db
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


def test_collect_topic_persists_gnews_decode_trace(monkeypatch):
    init_db()

    def fake_collect_gnews(query):
        return [
            {
                "url": "https://www.reuters.com/world/story",
                "original_url": "https://news.google.com/rss/articles/CBMiSample?oc=5",
                "url_decoded": True,
                "url_decode_method": "batchexecute",
                "url_decode_error": "",
                "title": "Decode trace collection test",
                "source": "Reuters",
                "source_lang": "en",
                "source_country": "",
                "published_at": None,
                "snippet": "Decode trace collection test",
                "collector": "gnews",
            }
        ]

    monkeypatch.setattr(topic_ops.rss, "collect_gnews", fake_collect_gnews)

    with Session(engine) as session:
        topic = Topic(name="Decode trace collection test", queries=["Decode trace collection test"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            stats = topic_ops.collect_topic(session, topic, gnews=True)

            assert stats["decode_stats"]["gnews"]["decoded"] == 1
            links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic.id)).all()
            article = session.get(Article, links[0].article_id)
            assert article.url == "https://www.reuters.com/world/story"
            assert article.original_url == "https://news.google.com/rss/articles/CBMiSample?oc=5"
            assert article.url_decoded is True
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


def test_decode_stats_tracks_default_disabled_gnews_without_failed():
    stats = topic_ops._decode_stats(
        [
            {
                "collector": "gnews",
                "url_decoded": False,
                "url_decode_method": "disabled",
            }
        ]
    )

    assert stats["gnews"]["disabled"] == 1
    assert stats["gnews"]["failed"] == 0


def test_collect_topic_does_not_call_searxng_by_default(monkeypatch):
    init_db()
    called = []

    monkeypatch.setattr(topic_ops.config, "USE_SEARXNG", False)
    monkeypatch.setattr(topic_ops.searxng, "collect", lambda query: called.append(query))

    with Session(engine) as session:
        topic = Topic(name="SearXNG default off", queries=["SearXNG default off"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            stats = topic_ops.collect_topic(session, topic, gnews=False)

            assert called == []
            assert stats["requests"] == []
        finally:
            session.delete(topic)
            session.commit()


def test_collect_topic_uses_searxng_when_enabled(monkeypatch):
    init_db()

    monkeypatch.setattr(topic_ops.config, "USE_SEARXNG", True)
    monkeypatch.setattr(
        topic_ops.searxng,
        "collect",
        lambda query: [
            {
                "url": f"https://example.com/{query}",
                "title": f"{query} SearXNG result",
                "source": "example.com",
                "source_lang": "",
                "source_country": "",
                "published_at": None,
                "snippet": f"{query} SearXNG result",
                "collector": "searxng",
            }
        ],
    )

    with Session(engine) as session:
        topic = Topic(name="SearXNG enabled", queries=["SearXNG enabled"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            stats = topic_ops.collect_topic(session, topic, gnews=False)

            assert stats["collector_counts"] == {"searxng": 1}
            assert stats["requests"][0]["collector"] == "searxng"
            assert stats["requests"][0]["raw_count"] == 1
            assert stats["requests"][0]["kept_count"] == 1
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


def test_local_analysis_persist_preserves_existing_llm_analysis():
    init_db()

    with Session(engine) as session:
        topic = Topic(name="俄乌战争", queries=["俄乌战争"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        article = Article(
            url=f"https://example.com/llm-preserve/{topic.id}",
            title="俄乌战争 前线态势更新",
            source="Reuters",
            source_lang="zh",
            published_at=None,
            snippet="俄乌战争前线态势出现新变化。",
            collector="test",
        )
        session.add(article)
        session.commit()
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
        session.add(TimelineEvent(topic_id=topic.id, title_zh="LLM 时间线", summary_zh="LLM 生成"))
        session.add(SourceFraming(topic_id=topic.id, party="LLM 来源", stance="综合", summary_zh="LLM 观点"))
        session.add(Analysis(topic_id=topic.id, content_md=f"{topic_ops.LLM_ANALYSIS_MARKER}\nLLM 深度分析"))
        session.commit()

        topic_ops.analyze_topic(session, topic, persist=True)

        analyses = session.exec(select(Analysis).where(Analysis.topic_id == topic.id)).all()
        timeline = session.exec(select(TimelineEvent).where(TimelineEvent.topic_id == topic.id)).all()
        framing = session.exec(select(SourceFraming).where(SourceFraming.topic_id == topic.id)).all()

        assert len(analyses) == 1
        assert topic_ops.LLM_ANALYSIS_MARKER in analyses[0].content_md
        assert "LLM 深度分析" in analyses[0].content_md
        assert [row.title_zh for row in timeline] == ["LLM 时间线"]
        assert [row.party for row in framing] == ["LLM 来源"]

        for row in [*timeline, *framing, *analyses]:
            session.delete(row)
        session.delete(session.get(TopicArticle, (topic.id, article.id)))
        session.delete(article)
        session.delete(topic)
        session.commit()


def test_topic_detail_reports_when_llm_analysis_evidence_is_outdated():
    init_db()
    with Session(engine) as session:
        topic = Topic(name='Evidence drift', queries=['evidence drift'])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        def add_article(day: int) -> None:
            article = Article(
                url=f'https://example.com/evidence/{topic.id}/{day}',
                title=f'Evidence {day}',
                source='Example',
                published_at=datetime(2026, 7, day, 8),
                collector='test',
            )
            session.add(article)
            session.commit()
            session.refresh(article)
            session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
            session.commit()

        add_article(1)
        topic_ops._persist_analysis(session, topic.id, {
            'events': [],
            'framing': [],
            'analysis_md': f'{topic_ops.LLM_ANALYSIS_MARKER}\nInitial LLM analysis',
        })
        add_article(2)
        topic_ops.analyze_topic(session, topic, persist=True)
        topic_id = topic.id

    payload = TestClient(api.app).get(f'/api/topics/{topic_id}').json()
    assert 'Initial LLM analysis' in payload['analysis']['content_md']
    assert payload['analysis_meta']['source'] == 'llm'
    assert payload['analysis_meta']['sample_article_count'] == 1
    assert payload['analysis_meta']['current_article_count'] == 2
    assert payload['analysis_meta']['sample_latest_published_at'] == '2026-07-01T08:00:00'
    assert payload['analysis_meta']['current_latest_published_at'] == '2026-07-02T08:00:00'
    assert payload['analysis_meta']['evidence_newer'] is True
    assert payload['analysis_meta']['sample_changed'] is True

    with Session(engine) as session:
        topic_ops._persist_analysis(session, topic_id, {
            'events': [],
            'framing': [],
            'analysis_md': f'{topic_ops.LLM_ANALYSIS_MARKER}\nRefreshed LLM analysis',
        })

    refreshed = TestClient(api.app).get(f'/api/topics/{topic_id}').json()
    assert refreshed['analysis_meta']['sample_article_count'] == 2
    assert refreshed['analysis_meta']['current_article_count'] == 2
    assert refreshed['analysis_meta']['evidence_newer'] is False
    assert refreshed['analysis_meta']['sample_changed'] is False

    with Session(engine) as session:
        topic_ops.remove_topic(session, topic_id, dry_run=False)


def test_topic_detail_keeps_legacy_analysis_freshness_unknown():
    init_db()
    with Session(engine) as session:
        topic = Topic(name='Legacy analysis metadata', queries=['legacy analysis metadata'])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        article = Article(
            url=f'https://example.com/legacy-analysis/{topic.id}',
            title='Evidence added before sample metadata existed',
            source='Example',
            published_at=datetime(2026, 7, 3, 8),
            collector='test',
        )
        session.add(article)
        session.commit()
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
        session.add(
            Analysis(
                topic_id=topic.id,
                content_md='Legacy analysis without a recorded evidence snapshot',
                sample_article_count=None,
                sample_latest_published_at=None,
            )
        )
        session.commit()
        topic_id = topic.id

    payload = TestClient(api.app).get(f'/api/topics/{topic_id}').json()
    assert payload['analysis_meta']['sample_article_count'] is None
    assert payload['analysis_meta']['evidence_newer'] is None
    assert payload['analysis_meta']['sample_changed'] is None

    with Session(engine) as session:
        topic_ops.remove_topic(session, topic_id, dry_run=False)
