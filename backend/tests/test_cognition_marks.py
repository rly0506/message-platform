from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import Article, CognitionProfile, Topic, TopicArticle, engine, init_db


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


def test_seed_cognition_mark_uses_target_key_and_note():
    client = TestClient(api.app)
    payload = {
        "target_type": "seed",
        "target_key": "https://example.com/frontier-seed",
        "domain": "energy",
        "label": "unfamiliar",
        "note": "能源领域只听过新闻，没有主动了解",
    }

    create = client.put("/api/cognition/marks", json=payload)
    assert create.status_code == 200
    body = create.json()
    assert body["target_type"] == "seed"
    assert body["target_key"] == payload["target_key"]
    assert body["target_id"] == 0
    assert body["domain"] == "energy"
    assert body["label"] == "unfamiliar"
    assert body["note"] == payload["note"]

    update = client.put("/api/cognition/marks", json={**payload, "label": "doubtful", "note": "需要再核对"})
    assert update.status_code == 200
    assert update.json()["id"] == body["id"]
    assert update.json()["label"] == "doubtful"
    assert update.json()["note"] == "需要再核对"

    marks = client.get("/api/cognition/marks?target_type=seed").json()
    assert len([mark for mark in marks if mark["target_key"] == payload["target_key"]]) == 1


def test_seed_mark_known_calibrates_matching_profile_with_evidence():
    init_db()
    client = TestClient(api.app)
    before = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}

    response = client.put("/api/cognition/marks", json={
        "target_type": "seed",
        "target_key": "https://example.com/science-frontier",
        "domain": "science",
        "label": "known",
        "note": "这条生命科学突破已经读懂。",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "science"
    after = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}
    assert after["biotech"]["confidence"] == min(100, before["biotech"]["confidence"] + 5)
    assert "标 science 种子已懂" in after["biotech"]["evidence"]
    assert f'{before["biotech"]["confidence"]}→{after["biotech"]["confidence"]}' in after["biotech"]["evidence"]


def test_seed_mark_unmapped_domain_is_stored_without_profile_calibration():
    init_db()
    client = TestClient(api.app)
    before = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}

    response = client.put("/api/cognition/marks", json={
        "target_type": "seed",
        "target_key": "https://example.com/other-frontier",
        "domain": "other",
        "label": "known",
    })

    assert response.status_code == 200
    assert response.json()["domain"] == "other"
    after = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}
    assert after == before


def test_seed_mark_doubtful_records_evidence_without_confidence_gain():
    init_db()
    client = TestClient(api.app)
    before = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}

    response = client.put("/api/cognition/marks", json={
        "target_type": "seed",
        "target_key": "https://example.com/finance-frontier",
        "domain": "finance",
        "label": "doubtful",
    })

    assert response.status_code == 200
    after = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}
    assert after["finance"]["confidence"] == before["finance"]["confidence"]
    assert "标 finance 种子存疑" in after["finance"]["evidence"]
    assert f'{before["finance"]["confidence"]}→{before["finance"]["confidence"]}' in after["finance"]["evidence"]


def test_repeating_same_seed_mark_does_not_recalibrate_profile_again():
    init_db()
    client = TestClient(api.app)
    payload = {
        "target_type": "seed",
        "target_key": "https://example.com/repeated-science-frontier",
        "domain": "science",
        "label": "known",
    }
    first = client.put("/api/cognition/marks", json=payload)
    assert first.status_code == 200
    after_first = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}

    second = client.put("/api/cognition/marks", json=payload)

    assert second.status_code == 200
    after_second = {item["domain_key"]: item for item in client.get("/api/cognition/profile").json()}
    assert after_second["biotech"]["confidence"] == after_first["biotech"]["confidence"]
    assert after_second["biotech"]["evidence"] == after_first["biotech"]["evidence"]


def test_cognition_profile_initializes_default_boundaries():
    response = TestClient(api.app).get("/api/cognition/profile")

    assert response.status_code == 200
    profile = response.json()
    assert len(profile) >= 11
    by_key = {item["domain_key"]: item for item in profile}
    assert by_key["ai_infra"]["level"] == "partial"
    assert "CPU" in by_key["ai_infra"]["note"]
    assert by_key["ai_infra"]["depth"] == "terms"
    assert by_key["ai_infra"]["interest"] == "high"
    assert by_key["ai_infra"]["confidence"] == 60
    assert by_key["ai_infra"]["evidence"]
    assert by_key["ai_infra"]["recommended_seed_style"] == "mechanism"
    assert by_key["energy"]["level"] == "unfamiliar"
    assert by_key["finance"]["level"] == "strong_partial"
    assert by_key["media_literacy"]["recommended_seed_style"] == "rhetoric_check"


def test_cognition_profile_updates_calibration_fields():
    client = TestClient(api.app)
    response = client.put("/api/cognition/profile", json=[
        {
            "domain_key": "energy",
            "level": "partial",
            "note": "开始关注电力和核能。",
            "depth": "mechanism",
            "interest": "medium",
            "confidence": 72,
            "evidence": "读过两条能源日报并追问核电受益逻辑。",
            "recommended_seed_style": "comparison",
        }
    ])

    assert response.status_code == 200
    by_key = {item["domain_key"]: item for item in response.json()}
    assert by_key["energy"]["level"] == "partial"
    assert by_key["energy"]["note"] == "开始关注电力和核能。"
    assert by_key["energy"]["depth"] == "mechanism"
    assert by_key["energy"]["interest"] == "medium"
    assert by_key["energy"]["confidence"] == 72
    assert by_key["energy"]["evidence"] == "读过两条能源日报并追问核电受益逻辑。"
    assert by_key["energy"]["recommended_seed_style"] == "comparison"


def test_cognition_profile_backfills_legacy_profile_rows():
    client = TestClient(api.app)
    client.get("/api/cognition/profile")
    with Session(engine) as session:
        item = session.exec(select(CognitionProfile).where(CognitionProfile.domain_key == "ai_infra")).one()
        item.note = "旧库里只有 level 和 note。"
        item.depth = "none"
        item.interest = "medium"
        item.confidence = 50
        item.evidence = ""
        item.recommended_seed_style = "mechanism"
        session.add(item)
        session.commit()

    response = client.get("/api/cognition/profile")

    assert response.status_code == 200
    by_key = {item["domain_key"]: item for item in response.json()}
    assert by_key["ai_infra"]["note"] == "旧库里只有 level 和 note。"
    assert by_key["ai_infra"]["depth"] == "terms"
    assert by_key["ai_infra"]["interest"] == "high"
    assert by_key["ai_infra"]["confidence"] == 60
    assert by_key["ai_infra"]["evidence"]
    assert by_key["ai_infra"]["recommended_seed_style"] == "mechanism"


def test_cognition_mark_put_cors_preflight_is_allowed():
    response = TestClient(api.app).options("/api/cognition/marks", headers={
        "Origin": "http://127.0.0.1:5173",
        "Access-Control-Request-Method": "PUT",
    })

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]


def test_lan_cors_preflight_is_allowed_for_mobile_dev():
    response = TestClient(api.app).options("/api/discovery/latest", headers={
        "Origin": "http://192.168.1.20:5173",
        "Access-Control-Request-Method": "GET",
    })

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://192.168.1.20:5173"


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
