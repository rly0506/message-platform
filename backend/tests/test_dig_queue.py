from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import CognitionMark, engine, init_db


def test_dig_queue_upserts_and_lists_one_stable_item():
    init_db()
    client = TestClient(api.app)
    payload = {
        "topic_id": 701,
        "topic_name": "RM055 Queue Topic",
        "event_id": 1701,
        "event_title": "Initial event title",
        "view": "contrast",
        "added_at": "2026-07-13T09:00:00Z",
    }

    created = client.put("/api/dig-queue", json=payload)

    assert created.status_code == 200
    assert created.json() == {
        "id": created.json()["id"],
        "item_key": "t:701:e:1701",
        **payload,
        "added_at": "2026-07-13T09:00:00",
    }

    updated = client.put(
        "/api/dig-queue",
        json={
            **payload,
            "event_title": "Updated event title",
            "view": "analogue",
            "added_at": "2026-07-13T10:00:00Z",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]
    assert updated.json()["event_title"] == "Updated event title"
    assert updated.json()["view"] == "analogue"

    listed = client.get("/api/dig-queue")
    assert listed.status_code == 200
    matching = [item for item in listed.json() if item["item_key"] == "t:701:e:1701"]
    assert len(matching) == 1
    assert matching[0] == updated.json()


def test_dig_queue_supports_topic_items_and_idempotent_delete():
    init_db()
    client = TestClient(api.app)
    created = client.put(
        "/api/dig-queue",
        json={
            "topic_id": 702,
            "topic_name": "RM055 Topic-only Queue",
            "event_id": None,
            "event_title": "RM055 Topic-only Queue",
            "view": "contrast",
            "added_at": "2026-07-13T11:00:00Z",
        },
    )
    assert created.status_code == 200
    assert created.json()["item_key"] == "t:702"

    deleted = client.delete("/api/dig-queue/t%3A702")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "item_key": "t:702"}

    repeated = client.delete("/api/dig-queue/t%3A702")
    assert repeated.status_code == 200
    assert repeated.json() == {"deleted": False, "item_key": "t:702"}
    assert all(item["item_key"] != "t:702" for item in client.get("/api/dig-queue").json())


def test_dig_queue_never_mutates_cognition_profile_or_marks():
    init_db()
    client = TestClient(api.app)
    before_profile = client.get("/api/cognition/profile").json()
    with Session(engine) as session:
        before_marks = list(session.exec(select(CognitionMark)).all())

    saved = client.put(
        "/api/dig-queue",
        json={
            "topic_id": 703,
            "topic_name": "Strictly separate curiosity",
            "event_id": 1703,
            "event_title": "Must not calibrate cognition",
            "view": "contrast",
            "added_at": "2026-07-13T12:00:00Z",
        },
    )
    assert saved.status_code == 200
    assert client.delete("/api/dig-queue/t%3A703%3Ae%3A1703").status_code == 200

    after_profile = client.get("/api/cognition/profile").json()
    with Session(engine) as session:
        after_marks = list(session.exec(select(CognitionMark)).all())

    assert after_profile == before_profile
    assert after_marks == before_marks
