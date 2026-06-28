from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import Paper, PaperCitation, Topic, TopicPaper, engine, init_db
from app.pipeline import academic
from app.services import search_service


def test_checkpoint_named_helpers_delegate_to_academic_core(monkeypatch):
    inverted = {"Iran": [0], "deal": [1]}
    papers = [
        {"openalex_id": "W1", "referenced_works": ["W2"]},
        {"openalex_id": "W2", "referenced_works": []},
    ]
    topic = Topic(name="Named Helper Topic", description="", queries=["Named Helper Topic"])
    schools_data = {"foundational_papers": [], "schools": []}
    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        return "academic summary"

    monkeypatch.setattr(academic.llm, "chat", fake_chat)

    assert academic.rebuild_abstract(inverted) == "Iran deal"
    assert academic.build_citation_graph(papers) == [
        {"citing_openalex_id": "W1", "cited_openalex_id": "W2"}
    ]
    assert academic.synthesize_academic(topic, papers, [], schools_data) == "academic summary"
    assert "Named Helper Topic" in captured["prompt"]


def test_identify_schools_groups_by_shared_concepts_and_marks_foundations():
    papers = [
        {
            "openalex_id": "W1",
            "title": "Foundational sanctions paper",
            "year": 2015,
            "cited_by_count": 100,
            "concepts": [{"name": "Sanctions"}, {"name": "International relations"}],
        },
        {
            "openalex_id": "W2",
            "title": "Sanctions follow-up",
            "year": 2018,
            "cited_by_count": 30,
            "concepts": [{"name": "Sanctions"}],
        },
        {
            "openalex_id": "W3",
            "title": "Tourism view",
            "year": 2016,
            "cited_by_count": 20,
            "concepts": [{"name": "Tourism"}],
        },
    ]
    edges = [
        {"citing_openalex_id": "W2", "cited_openalex_id": "W1"},
        {"citing_openalex_id": "W3", "cited_openalex_id": "W1"},
    ]

    result = academic.analyze_schools(papers, edges)

    assert result["foundational_papers"][0]["openalex_id"] == "W1"
    schools = {school["name"]: school for school in result["schools"]}
    assert "Sanctions" in schools
    assert schools["Sanctions"]["paper_count"] == 2
    assert schools["Tourism"]["paper_count"] == 1


def test_run_academic_analysis_fetches_persists_and_synthesizes(monkeypatch):
    topic_id = _seed_topic()

    papers = [
        {
            "openalex_id": "W1",
            "title": "Foundational Iran nuclear deal paper",
            "abstract": "Study of the Iran nuclear deal.",
            "year": 2015,
            "cited_by_count": 100,
            "authors": ["A"],
            "venue": "Security Journal",
            "concepts": [{"name": "Sanctions"}, {"name": "International relations"}],
            "url": "https://example.com/w1",
            "referenced_works": [],
        },
        {
            "openalex_id": "W2",
            "title": "Follow-up sanctions paper",
            "abstract": "Later debate.",
            "year": 2018,
            "cited_by_count": 20,
            "authors": ["B"],
            "venue": "Policy Journal",
            "concepts": [{"name": "Sanctions"}],
            "url": "https://example.com/w2",
            "referenced_works": ["W1"],
        },
    ]
    edges = [{"citing_openalex_id": "W2", "cited_openalex_id": "W1"}]

    monkeypatch.setattr(academic.openalex, "search_works", lambda query, top_n=30: papers)
    monkeypatch.setattr(academic.openalex, "converged_citation_edges", lambda values: edges)
    monkeypatch.setattr(academic.llm, "chat", lambda model, prompt, max_tokens, system: "## 学界共识\n存在制裁学派。")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = academic.run_academic_analysis(session, topic, top_n=2)

        assert result["paper_count"] == 2
        assert result["edge_count"] == 1
        assert result["summary_md"].startswith("## 学界共识")

        stored_papers = session.exec(select(Paper)).all()
        assert {paper.openalex_id for paper in stored_papers} == {"W1", "W2"}
        assert session.exec(select(PaperCitation)).one().citing_paper_id != session.exec(select(PaperCitation)).one().cited_paper_id
        assert len(session.exec(select(TopicPaper).where(TopicPaper.topic_id == topic_id)).all()) == 2


def test_run_academic_analysis_translates_cjk_topic_before_openalex_search(monkeypatch):
    topic_id = _seed_topic(name="美伊战争")
    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["translation_prompt"] = prompt
        return "US Iran war"

    def fake_search(query, top_n=30):
        captured["search_query"] = query
        captured["top_n"] = top_n
        return []

    monkeypatch.setattr(academic.llm, "chat", fake_chat)
    monkeypatch.setattr(academic.openalex, "search_works", fake_search)
    monkeypatch.setattr(academic, "synthesize_academic", lambda topic, papers, edges, schools_data: "summary")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        academic.run_academic_analysis(session, topic, top_n=7)

    assert captured["search_query"] == "US Iran war"
    assert captured["top_n"] == 7
    assert "美伊战争" in captured["translation_prompt"]


def test_run_academic_analysis_keeps_english_topic_without_translation(monkeypatch):
    topic_id = _seed_topic(name="Iran nuclear deal")
    captured = {}

    def fail_if_translation_called(*args, **kwargs):
        raise AssertionError("English academic topic should not be translated")

    def fake_search(query, top_n=30):
        captured["search_query"] = query
        return []

    monkeypatch.setattr(academic.llm, "chat", fail_if_translation_called)
    monkeypatch.setattr(academic.openalex, "search_works", fake_search)
    monkeypatch.setattr(academic, "synthesize_academic", lambda topic, papers, edges, schools_data: "summary")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        academic.run_academic_analysis(session, topic, top_n=5)

    assert captured["search_query"] == "Iran nuclear deal"


def test_run_academic_analysis_falls_back_to_original_topic_when_translation_fails(monkeypatch):
    topic_id = _seed_topic(name="美伊战争")
    captured = {}

    def raise_translation_error(*args, **kwargs):
        raise RuntimeError("translation unavailable")

    def fake_search(query, top_n=30):
        captured["search_query"] = query
        return []

    monkeypatch.setattr(academic.llm, "chat", raise_translation_error)
    monkeypatch.setattr(academic.openalex, "search_works", fake_search)
    monkeypatch.setattr(academic, "synthesize_academic", lambda topic, papers, edges, schools_data: "summary")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        academic.run_academic_analysis(session, topic, top_n=5)

    assert captured["search_query"] == "美伊战争"


def test_synthesize_academic_consensus_uses_compact_prompt(monkeypatch):
    captured = {}
    papers = [
        {
            "openalex_id": "W1",
            "title": "Compact prompt paper",
            "abstract": "x" * 5000,
            "year": 2020,
            "cited_by_count": 5,
            "authors": ["A"],
            "venue": "Journal",
            "concepts": [{"name": "Sanctions"}, {"name": "Politics"}],
        }
    ]
    schools_data = academic.analyze_schools(papers, [])

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        return "summary"

    monkeypatch.setattr(academic.llm, "chat", fake_chat)

    topic = Topic(name="Prompt Topic", description="", queries=["Prompt Topic"])
    academic.synthesize_academic_consensus(topic, papers, [], schools_data)

    assert "x" * 1000 not in captured["prompt"]
    assert "Compact prompt paper" in captured["prompt"]
    assert len(captured["prompt"]) < 6000


def test_academic_api_endpoints_use_background_job_and_return_payload(monkeypatch):
    topic_id = _seed_topic(name="Academic API Topic")
    started = []

    class DummyThread:
        def __init__(self, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started.append((self.target, self.args, self.daemon))

    monkeypatch.setattr(search_service, "Thread", DummyThread)

    client = TestClient(api.app)
    response = client.post(f"/api/topics/{topic_id}/academic/jobs", json={"top_n": 12})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert [step["key"] for step in body["steps"]] == ["fetch", "graph", "synthesize", "persist"]
    assert started == [(search_service.run_academic_analysis_job, (body["id"], topic_id, 12), True)]

    with Session(engine) as session:
        paper = Paper(
            openalex_id="W-api",
            title="API Paper",
            abstract="",
            year=2020,
            cited_by_count=9,
            authors=["A"],
            venue="Journal",
            concepts=[{"name": "Sanctions"}],
            url="https://example.com/api",
        )
        session.add(paper)
        session.commit()
        session.refresh(paper)
        session.add(TopicPaper(topic_id=topic_id, paper_id=paper.id, relevance=1.0))
        session.commit()

    payload = client.get(f"/api/topics/{topic_id}/academic").json()

    assert payload["topic_id"] == topic_id
    assert payload["papers"][0]["openalex_id"] == "W-api"
    assert payload["graph"]["nodes"][0]["id"] == "W-api"
    assert payload["schools"][0]["name"] == "Sanctions"
    assert "summary_md" in payload


def test_academic_view_returns_latest_academic_job_summary():
    topic_id = _seed_topic(name="Academic Summary Topic")
    older = datetime(2026, 1, 1, 10, 0, 0)
    newer = older + timedelta(minutes=5)

    with Session(engine) as session:
        paper = Paper(
            openalex_id="W-summary",
            title="Summary Paper",
            abstract="",
            year=2021,
            cited_by_count=4,
            authors=["A"],
            venue="Journal",
            concepts=[{"name": "Sanctions"}],
            url="https://example.com/summary",
        )
        session.add(paper)
        session.commit()
        session.refresh(paper)
        session.add(TopicPaper(topic_id=topic_id, paper_id=paper.id, relevance=1.0))
        session.add(
            search_service.SearchJob(
                id="academic-old",
                query="academic:Academic Summary Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "academic_analysis"},
                result={"summary_md": "old summary"},
                created_at=older,
                updated_at=older,
            )
        )
        session.add(
            search_service.SearchJob(
                id="academic-new",
                query="academic:Academic Summary Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "academic_analysis"},
                result={"summary_md": "new summary"},
                created_at=newer,
                updated_at=newer,
            )
        )
        session.commit()

    client = TestClient(api.app)
    payload = client.get(f"/api/topics/{topic_id}/academic").json()

    assert payload["summary_md"] == "new summary"


def _seed_topic(name: str = "Academic Topic") -> int:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, description="学界层测试", queries=[name])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        return topic.id
