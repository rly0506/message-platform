from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api, db, feed_registry, topic_ops
from app.db import Article, Topic, TopicArticle, engine, init_db


def source_model():
    assert hasattr(db, "SourceRegistry")
    return db.SourceRegistry


def clear_sources(session: Session) -> None:
    SourceRegistry = source_model()
    for source in session.exec(select(SourceRegistry)).all():
        session.delete(source)
    session.commit()


def test_init_db_seeds_curated_source_registry_with_operational_defaults():
    init_db()
    SourceRegistry = source_model()
    first_feed = feed_registry.curated_feeds()[0]

    with Session(engine) as session:
        rows = session.exec(select(SourceRegistry)).all()
        source = session.exec(
            select(SourceRegistry).where(SourceRegistry.url == first_feed["url"])
        ).one()

    assert rows
    assert source.name == first_feed["name"]
    assert source.country == first_feed["country"]
    assert source.language == first_feed["lang"]
    assert source.source_type == "rss"
    assert source.quality_tier == first_feed["tier"]
    assert source.enabled is True
    assert source.requires_login is False
    assert source.fulltext_support is False
    assert source.last_status == "never"
    assert source.last_error == ""
    assert source.last_fetched_at is None
    assert source.article_count == 0


def test_curated_feeds_include_video_intelligence_sources():
    feeds = feed_registry.curated_feeds()
    by_name = {feed["name"]: feed for feed in feeds}

    assert {
        "TLDR",
        "The Rundown AI",
        "Morning Brew",
        "Stratechery",
        "Lenny's Newsletter",
        "OpenAI Research",
    } <= set(by_name)
    assert by_name["Morning Brew"]["enabled"] == "false"
    assert by_name["The Rundown AI"]["enabled"] == "false"
    assert by_name["Morning Brew"]["notes"]
    assert by_name["The Rundown AI"]["notes"]


def test_collect_topic_uses_enabled_registry_sources_and_skips_disabled(monkeypatch):
    init_db()
    SourceRegistry = source_model()

    with Session(engine) as session:
        clear_sources(session)
        enabled = SourceRegistry(
            name="Enabled Wire",
            url="https://example.com/enabled.xml",
            country="United Kingdom",
            language="en",
            source_type="rss",
            quality_tier="wire",
            enabled=True,
        )
        disabled = SourceRegistry(
            name="Disabled Wire",
            url="https://example.com/disabled.xml",
            country="United States",
            language="en",
            source_type="rss",
            quality_tier="wire",
            enabled=False,
        )
        topic = Topic(name="Battery supply chain", queries=["Battery supply chain"])
        session.add(enabled)
        session.add(disabled)
        session.add(topic)
        session.commit()
        session.refresh(topic)
        enabled_id = enabled.id

        seen_urls = []

        def fake_collect_feed(url, metadata=None):
            seen_urls.append(url)
            return [
                {
                    "url": "https://example.com/story",
                    "title": "Battery supply chain disruption",
                    "source": metadata["name"],
                    "source_lang": metadata["lang"],
                    "source_country": metadata["country"],
                    "published_at": None,
                    "snippet": "Battery supply chain disruption affects markets.",
                    "collector": "rss",
                    "source_tier": metadata["tier"],
                }
            ]

        monkeypatch.setattr(topic_ops.rss, "collect_feed", fake_collect_feed)

        stats = topic_ops.collect_topic(
            session,
            topic,
            gnews=False,
            use_curated_feeds=True,
            min_rel=0.2,
        )

    assert seen_urls == ["https://example.com/enabled.xml"]
    assert stats["raw"] == 1
    assert stats["kept"] == 1
    assert stats["requests"][0]["source_id"] == enabled_id
    assert stats["requests"][0]["source_name"] == "Enabled Wire"
    assert stats["requests"][0]["source_type"] == "rss"
    assert stats["requests"][0]["quality_tier"] == "wire"


def test_collect_topic_does_not_fallback_to_curated_feeds_when_registry_sources_are_disabled(monkeypatch):
    init_db()
    SourceRegistry = source_model()

    with Session(engine) as session:
        clear_sources(session)
        disabled = SourceRegistry(
            name="Disabled Limited Feed",
            url="https://example.com/disabled-limited.xml",
            country="United States",
            language="en",
            source_type="rss",
            quality_tier="mainstream",
            enabled=False,
            coverage="summary_only",
            access="paywalled",
            coverage_reason="Visible for source planning, not collected as a fresh feed.",
        )
        topic = Topic(name="Ukraine frontline", queries=["Ukraine frontline"])
        session.add(disabled)
        session.add(topic)
        session.commit()
        session.refresh(topic)

        seen_urls = []

        def fake_collect_feed(url, metadata=None):
            seen_urls.append(url)
            return []

        monkeypatch.setattr(topic_ops.rss, "collect_feed", fake_collect_feed)

        stats = topic_ops.collect_topic(
            session,
            topic,
            gnews=False,
            use_curated_feeds=True,
            min_rel=0.2,
        )

    assert seen_urls == []
    assert stats["raw"] == 0
    assert stats["requests"] == []


def test_collect_topic_updates_source_registry_status_and_failure(monkeypatch):
    init_db()
    SourceRegistry = source_model()

    with Session(engine) as session:
        clear_sources(session)
        ok_source = SourceRegistry(
            name="Status Wire",
            url="https://example.com/status.xml",
            country="France",
            language="en",
            source_type="rss",
            quality_tier="wire",
            enabled=True,
        )
        fail_source = SourceRegistry(
            name="Broken Feed",
            url="https://example.com/broken.xml",
            country="France",
            language="en",
            source_type="rss",
            quality_tier="mainstream",
            enabled=True,
        )
        topic = Topic(name="Energy security", queries=["Energy security"])
        session.add(ok_source)
        session.add(fail_source)
        session.add(topic)
        session.commit()
        session.refresh(topic)
        session.refresh(ok_source)
        session.refresh(fail_source)

        def fake_collect_feed(url, metadata=None):
            if "broken" in url:
                raise RuntimeError("feed offline")
            return [
                {
                    "url": "https://example.com/energy",
                    "title": "Energy security supply disruption",
                    "source": metadata["name"],
                    "source_lang": metadata["lang"],
                    "source_country": metadata["country"],
                    "published_at": None,
                    "snippet": "Energy security supply disruption affects markets.",
                    "collector": "rss",
                    "source_tier": metadata["tier"],
                }
            ]

        monkeypatch.setattr(topic_ops.rss, "collect_feed", fake_collect_feed)

        stats = topic_ops.collect_topic(
            session,
            topic,
            gnews=False,
            use_curated_feeds=True,
            min_rel=0.2,
        )
        session.refresh(ok_source)
        session.refresh(fail_source)

    assert stats["kept"] == 1
    assert ok_source.last_status == "ok"
    assert ok_source.last_error == ""
    assert ok_source.last_fetched_at is not None
    assert ok_source.article_count == 1
    assert fail_source.last_status == "failed"
    assert "feed offline" in fail_source.last_error
    assert fail_source.last_fetched_at is not None
    assert stats["requests"][1]["status"] == "failed"
    assert stats["requests"][1]["source_name"] == "Broken Feed"


def test_sources_api_lists_and_updates_registry_entries():
    init_db()
    client = TestClient(api.app)

    list_response = client.get("/api/sources")

    assert list_response.status_code == 200
    sources = list_response.json()
    assert sources
    source = sources[0]
    assert {"id", "name", "url", "enabled", "quality_tier", "source_type"} <= set(source)

    update_response = client.patch(f"/api/sources/{source['id']}", json={
        "enabled": False,
        "notes": "paused during test",
    })

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["enabled"] is False
    assert updated["notes"] == "paused during test"


def test_sources_api_creates_user_rss_source_and_rejects_duplicates():
    init_db()
    client = TestClient(api.app)
    payload = {
        "name": "Google Alert - Ukraine frontline",
        "url": "https://example.com/google-alerts/ukraine-frontline.xml",
        "country": "United States",
        "language": "en",
        "source_type": "rss",
        "quality_tier": "user",
        "notes": "Imported from Google Alerts",
    }

    response = client.post("/api/sources", json=payload)

    assert response.status_code == 200
    created = response.json()
    assert created["name"] == payload["name"]
    assert created["url"] == payload["url"]
    assert created["enabled"] is True
    assert created["source_type"] == "rss"
    assert created["quality_tier"] == "user"
    assert created["last_status"] == "never"

    duplicate = client.post("/api/sources", json=payload)
    assert duplicate.status_code == 409


def test_sources_api_preserves_classified_coverage_metadata():
    init_db()
    client = TestClient(api.app)
    payload = {
        "name": "WSJ World News",
        "url": "https://example.com/wsj-world.xml",
        "country": "United States",
        "language": "en",
        "source_type": "rss",
        "quality_tier": "mainstream",
        "enabled": False,
        "coverage": "summary_only",
        "access": "paywalled",
        "last_tested": "2026-07-04",
        "coverage_reason": "RSS only exposes summaries; full text requires subscription.",
        "state_media": True,
    }

    response = client.post("/api/sources", json=payload)

    assert response.status_code == 200
    created = response.json()
    assert created["coverage"] == "summary_only"
    assert created["access"] == "paywalled"
    assert created["last_tested"] == "2026-07-04"
    assert created["coverage_reason"] == "RSS only exposes summaries; full text requires subscription."
    assert created["state_media"] is True

    listed = client.get("/api/sources").json()
    row = next(item for item in listed if item["url"] == payload["url"])
    assert row["coverage"] == "summary_only"
    assert row["access"] == "paywalled"
    assert row["last_tested"] == "2026-07-04"
    assert row["coverage_reason"] == "RSS only exposes summaries; full text requires subscription."
    assert row["state_media"] is True


def test_sources_api_imports_bulk_feed_lines_with_duplicate_and_invalid_reports():
    init_db()
    client = TestClient(api.app)
    existing_payload = {
        "name": "Existing Alert",
        "url": "https://example.com/existing.xml",
        "country": "United States",
        "language": "en",
        "source_type": "rss",
        "quality_tier": "user",
    }
    assert client.post("/api/sources", json=existing_payload).status_code == 200

    response = client.post("/api/sources/import", json={
        "text": "\n".join([
            "Ukraine Alert https://example.com/ukraine.xml",
            "https://example.com/existing.xml",
            "not a url",
            "Field Notes, https://example.com/field-notes.xml",
        ]),
        "country": "United States",
        "language": "en",
        "source_type": "rss",
        "quality_tier": "newsletter",
    })

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 2
    assert payload["duplicate_count"] == 1
    assert payload["invalid_count"] == 1
    assert [item["name"] for item in payload["created"]] == ["Ukraine Alert", "Field Notes"]
    assert all(item["quality_tier"] == "newsletter" for item in payload["created"])
    assert payload["duplicates"][0]["url"] == "https://example.com/existing.xml"
    assert payload["invalid"][0]["line"] == "not a url"


def test_sources_api_validates_required_name_and_http_url():
    init_db()
    client = TestClient(api.app)

    missing_name = client.post("/api/sources", json={
        "url": "https://example.com/feed.xml",
    })
    bad_url = client.post("/api/sources", json={
        "name": "Bad Feed",
        "url": "ftp://example.com/feed.xml",
    })

    assert missing_name.status_code == 422
    assert bad_url.status_code == 422


def test_evidence_package_api_returns_no_llm_source_and_article_evidence():
    init_db()
    SourceRegistry = source_model()

    with Session(engine) as session:
        clear_sources(session)
        session.add(SourceRegistry(
            name="Reuters",
            url="https://example.com/reuters.xml",
            country="United Kingdom",
            language="en",
            source_type="rss",
            quality_tier="wire",
            enabled=True,
        ))
        topic = Topic(name="Ukraine frontline", queries=["Ukraine frontline"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        for idx, source in enumerate(["Reuters", "BBC"], start=1):
            article = Article(
                url=f"https://example.com/frontline/{idx}",
                title=f"Ukraine frontline supply disruption {idx}",
                source=source,
                source_lang="en",
                source_country="United Kingdom",
                published_at=datetime(2026, 6, idx),
                snippet="Ukraine frontline supply disruption and force posture update.",
                collector="rss",
            )
            session.add(article)
            session.commit()
            session.refresh(article)
            session.add(TopicArticle(
                topic_id=topic.id,
                article_id=article.id,
                relevance=0.9,
                relevant=True,
                stance="neutral",
            ))
        session.commit()
        topic_id = topic.id

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/evidence-package")

    assert response.status_code == 200
    payload = response.json()
    assert payload["topic_id"] == topic_id
    assert payload["article_count"] == 2
    assert payload["source_types"][0]["key"] == "rss"
    assert any(item["key"] == "wire" for item in payload["quality_tiers"])
    assert payload["articles"][0]["source_type"] == "rss"
    assert payload["articles"][0]["quality_tier"] in {"wire", "mainstream", "other"}
    assert payload["events"]
    assert payload["events"][0]["evidence_articles"]
    assert payload["entities"]
