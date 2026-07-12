from contextlib import contextmanager
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api, topic_ops
from app.db import Article, Event, EventRelation, Topic, TopicArticle, engine, init_db


def test_event_graph_view_claims_blocking_topic_guard(monkeypatch):
    topic_id = _seed_topic_with_articles("Guarded Event Graph")
    claims: list[tuple[int, bool]] = []

    @contextmanager
    def fake_claim(claimed_topic_id: int, *, blocking: bool):
        claims.append((claimed_topic_id, blocking))
        yield True

    monkeypatch.setattr(api, "claim_topic", fake_claim)

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/event-graph")

    assert response.status_code == 200
    assert claims == [(topic_id, True)]


def test_event_graph_api_falls_back_to_local_events_for_legacy_topic():
    topic_id = _seed_topic_with_articles("Legacy Event Graph")

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/event-graph")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is False
    assert len(payload["nodes"]) >= 2
    assert any(edge["relation_type"] == "chronological" for edge in payload["edges"])
    assert all("from_id" in edge and "to_id" in edge for edge in payload["edges"])

    with Session(engine) as session:
        stored = session.exec(select(Event).where(Event.topic_id == topic_id)).all()
        assert len(stored) == len(payload["nodes"])


def test_event_graph_uses_stable_event_ids_and_builds_four_relation_types():
    topic_id = _seed_topic("Stored Event Graph")
    init_db()
    with Session(engine) as session:
        first = Event(
            topic_id=topic_id,
            date=datetime(2026, 6, 1),
            title="First strike",
            title_zh="第一轮空袭",
            summary_zh="第一轮空袭摘要。",
            article_ids=[101, 102],
            sources=["Reuters", "BBC"],
            entities=["伊朗", "白宫"],
            source_count=2,
            article_count=2,
        )
        second = Event(
            topic_id=topic_id,
            date=datetime(2026, 6, 2),
            title="Retaliation",
            title_zh="反击升级",
            summary_zh="反击升级摘要。",
            article_ids=[102, 103],
            sources=["Reuters", "AP"],
            entities=["伊朗", "霍尔木兹海峡"],
            source_count=2,
            article_count=2,
        )
        session.add(first)
        session.add(second)
        session.commit()
        session.refresh(first)
        session.refresh(second)
        expected_ids = {first.id, second.id}

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/event-graph")

    assert response.status_code == 200
    payload = response.json()
    assert {node["id"] for node in payload["nodes"]} == expected_ids
    assert payload["degraded"] is False
    edge_types = {edge["relation_type"] for edge in payload["edges"]}
    assert {
        "chronological",
        "shared_article",
        "shared_entity",
        "shared_source",
    }.issubset(edge_types)
    assert all(edge["from_id"] in expected_ids and edge["to_id"] in expected_ids for edge in payload["edges"])
    assert all(edge["from_id"] != 0 and edge["to_id"] != 1 for edge in payload["edges"])

    with Session(engine) as session:
        stored_relations = session.exec(select(EventRelation)).all()
        assert {row.relation_type for row in stored_relations}.issuperset(edge_types)


def test_analyze_topic_persists_events_idempotently():
    topic_id = _seed_topic_with_articles("Persisted Event Graph")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        topic_ops.analyze_topic(session, topic, persist=True)
        first_events = session.exec(select(Event).where(Event.topic_id == topic_id)).all()
        first_ids = [event.id for event in first_events]
        first_relation_count = len(session.exec(select(EventRelation)).all())

        topic_ops.analyze_topic(session, topic, persist=True)
        second_events = session.exec(select(Event).where(Event.topic_id == topic_id)).all()
        second_ids = [event.id for event in second_events]
        second_relation_count = len(session.exec(select(EventRelation)).all())

    assert first_ids
    assert second_ids == first_ids
    assert second_relation_count == first_relation_count


def test_event_graph_degrades_when_sample_is_too_small():
    topic_id = _seed_topic("Sparse Event Graph")
    init_db()
    with Session(engine) as session:
        session.add(Event(
            topic_id=topic_id,
            date=datetime(2026, 6, 1),
            title="Single event",
            title_zh="单节点",
            summary_zh="只有一个节点。",
            article_ids=[201],
            sources=["Reuters"],
            entities=["伊朗"],
            source_count=1,
            article_count=1,
        ))
        session.commit()

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/event-graph")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is True
    assert payload["edges"] == []
    assert "至少需要 2 个事件" in payload["note"]


def test_event_graph_degrades_when_dates_are_unknown():
    topic_id = _seed_topic("Unknown Date Event Graph")
    init_db()
    with Session(engine) as session:
        session.add(Event(
            topic_id=topic_id,
            title="Unknown first",
            title_zh="未知日期一",
            summary_zh="未知日期节点。",
            article_ids=[301],
            sources=["Reuters"],
            entities=["伊朗"],
            source_count=1,
            article_count=1,
        ))
        session.add(Event(
            topic_id=topic_id,
            title="Unknown second",
            title_zh="未知日期二",
            summary_zh="未知日期节点。",
            article_ids=[302],
            sources=["BBC"],
            entities=["白宫"],
            source_count=1,
            article_count=1,
        ))
        session.commit()

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/event-graph")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is True
    assert payload["edges"] == []
    assert "缺少可用日期" in payload["note"]


def _seed_topic(name: str) -> int:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, queries=[name])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        return topic.id


def _seed_topic_with_articles(name: str) -> int:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, queries=["Iran"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        base = datetime(2026, 6, 1)
        articles = [
            Article(
                url=f"https://example.com/{name}/strike",
                title="Israel launches strike on Iran nuclear site",
                source="Reuters",
                snippet="White House and Iran officials are cited.",
                published_at=base,
            ),
            Article(
                url=f"https://example.com/{name}/retaliation",
                title="Iran threatens retaliation in Strait of Hormuz",
                source="BBC",
                snippet="Iran and the Strait of Hormuz are central to the report.",
                published_at=base + timedelta(days=1),
            ),
            Article(
                url=f"https://example.com/{name}/markets",
                title="Oil markets watch Hormuz after Iran tensions",
                source="Financial Times",
                snippet="Markets react as Iran tensions continue.",
                published_at=base + timedelta(days=2),
            ),
        ]
        for article in articles:
            session.add(article)
        session.commit()
        for article in articles:
            session.refresh(article)
            session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
        session.commit()
        return topic.id
