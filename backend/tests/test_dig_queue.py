from concurrent.futures import ThreadPoolExecutor

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
        "expected_revision": None,
    }

    created = client.put("/api/dig-queue", json=payload)

    assert created.status_code == 200
    assert created.json() == {
        "id": created.json()["id"],
        "item_key": "t:701:e:1701",
        **{key: value for key, value in payload.items() if key != "expected_revision"},
        "added_at": "2026-07-13T09:00:00",
        "revision": 1,
        "deleted": False,
    }

    updated = client.put(
        "/api/dig-queue",
        json={
            **payload,
            "event_title": "Updated event title",
            "view": "analogue",
            "added_at": "2026-07-13T10:00:00Z",
            "expected_revision": 1,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]
    assert updated.json()["event_title"] == "Updated event title"
    assert updated.json()["view"] == "analogue"
    assert updated.json()["revision"] == 2

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
            "expected_revision": None,
        },
    )
    assert created.status_code == 200
    assert created.json()["item_key"] == "t:702"

    deleted = client.delete("/api/dig-queue/t%3A702", params={"expected_revision": 1})
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "item_key": "t:702", "revision": 2}

    repeated = client.delete("/api/dig-queue/t%3A702", params={"expected_revision": 1})
    assert repeated.status_code == 200
    assert repeated.json() == {"deleted": True, "item_key": "t:702", "revision": 2}
    tombstone = next(item for item in client.get("/api/dig-queue").json() if item["item_key"] == "t:702")
    assert tombstone["deleted"] is True
    assert tombstone["revision"] == 2


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
            "expected_revision": None,
        },
    )
    assert saved.status_code == 200
    assert client.delete(
        "/api/dig-queue/t%3A703%3Ae%3A1703",
        params={"expected_revision": saved.json()["revision"]},
    ).status_code == 200

    after_profile = client.get("/api/cognition/profile").json()
    with Session(engine) as session:
        after_marks = list(session.exec(select(CognitionMark)).all())

    assert after_profile == before_profile
    assert after_marks == before_marks


def test_stale_queue_mutations_cannot_delete_or_resurrect_newer_state():
    init_db()
    client = TestClient(api.app)
    payload = {
        "topic_id": 704,
        "topic_name": "Revision guarded queue",
        "event_id": None,
        "event_title": "Revision guarded queue",
        "view": "contrast",
        "added_at": "2026-07-13T13:00:00Z",
        "expected_revision": None,
    }

    created = client.put("/api/dig-queue", json=payload)
    assert created.status_code == 200
    assert created.json()["revision"] == 1

    deleted = client.delete("/api/dig-queue/t%3A704", params={"expected_revision": 1})
    assert deleted.json()["revision"] == 2

    stale_upsert = client.put(
        "/api/dig-queue",
        json={**payload, "event_title": "stale resurrection", "expected_revision": 1},
    )
    assert stale_upsert.status_code == 409
    assert stale_upsert.json()["detail"]["current"]["deleted"] is True
    assert stale_upsert.json()["detail"]["current"]["revision"] == 2

    restored = client.put(
        "/api/dig-queue",
        json={**payload, "event_title": "explicit restore", "expected_revision": 2},
    )
    assert restored.status_code == 200
    assert restored.json()["deleted"] is False
    assert restored.json()["revision"] == 3

    stale_delete = client.delete("/api/dig-queue/t%3A704", params={"expected_revision": 1})
    assert stale_delete.status_code == 409
    assert stale_delete.json()["detail"]["current"]["deleted"] is False
    assert stale_delete.json()["detail"]["current"]["revision"] == 3


def test_concurrent_identical_queue_puts_are_atomic_and_idempotent():
    init_db()
    payload = {
        "topic_id": 705,
        "topic_name": "Concurrent queue",
        "event_id": 1705,
        "event_title": "Same intent",
        "view": "contrast",
        "added_at": "2026-07-13T14:00:00Z",
        "expected_revision": None,
    }

    def save() -> tuple[int, dict]:
        response = TestClient(api.app).put("/api/dig-queue", json=payload)
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: save(), range(2)))

    assert [status for status, _ in results] == [200, 200]
    assert {body["revision"] for _, body in results} == {1}
    matching = [
        item
        for item in TestClient(api.app).get("/api/dig-queue").json()
        if item["item_key"] == "t:705:e:1705"
    ]
    assert len(matching) == 1


def test_retrying_an_applied_upsert_returns_the_same_revision():
    init_db()
    client = TestClient(api.app)
    payload = {
        "topic_id": 706,
        "topic_name": "Retry-safe queue",
        "event_id": None,
        "event_title": "Retry-safe queue",
        "view": "contrast",
        "added_at": "2026-07-13T15:00:00Z",
        "expected_revision": None,
    }

    created = client.put("/api/dig-queue", json=payload)
    retried_create = client.put("/api/dig-queue", json=payload)

    assert created.status_code == 200
    assert retried_create.status_code == 200
    assert retried_create.json() == created.json()

    updated_payload = {
        **payload,
        "event_title": "Applied exactly once",
        "added_at": "2026-07-13T15:05:00Z",
        "expected_revision": 1,
    }
    updated = client.put("/api/dig-queue", json=updated_payload)
    retried_update = client.put("/api/dig-queue", json=updated_payload)

    assert updated.status_code == 200
    assert retried_update.status_code == 200
    assert retried_update.json() == updated.json()
    assert updated.json()["revision"] == 2


def test_dig_queue_rejects_blank_names_and_mismatched_item_keys():
    init_db()
    client = TestClient(api.app)
    invalid = client.put(
        "/api/dig-queue",
        json={
            "topic_id": 707,
            "topic_name": "   ",
            "event_id": None,
            "event_title": "   ",
            "view": "contrast",
            "added_at": "2026-07-13T16:00:00Z",
            "expected_revision": None,
        },
    )

    assert invalid.status_code == 422

    created = client.put(
        "/api/dig-queue",
        json={
            "topic_id": 707,
            "topic_name": "Validated queue",
            "event_id": None,
            "event_title": "Validated queue",
            "view": "contrast",
            "added_at": "2026-07-13T16:00:00Z",
            "expected_revision": None,
        },
    )
    assert created.status_code == 200

    mismatched_delete = client.delete(
        "/api/dig-queue/t%3A707%3Ae%3A999",
        params={"expected_revision": created.json()["revision"]},
    )
    assert mismatched_delete.status_code == 409
