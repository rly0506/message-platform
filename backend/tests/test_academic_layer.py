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

        stored_papers = session.exec(
            select(Paper)
            .join(TopicPaper, TopicPaper.paper_id == Paper.id)
            .where(TopicPaper.topic_id == topic_id)
        ).all()
        assert {paper.openalex_id for paper in stored_papers} == {"W1", "W2"}
        assert session.exec(select(PaperCitation)).one().citing_paper_id != session.exec(select(PaperCitation)).one().cited_paper_id
        assert len(session.exec(select(TopicPaper).where(TopicPaper.topic_id == topic_id)).all()) == 2


def test_run_academic_analysis_uses_crossref_when_openalex_has_no_results(monkeypatch):
    topic_id = _seed_topic(name="Academic Crossref Topic")
    crossref_papers = [
        {
            "openalex_id": "crossref:10.1000/crossref-only",
            "title": "Crossref-only sanctions paper",
            "abstract": "",
            "year": 2022,
            "cited_by_count": 0,
            "authors": ["C. Scholar"],
            "venue": "Journal of Crossref Metadata",
            "concepts": [],
            "doi": "https://doi.org/10.1000/crossref-only",
            "openalex_url": "",
            "url": "https://doi.org/10.1000/crossref-only",
            "referenced_works": [],
            "sources": ["crossref"],
            "source_count": 1,
            "source_links": [
                {"source": "crossref", "url": "https://api.crossref.org/works/10.1000/crossref-only"}
            ],
        }
    ]

    monkeypatch.setattr(academic.openalex, "search_works", lambda query, top_n=30: [])
    monkeypatch.setattr(academic.crossref, "search_works", lambda query, top_n=30: crossref_papers)
    monkeypatch.setattr(academic, "synthesize_academic", lambda topic, papers, edges, schools_data: "summary")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = academic.run_academic_analysis(session, topic, top_n=5)

        assert result["paper_count"] == 1
        assert result["papers"][0]["title"] == "Crossref-only sanctions paper"
        assert result["papers"][0]["sources"] == ["crossref"]
        assert result["papers"][0]["source_count"] == 1
        assert result["papers"][0]["source_links"][0]["source"] == "crossref"
        assert "OpenAlex + Crossref" in result["sort_strategy"]

        stored = session.exec(select(Paper).where(Paper.openalex_id == "crossref:10.1000/crossref-only")).one()
        payload = academic.academic_payload(session, topic)

    assert stored.openalex_id == "crossref:10.1000/crossref-only"
    assert payload["papers"][0]["sources"] == ["crossref"]
    assert payload["papers"][0]["source_links"][0]["url"].endswith("/10.1000/crossref-only")


def test_run_academic_analysis_merges_openalex_and_crossref_by_doi(monkeypatch):
    topic_id = _seed_topic(name="Academic Merge Topic")
    openalex_papers = [
        {
            "openalex_id": "https://openalex.org/W-merge",
            "title": "OpenAlex sanctions paper",
            "abstract": "OpenAlex abstract.",
            "year": 2020,
            "cited_by_count": 42,
            "authors": ["A. Scholar"],
            "venue": "",
            "concepts": [{"name": "Sanctions"}],
            "doi": "https://doi.org/10.1000/merge",
            "openalex_url": "https://openalex.org/W-merge",
            "url": "https://openalex.org/W-merge",
            "referenced_works": [],
            "sources": ["openalex"],
            "source_count": 1,
            "source_links": [{"source": "openalex", "url": "https://openalex.org/W-merge"}],
        }
    ]
    crossref_papers = [
        {
            "openalex_id": "crossref:10.1000/merge",
            "title": "Crossref title should not replace existing title",
            "abstract": "",
            "year": 2020,
            "cited_by_count": 0,
            "authors": ["A. Scholar"],
            "venue": "Crossref Venue",
            "concepts": [],
            "doi": "https://doi.org/10.1000/merge",
            "openalex_url": "",
            "url": "https://doi.org/10.1000/merge",
            "referenced_works": [],
            "sources": ["crossref"],
            "source_count": 1,
            "source_links": [{"source": "crossref", "url": "https://api.crossref.org/works/10.1000/merge"}],
        }
    ]

    monkeypatch.setattr(academic.openalex, "search_works", lambda query, top_n=30: openalex_papers)
    monkeypatch.setattr(academic.crossref, "search_works", lambda query, top_n=30: crossref_papers)
    monkeypatch.setattr(academic, "synthesize_academic", lambda topic, papers, edges, schools_data: "summary")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = academic.run_academic_analysis(session, topic, top_n=5)
        payload = academic.academic_payload(session, topic)

    assert result["paper_count"] == 1
    assert result["papers"][0]["openalex_id"] == "https://openalex.org/W-merge"
    assert result["papers"][0]["venue"] == "Crossref Venue"
    assert result["papers"][0]["sources"] == ["crossref", "openalex"]
    assert payload["papers"][0]["source_count"] == 2
    assert {link["source"] for link in payload["papers"][0]["source_links"]} == {"openalex", "crossref"}


def test_run_academic_analysis_keeps_openalex_when_crossref_fails(monkeypatch):
    topic_id = _seed_topic(name="Academic Crossref Failure Topic")
    openalex_papers = [
        {
            "openalex_id": "https://openalex.org/W-openalex-only",
            "title": "OpenAlex-only after Crossref failure",
            "abstract": "OpenAlex abstract.",
            "year": 2021,
            "cited_by_count": 12,
            "authors": ["O. Scholar"],
            "venue": "OpenAlex Venue",
            "concepts": [{"name": "Security studies"}],
            "doi": "https://doi.org/10.1000/openalex-only",
            "openalex_url": "https://openalex.org/W-openalex-only",
            "url": "https://openalex.org/W-openalex-only",
            "referenced_works": [],
            "sources": ["openalex"],
            "source_count": 1,
            "source_links": [{"source": "openalex", "url": "https://openalex.org/W-openalex-only"}],
        }
    ]

    monkeypatch.setattr(academic.openalex, "search_works", lambda query, top_n=30: openalex_papers)

    def raise_crossref_error(query, top_n=30):
        raise RuntimeError("Crossref temporarily unavailable")

    monkeypatch.setattr(academic.crossref, "search_works", raise_crossref_error)
    monkeypatch.setattr(academic, "synthesize_academic", lambda topic, papers, edges, schools_data: "summary")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = academic.run_academic_analysis(session, topic, top_n=5)
        payload = academic.academic_payload(session, topic)

    assert result["paper_count"] == 1
    assert result["papers"][0]["title"] == "OpenAlex-only after Crossref failure"
    assert result["papers"][0]["sources"] == ["openalex"]
    assert payload["papers"][0]["source_count"] == 1
    assert payload["papers"][0]["source_links"][0]["source"] == "openalex"


def test_run_academic_analysis_synthesize_timeout_degrades_and_still_persists(monkeypatch):
    """#9: LLM 综述超时不能中断 —— 降级为 warning, 论文/引用图照常落库, persist 不跳过。"""
    topic_id = _seed_topic()
    papers = [
        {
            "openalex_id": "W1", "title": "Paper one", "abstract": "x", "year": 2015,
            "cited_by_count": 100, "authors": ["A"], "venue": "J",
            "concepts": [{"name": "Sanctions"}], "url": "https://example.com/w1",
            "referenced_works": [],
        },
        {
            "openalex_id": "W2", "title": "Paper two", "abstract": "y", "year": 2018,
            "cited_by_count": 20, "authors": ["B"], "venue": "J",
            "concepts": [{"name": "Sanctions"}], "url": "https://example.com/w2",
            "referenced_works": ["W1"],
        },
    ]
    edges = [{"citing_openalex_id": "W2", "cited_openalex_id": "W1"}]
    monkeypatch.setattr(academic.openalex, "search_works", lambda query, top_n=30: papers)
    monkeypatch.setattr(academic.openalex, "converged_citation_edges", lambda values: edges)

    # 综述步骤模拟 ReadTimeout。
    def boom(topic, papers, edges, schools_data):
        raise TimeoutError("read timed out")
    monkeypatch.setattr(academic, "synthesize_academic", boom)

    steps = []  # 捕获 on_step 推进
    def on_step(key, status, details=None):
        steps.append((key, status))

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = academic.run_academic_analysis(session, topic, top_n=2, on_step=on_step)

        # 综述降级: 空摘要, 但流程没崩。
        assert result["summary_md"] == ""
        # persist 仍跑: 论文落库。
        stored = session.exec(
            select(Paper)
            .join(TopicPaper, TopicPaper.paper_id == Paper.id)
            .where(TopicPaper.topic_id == topic_id)
        ).all()
        assert {p.openalex_id for p in stored} == {"W1", "W2"}
        # 步骤终态: synthesize=warning, persist=done, 没有卡在 running/pending。
        assert ("synthesize", "warning") in steps
        assert ("persist", "done") in steps


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


def test_synthesize_academic_consensus_requires_cited_review_format(monkeypatch):
    captured = {}
    papers = [
        {
            "openalex_id": "https://openalex.org/W1",
            "title": "Cited paper",
            "abstract": "Evidence about sanctions.",
            "year": 2020,
            "cited_by_count": 5,
            "authors": ["A. Scholar"],
            "venue": "Security Journal",
            "doi": "https://doi.org/10.123/example",
            "openalex_url": "https://openalex.org/W1",
            "concepts": [{"name": "Sanctions"}],
        }
    ]
    schools_data = academic.analyze_schools(papers, [])

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        captured["system"] = system
        return "summary"

    monkeypatch.setattr(academic.llm, "chat", fake_chat)

    topic = Topic(name="Prompt Topic", description="", queries=["Prompt Topic"])
    academic.synthesize_academic_consensus(topic, papers, [], schools_data)

    assert "学界综述" in captured["prompt"]
    assert "参考文献" in captured["prompt"]
    assert "[W1]" in captured["prompt"]
    assert "https://doi.org/10.123/example" in captured["prompt"]
    assert "引用每一条判断" in captured["prompt"]
    assert "不编造文献" in captured["system"]


def test_synthesize_academic_consensus_describes_multi_source_sample(monkeypatch):
    captured = {}
    papers = [
        {
            "openalex_id": "https://openalex.org/W1",
            "title": "OpenAlex paper",
            "abstract": "Evidence from OpenAlex.",
            "year": 2020,
            "cited_by_count": 12,
            "authors": ["A. Scholar"],
            "venue": "Security Journal",
            "doi": "https://doi.org/10.1000/openalex",
            "openalex_url": "https://openalex.org/W1",
            "sources": ["openalex"],
            "source_links": [{"source": "openalex", "url": "https://openalex.org/W1"}],
            "concepts": [{"name": "Sanctions"}],
        },
        {
            "openalex_id": "crossref:10.1000/crossref",
            "title": "Crossref paper",
            "abstract": "Evidence from Crossref.",
            "year": 2021,
            "cited_by_count": 0,
            "authors": ["C. Scholar"],
            "venue": "Crossref Journal",
            "doi": "https://doi.org/10.1000/crossref",
            "openalex_url": "",
            "sources": ["crossref"],
            "source_links": [{"source": "crossref", "url": "https://api.crossref.org/works/10.1000%2Fcrossref"}],
            "concepts": [],
        },
    ]
    schools_data = academic.analyze_schools(papers, [])

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        return "summary"

    monkeypatch.setattr(academic.llm, "chat", fake_chat)

    topic = Topic(name="Prompt Topic", description="", queries=["Prompt Topic"])
    academic.synthesize_academic_consensus(topic, papers, [], schools_data)

    assert "OpenAlex + Crossref" in captured["prompt"]
    assert "样本来源" in captured["prompt"]
    assert "只使用样本内部互引" in captured["prompt"]
    assert "OpenAlex top-N" not in captured["prompt"]
    assert "OpenAlex 学术论文样本" not in captured["prompt"]


def test_academic_payload_exposes_citation_metadata_and_readable_literature_network():
    topic_id = _seed_topic(name="Academic Citation Metadata Topic")

    with Session(engine) as session:
        cited = Paper(
            openalex_id="https://openalex.org/W1",
            title="Foundational sanctions paper",
            abstract="",
            year=2018,
            cited_by_count=100,
            authors=["A"],
            venue="Security Journal",
            concepts=[{"name": "Sanctions"}],
            url="https://example.com/w1",
            doi="https://doi.org/10.1000/w1",
            openalex_url="https://openalex.org/W1",
        )
        citing = Paper(
            openalex_id="https://openalex.org/W2",
            title="Follow-up sanctions paper",
            abstract="",
            year=2021,
            cited_by_count=20,
            authors=["B"],
            venue="Policy Journal",
            concepts=[{"name": "Sanctions"}],
            url="https://example.com/w2",
            doi="10.1000/w2",
            openalex_url="https://openalex.org/W2",
        )
        session.add(cited)
        session.add(citing)
        session.commit()
        session.refresh(cited)
        session.refresh(citing)
        session.add(TopicPaper(topic_id=topic_id, paper_id=cited.id, relevance=1.0))
        session.add(TopicPaper(topic_id=topic_id, paper_id=citing.id, relevance=1.0))
        session.add(PaperCitation(citing_paper_id=citing.id, cited_paper_id=cited.id))
        topic = session.get(Topic, topic_id)
        session.commit()

        payload = academic.academic_payload(session, topic)

    paper = {item["openalex_id"]: item for item in payload["papers"]}
    assert paper["https://openalex.org/W1"]["doi"] == "https://doi.org/10.1000/w1"
    assert paper["https://openalex.org/W1"]["citation_key"] == "W1"
    assert "A" in paper["https://openalex.org/W1"]["citation"]
    assert payload["literature_network"]["nodes"][0]["citation_key"] in {"W1", "W2"}
    assert payload["literature_network"]["edges"] == [
        {
            "citing_openalex_id": "https://openalex.org/W2",
            "cited_openalex_id": "https://openalex.org/W1",
            "citing_title": "Follow-up sanctions paper",
            "cited_title": "Foundational sanctions paper",
            "relation": "cites",
        }
    ]


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
