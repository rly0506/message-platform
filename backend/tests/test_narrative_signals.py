from datetime import datetime, timedelta

from app.pipeline.local_analyze import ArticleRow


def row(idx: int, title: str, source: str, day: int = 0) -> ArticleRow:
    return ArticleRow(
        id=idx,
        title=title,
        source=source,
        published_at=datetime(2026, 6, 1) + timedelta(days=day),
        snippet="",
        relevance=0.8,
    )


def test_narrative_signals_group_repeated_topic_phrases():
    from app.pipeline import narrative_signals

    rows = [
        row(1, "AI capex boom will reshape data centers", "Reuters"),
        row(2, "Analysts say AI capex boom is accelerating", "Financial Times", 1),
        row(3, "AI capex boom draws chip investors", "Bloomberg", 2),
        row(4, "Central bank holds interest rates", "BBC", 3),
    ]

    signals = narrative_signals.detect_narrative_signals(rows)

    assert len(signals) == 1
    assert signals[0]["claim"] == "ai capex boom"
    assert signals[0]["source_count"] == 3
    assert signals[0]["article_count"] == 3
    assert signals[0]["article_ids"] == [1, 2, 3]
    assert signals[0]["first_seen"] == "2026-06-01T00:00:00"
    assert signals[0]["last_seen"] == "2026-06-03T00:00:00"


def test_narrative_signals_stay_empty_for_low_sample():
    from app.pipeline import narrative_signals

    rows = [
        row(1, "AI capex boom will reshape data centers", "Reuters"),
        row(2, "AI capex boom draws chip investors", "Reuters", 1),
    ]

    assert narrative_signals.detect_narrative_signals(rows) == []


def test_local_events_payload_includes_narrative_signals(monkeypatch):
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from app import api
    from app.db import Article, Topic, TopicArticle, engine, init_db

    init_db()
    with Session(engine) as session:
        topic = Topic(name="Narrative Topic", queries=["Narrative Topic"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        for idx, source in enumerate(["Reuters", "Financial Times", "Bloomberg"], start=1):
            article = Article(
                url=f"https://example.com/n/{idx}",
                title=f"AI capex boom reshapes market {idx}",
                source=source,
                published_at=datetime(2026, 6, idx),
            )
            session.add(article)
            session.commit()
            session.refresh(article)
            session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.8, relevant=True))
        session.commit()
        topic_id = topic.id

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/local-events").json()

    assert payload["narrative_signals"]
    assert payload["narrative_signals"][0]["claim"] == "ai capex boom"
