from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import Project, Topic, engine, init_db


def test_projects_backfill_existing_topics_into_default_projects():
    init_db()
    with Session(engine) as session:
        topic = Topic(name="俄乌战争", description="长期追踪", queries=["俄乌战争"])
        session.add(topic)
        session.commit()

    client = TestClient(api.app)
    response = client.get("/api/projects")

    assert response.status_code == 200
    projects = response.json()
    project = next(item for item in projects if item["name"] == "俄乌战争")
    assert project["name"] == "俄乌战争"
    assert project["topic_count"] == 1
    assert project["topics"][0]["name"] == "俄乌战争"

    with Session(engine) as session:
        saved_topic = session.exec(select(Topic).where(Topic.name == "俄乌战争")).one()
        assert saved_topic.project_id == project["id"]


def test_create_project_and_topic_then_update_archive_and_delete_topic():
    client = TestClient(api.app)

    project_response = client.post("/api/projects", json={
        "name": "俄乌战争研究",
        "description": "围绕俄乌战争管理多个子专题。",
    })

    assert project_response.status_code == 200
    project = project_response.json()
    assert project["name"] == "俄乌战争研究"
    assert project["description"] == "围绕俄乌战争管理多个子专题。"
    assert project["status"] == "active"

    topic_response = client.post("/api/topics", json={
        "project_id": project["id"],
        "name": "俄乌战争前线态势",
        "description": "追踪战线推进、兵力部署和火力消耗。",
        "queries": ["俄乌战争 前线态势", "Russia Ukraine frontline"],
    })

    assert topic_response.status_code == 200
    topic = topic_response.json()
    assert topic["project_id"] == project["id"]
    assert topic["project_name"] == "俄乌战争研究"
    assert topic["queries"] == ["俄乌战争 前线态势", "Russia Ukraine frontline"]

    update_response = client.patch(f"/api/topics/{topic['id']}", json={
        "name": "俄乌战争：前线态势",
        "description": "保留父专题语境的前线变化追踪。",
        "queries": ["俄乌战争 前线态势"],
        "status": "archived",
    })

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "俄乌战争：前线态势"
    assert updated["description"] == "保留父专题语境的前线变化追踪。"
    assert updated["queries"] == ["俄乌战争 前线态势"]
    assert updated["status"] == "archived"
    assert updated["archived_at"]

    delete_response = client.delete(f"/api/topics/{topic['id']}")

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert client.get(f"/api/topics/{topic['id']}").status_code == 404


def test_update_project_archives_project_without_deleting_topics():
    client = TestClient(api.app)
    project = client.post("/api/projects", json={"name": "低空经济"}).json()
    topic = client.post("/api/topics", json={
        "project_id": project["id"],
        "name": "低空经济政策",
        "queries": ["低空经济 政策"],
    }).json()

    response = client.patch(f"/api/projects/{project['id']}", json={
        "description": "暂时归档观察。",
        "status": "archived",
    })

    assert response.status_code == 200
    archived = response.json()
    assert archived["status"] == "archived"
    assert archived["archived_at"]

    topic_response = client.get(f"/api/topics/{topic['id']}")
    assert topic_response.status_code == 200
    assert topic_response.json()["project_id"] == project["id"]


def test_update_topic_allows_project_unlink_with_null():
    init_db()
    client = TestClient(api.app)
    project = client.post("/api/projects", json={"name": "项目解绑测试"}).json()
    topic = client.post("/api/topics", json={
        "project_id": project["id"],
        "name": "项目解绑专题",
        "queries": ["项目解绑专题"],
    }).json()

    response = client.patch(f"/api/topics/{topic['id']}", json={"project_id": None})

    assert response.status_code == 200
    assert response.json()["project_id"] is None


def test_update_topic_rejects_invalid_project_id_without_server_error():
    init_db()
    client = TestClient(api.app)
    topic = client.post("/api/topics", json={
        "name": "非法项目ID更新",
        "queries": ["非法项目ID更新"],
    }).json()

    response = client.patch(f"/api/topics/{topic['id']}", json={"project_id": "not-an-int"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Project id must be an integer"


def test_create_topic_rejects_invalid_project_id_without_server_error():
    init_db()
    client = TestClient(api.app)

    response = client.post("/api/topics", json={
        "project_id": "not-an-int",
        "name": "非法项目ID创建",
        "queries": ["非法项目ID创建"],
    })

    assert response.status_code == 422
    assert response.json()["detail"] == "Project id must be an integer"


def test_topic_update_and_delete_claim_blocking_write_guard(monkeypatch):
    init_db()
    client = TestClient(api.app)
    updated_topic = client.post("/api/topics", json={
        "name": "Guarded topic update",
        "queries": ["guarded topic update"],
    }).json()
    deleted_topic = client.post("/api/topics", json={
        "name": "Guarded topic delete",
        "queries": ["guarded topic delete"],
    }).json()
    claims: list[tuple[int, bool]] = []

    @contextmanager
    def fake_claim(topic_id: int, *, blocking: bool):
        claims.append((topic_id, blocking))
        yield True

    monkeypatch.setattr(api, "claim_topic", fake_claim, raising=False)

    update_response = client.patch(
        f"/api/topics/{updated_topic['id']}",
        json={"description": "Updated while holding the topic guard."},
    )
    delete_response = client.delete(f"/api/topics/{deleted_topic['id']}")

    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert claims == [
        (updated_topic["id"], True),
        (deleted_topic["id"], True),
    ]
