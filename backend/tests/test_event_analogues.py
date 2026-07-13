import json
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import Article, Event, EventRelation, Topic, TopicArticle, engine, init_db


def test_event_analogues_returns_cross_topic_evidence_and_named_differences():
    topic_id, target_id, same_topic_id, strong_id = _seed_main_case()
    response = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{target_id}/analogues")

    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is False
    assert payload["note"] == "类比不等于预测；请同时阅读差异提醒。"
    assert payload["target"]["event_id"] == target_id
    assert payload["scan"]["total_events"] >= 4
    assert payload["scan"]["eligible_candidates"] >= 2
    assert payload["scan"]["truncated"] is False
    item_ids = {item["event_id"] for item in payload["items"]}
    assert same_topic_id not in item_ids
    assert strong_id in item_ids

    strong = next(item for item in payload["items"] if item["event_id"] == strong_id)
    assert strong["similarity_score"] >= 70
    assert strong["score_label"] == "较强相似"
    kinds = {basis["kind"] for basis in strong["basis"]}
    assert kinds >= {"shared_entity", "shared_keyword"}
    assert all(basis["items"] and basis["weight"] > 0 for basis in strong["basis"])
    assert any("时间相差 8 个月" in item for item in strong["differences"])
    assert any("海湾国家" in item for item in strong["differences"])
    assert "时间阶段不同" not in strong["differences"]
    assert "参与方不同" not in strong["differences"]
    assert strong["evidence_article_ids"]
    assert [article["id"] for article in strong["evidence_articles"]] == strong["evidence_article_ids"]
    assert all(article["title"] and article["url"].startswith("https://example.com/") for article in strong["evidence_articles"])
    assert all(article["source"] and article["published_at"] for article in strong["evidence_articles"])
    assert strong["note"] == "相似仅表示样本内结构信号重合，不代表同因、同果或会重演。"


def test_event_analogue_score_thresholds_are_fixed():
    from app.services.event_analogues import _score_label

    assert _score_label(70) == "较强相似"
    assert _score_label(69) == "有限相似"
    assert _score_label(40) == "有限相似"
    assert _score_label(39) is None


def test_event_analogues_omits_candidates_below_40():
    with Session(engine) as session:
        init_db()
        target_topic = _topic(session, "Threshold target")
        other_topic = _topic(session, "Threshold other")
        target = _event(session, target_topic, "threshold-target", datetime(2026, 3, 1), ["加拿大"], ["BBC"], ["Canada election parliament campaign"])
        low = _event(session, other_topic, "threshold-low", datetime(2020, 1, 1), ["印度尼西亚"], ["Reuters"], ["Indonesia volcano evacuation ash"])
        topic_id, target_id, low_id = target_topic.id, target.id, low.id

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{target_id}/analogues").json()
    assert low_id not in {item["event_id"] for item in payload["items"]}


def test_event_analogues_degrades_when_topic_has_no_persisted_events():
    with Session(engine) as session:
        init_db()
        topic_id = _topic(session, "No persisted events").id

    response = TestClient(api.app).get(f"/api/topics/{topic_id}/events/999999/analogues")
    assert response.status_code == 200
    payload = response.json()
    assert payload["degraded"] is True
    assert payload["items"] == []
    assert payload["scan"]["scanned_candidates"] == 0
    assert "没有持久化事件" in payload["degraded_reason"]


def test_event_analogues_rejects_event_outside_topic():
    with Session(engine) as session:
        init_db()
        first = _topic(session, "Analogue association A")
        second = _topic(session, "Analogue association B")
        _event(session, first, "association-a", datetime(2026, 1, 1), ["法国"], ["Reuters"], ["France budget vote"])
        other = _event(session, second, "association-b", datetime(2026, 1, 2), ["德国"], ["Reuters"], ["Germany budget vote"])
        first_id, other_id = first.id, other.id

    response = TestClient(api.app).get(f"/api/topics/{first_id}/events/{other_id}/analogues")
    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found in topic"


def test_event_analogues_records_candidate_scan_truncation(monkeypatch):
    from app.services import event_analogues

    monkeypatch.setattr(event_analogues, "CANDIDATE_SCAN_CAP", 1)
    with Session(engine) as session:
        init_db()
        target_topic = _topic(session, "Truncation target")
        other_topic = _topic(session, "Truncation other")
        target = _event(session, target_topic, "truncation-target", datetime(2026, 4, 1), ["日本"], ["Reuters"], ["Japan rates currency markets"])
        for index in range(2):
            _event(session, other_topic, f"truncation-{index}", datetime(2026, 4, index + 2), ["日本"], ["Reuters"], ["Japan rates currency markets"])
        topic_id, target_id = target_topic.id, target.id

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{target_id}/analogues").json()
    assert payload["scan"]["eligible_candidates"] > 1
    assert payload["scan"]["scanned_candidates"] == 1
    assert payload["scan"]["candidate_cap"] == 1
    assert payload["scan"]["truncated"] is True
    assert "截断" in payload["scan"]["note"]


def test_event_analogues_candidate_cap_prefers_newest_events(monkeypatch):
    from app.services import event_analogues

    monkeypatch.setattr(event_analogues, "CANDIDATE_SCAN_CAP", 1)
    with Session(engine) as session:
        init_db()
        target_topic = _topic(session, "Newest target")
        other_topic = _topic(session, "Newest candidates")
        target = _event(
            session,
            target_topic,
            "newest-target",
            datetime(2027, 7, 1),
            ["Iran", "Hormuz"],
            ["Reuters", "BBC"],
            ["Iran Hormuz shipping pressure grows", "Iran Hormuz shipping pressure continues"],
        )
        newest = _event(
            session,
            other_topic,
            "newest-related",
            datetime(2027, 7, 2),
            ["Iran", "Hormuz"],
            ["Reuters", "AP News"],
            ["Iran Hormuz shipping pressure returns", "Iran Hormuz shipping pressure widens"],
        )
        _event(
            session,
            other_topic,
            "old-unrelated",
            datetime(2020, 1, 1),
            ["Brazil"],
            ["Financial Times"],
            ["Brazil agriculture rainfall outlook"],
        )
        topic_id, target_id, newest_id = target_topic.id, target.id, newest.id

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{target_id}/analogues").json()

    assert payload["scan"]["truncated"] is True
    assert newest_id in {item["event_id"] for item in payload["items"]}


def test_event_analogues_is_read_only_and_avoids_generated_causal_claims():
    with Session(engine) as session:
        init_db()
        target_topic = _topic(session, "Read only target")
        other_topic = _topic(session, "Read only other")
        target = _event(session, target_topic, "read-only-target", datetime(2026, 5, 1), ["欧盟", "关税"], ["Reuters", "BBC"], ["Europe tariff trade talks continue", "Europe tariff trade talks widen"])
        same = _event(session, target_topic, "read-only-same", datetime(2026, 5, 2), ["欧盟"], ["Reuters"], ["Europe tariff trade talks continue"])
        _event(session, other_topic, "read-only-other", datetime(2026, 6, 1), ["欧盟", "关税"], ["Reuters", "BBC"], ["Europe tariff trade talks continue", "Europe tariff trade talks widen"])
        session.add(EventRelation(from_event_id=target.id, to_event_id=same.id, relation_type="chronological", evidence="2026-05-01 to 2026-05-02", items=[]))
        session.commit()
        before = len(session.exec(select(EventRelation)).all())
        topic_id, target_id = target_topic.id, target.id

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/events/{target_id}/analogues").json()
    with Session(engine) as session:
        after = len(session.exec(select(EventRelation)).all())
    assert after == before

    generated = json.dumps([{"score_label": item["score_label"], "basis": item["basis"], "differences": item["differences"]} for item in payload["items"]], ensure_ascii=False)
    for forbidden in ("导致", "根因", "证明", "因果", "必然", "重演"):
        assert forbidden not in generated


def _seed_main_case() -> tuple[int, int, int, int]:
    with Session(engine) as session:
        init_db()
        target_topic = _topic(session, "Analogues target")
        other_topic = _topic(session, "Analogues other")
        target = _event(session, target_topic, "target", datetime(2026, 1, 10), ["伊朗", "霍尔木兹海峡"], ["Reuters", "BBC"], ["Iran sanctions tanker route pressure builds", "Iran sanctions tanker route pressure continues"])
        same = _event(session, target_topic, "same-topic", datetime(2026, 2, 10), ["伊朗", "霍尔木兹海峡"], ["Reuters", "BBC"], ["Iran sanctions tanker route pressure returns", "Iran sanctions tanker route pressure expands"])
        strong = _event(session, other_topic, "strong", datetime(2026, 9, 10), ["伊朗", "霍尔木兹海峡", "海湾国家"], ["Reuters", "AP News"], ["Iran sanctions tanker route pressure rises", "Iran sanctions tanker route pressure persists"])
        _event(session, other_topic, "unrelated", datetime(2024, 5, 1), ["巴西", "亚马孙雨林"], ["Financial Times"], ["Brazil rainforest farming weather outlook"])
        return target_topic.id, target.id, same.id, strong.id


def _topic(session: Session, name: str) -> Topic:
    topic = Topic(name=f"{name}-{uuid4().hex[:8]}", queries=[name])
    session.add(topic)
    session.commit()
    session.refresh(topic)
    return topic


def _event(session: Session, topic: Topic, label: str, date: datetime, entities: list[str], sources: list[str], texts: list[str]) -> Event:
    article_ids: list[int] = []
    for index, text in enumerate(texts):
        source = sources[index % len(sources)]
        article = Article(url=f"https://example.com/{label}-{uuid4().hex}", title=text, source=source, snippet=f"{text} evidence sample", published_at=date)
        session.add(article)
        session.commit()
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.9))
        article_ids.append(article.id)
    event = Event(topic_id=topic.id, date=date, title=f"{label} event", title_zh=f"{label} 事件", summary_zh=f"{label} 事件摘要", article_ids=article_ids, sources=sources, entities=entities, source_count=len(set(sources)), article_count=len(article_ids))
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
