from fastapi.testclient import TestClient
from sqlmodel import Session

from app import api
from app.db import Article, Topic, TopicArticle, engine, init_db


def test_cognition_mark_create_update_and_summary():
    topic_id, article_id = _seed_mark_case()
    client = TestClient(api.app)

    create = client.put("/api/cognition/marks", json={
        "target_type": "article",
        "target_id": article_id,
        "topic_id": topic_id,
        "label": "unexpected",
    })
    assert create.status_code == 200
    assert create.json()["label"] == "unexpected"

    update = client.put("/api/cognition/marks", json={
        "target_type": "article",
        "target_id": article_id,
        "topic_id": topic_id,
        "label": "doubtful",
    })
    assert update.status_code == 200
    assert update.json()["label"] == "doubtful"

    summary = client.get("/api/cognition/marks/summary").json()
    assert summary["counts"] == {"doubtful": 1}
    assert summary["recent"][0]["label"] == "doubtful"
    assert summary["recent"][0]["target_id"] == article_id
    assert summary["unfamiliar_topics"] == []

    marks = client.get(f"/api/cognition/marks?topic_id={topic_id}&target_type=article").json()
    assert len(marks) == 1
    assert marks[0]["target_id"] == article_id
    assert marks[0]["label"] == "doubtful"

    unfamiliar = client.put("/api/cognition/marks", json={
        "target_type": "article",
        "target_id": article_id,
        "topic_id": topic_id,
        "label": "unfamiliar",
    })
    assert unfamiliar.status_code == 200
    unfamiliar_summary = client.get("/api/cognition/marks/summary").json()
    assert unfamiliar_summary["unfamiliar_topics"] == [
        {"topic_id": topic_id, "topic": "Mark Topic", "count": 1}
    ]


def test_cognition_mark_rejects_unknown_label():
    response = TestClient(api.app).put("/api/cognition/marks", json={
        "target_type": "topic",
        "target_id": 1,
        "label": "interesting",
    })

    assert response.status_code == 422


def _seed_mark_case() -> tuple[int, int]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name="Mark Topic", queries=["Mark Topic"])
        article = Article(url="https://example.com/mark", title="Mark me")
        session.add(topic)
        session.add(article)
        session.commit()
        session.refresh(topic)
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
        session.commit()
        return topic.id, article.id
