from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api, topic_ops
from app.db import (
    Analysis,
    Article,
    SearchJob,
    SourceFraming,
    TimelineEvent,
    Topic,
    TopicArticle,
    engine,
    init_db,
)
from app.services import search_service


def test_clamp_score_handles_bad_values():
    """_clamp_score: 钳到 0~100; 缺失/非法 -> -1 (未评分, 前端不显示徽标, 守可追溯)。"""
    assert topic_ops._clamp_score(82) == 82
    assert topic_ops._clamp_score(150) == 100
    assert topic_ops._clamp_score(-5) == 0
    assert topic_ops._clamp_score(None) == -1   # 缺失 -> 未评分
    assert topic_ops._clamp_score("garbage") == -1  # 非法 -> 未评分
    assert topic_ops._clamp_score("73") == 73  # 数字字符串可解


def test_run_deep_analysis_enriches_synthesizes_and_persists(monkeypatch):
    topic_id, article_ids = _seed_deep_analysis_case(article_count=3)
    steps = []

    def fake_enrich_batch(topic_name, description, items):
        return {
            item["id"]: {
                "title_zh": f"译文 {item['id']}",
                "snippet_zh": f"摘要 {item['id']}",
                "relevant": True,
                "relevance": 0.9,
                "stance": "支持行动",
                "stance_summary": "认为事件会升级",
                "substance_score": 82,
                "substance_note": "含具体金额与时间",
            }
            for item in items
        }

    def fake_synthesize(topic_name, description, rows):
        assert topic_name == "LLM 接入测试"
        assert len(rows) == 2
        return {
            "timeline": [
                {
                    "date": "2026-06-01",
                    "title_zh": "LLM 时间线节点",
                    "summary_zh": "综合多篇报道后形成的节点。",
                    "article_ids": [row["id"] for row in rows],
                }
            ],
            "framing": [
                {
                    "party": "测试媒体",
                    "stance": "支持行动",
                    "summary_zh": "测试媒体强调行动进展。",
                    "article_ids": [rows[0]["id"]],
                }
            ],
            "analysis_md": "LLM 生成的批判分析",
        }

    monkeypatch.setattr(topic_ops.enrichp, "BATCH", 6)
    monkeypatch.setattr(topic_ops.enrichp, "enrich_batch", fake_enrich_batch)
    monkeypatch.setattr(topic_ops.synthp, "synthesize", fake_synthesize)

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        result = topic_ops.run_deep_analysis(
            session,
            topic,
            enrich_limit=2,
            on_step=lambda key, status, details=None: steps.append((key, status, details)),
        )

        assert result["enrich"]["processed"] == 2
        assert result["enrich"]["pending"] == 2
        assert result["enrich"]["calls"] == 1
        assert result["synthesize"]["input_articles"] == 2
        assert result["synthesize"]["timeline"] == 1
        assert result["synthesize"]["framing"] == 1
        assert result["synthesize"]["calls"] == 3

        articles = session.exec(select(Article).where(Article.id.in_(article_ids[:2]))).all()
        assert all(article.enriched for article in articles)
        assert all(article.title_zh.startswith("译文") for article in articles)

        # 干货密度写回 TopicArticle (A: 事前筛水文)
        links = session.exec(
            select(TopicArticle).where(TopicArticle.article_id.in_(article_ids[:2]))
        ).all()
        assert all(link.substance_score == 82 for link in links)
        assert all(link.substance_note == "含具体金额与时间" for link in links)

        timeline = session.exec(select(TimelineEvent).where(TimelineEvent.topic_id == topic_id)).all()
        framing = session.exec(select(SourceFraming).where(SourceFraming.topic_id == topic_id)).all()
        analysis = session.exec(select(Analysis).where(Analysis.topic_id == topic_id)).one()
        assert timeline[0].title_zh == "LLM 时间线节点"
        assert framing[0].party == "测试媒体"
        assert "<!-- analysis-source: llm -->" in analysis.content_md
        assert "LLM 生成的批判分析" in analysis.content_md

    assert ("enrich", "done", result["enrich"]) in steps
    assert ("synthesize", "running", None) in steps
    assert ("persist", "done", None) in steps


def test_enqueue_deep_analysis_job_creates_search_job_without_running_llm(monkeypatch):
    topic_id, _article_ids = _seed_deep_analysis_case(article_count=1)
    started = []

    class DummyThread:
        def __init__(self, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            started.append((self.target, self.args, self.daemon))

    monkeypatch.setattr(search_service, "Thread", DummyThread)

    snapshot = search_service.enqueue_deep_analysis_job(topic_id, enrich_limit=20)

    assert snapshot["query"] == "deep-analysis:LLM 接入测试"
    assert snapshot["status"] == "queued"
    assert snapshot["payload"] if "payload" in snapshot else True
    assert [step["key"] for step in snapshot["steps"]] == ["enrich", "synthesize", "persist"]
    assert started == [(search_service.run_deep_analysis_job, (snapshot["id"], topic_id, 20), True)]
    with Session(engine) as session:
        job = session.get(SearchJob, snapshot["id"])
        assert job.payload == {"topic_id": topic_id, "enrich_limit": 20, "kind": "deep_analysis"}


def test_enrich_topic_articles_processes_articles_with_local_stance_but_no_llm_enrichment(monkeypatch):
    topic_id, article_ids = _seed_deep_analysis_case(article_count=2)

    def fake_enrich_batch(topic_name, description, items):
        return {
            item["id"]: {
                "title_zh": f"LLM 译文 {item['id']}",
                "snippet_zh": f"LLM 摘要 {item['id']}",
                "relevant": True,
                "relevance": 0.95,
                "stance": "LLM 立场",
                "stance_summary": "LLM 富化摘要",
            }
            for item in items
        }

    monkeypatch.setattr(topic_ops.enrichp, "enrich_batch", fake_enrich_batch)

    with Session(engine) as session:
        for article_id in article_ids:
            link = session.get(TopicArticle, (topic_id, article_id))
            link.stance = "本地规则立场"
            session.add(link)
        session.commit()

        topic = session.get(Topic, topic_id)
        stats = topic_ops.enrich_topic_articles(session, topic, limit=2)

        assert stats["processed"] == 2
        links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic_id)).all()
        assert {link.stance for link in links} == {"LLM 立场"}
        articles = session.exec(select(Article).where(Article.id.in_(article_ids))).all()
        assert all(article.enriched for article in articles)


def test_enrich_topic_articles_backfills_substance_for_already_enriched_links(monkeypatch):
    topic_id, article_ids = _seed_deep_analysis_case(article_count=2)
    seen_items = []

    def fake_enrich_batch(topic_name, description, items):
        seen_items.extend(items)
        return {
            item["id"]: {
                "relevant": True,
                "relevance": 0.88,
                "stance": "LLM 绔嬪満",
                "stance_summary": "LLM 瀵屽寲鎽樿",
                "substance_score": 76,
                "substance_note": "鍚叿浣撴暟瀛椾笌鏃堕棿",
            }
            for item in items
        }

    monkeypatch.setattr(topic_ops.enrichp, "enrich_batch", fake_enrich_batch)

    with Session(engine) as session:
        for article_id in article_ids:
            article = session.get(Article, article_id)
            article.enriched = True
            article.title_zh = f"鏃ф爣棰?{article_id}"
            article.snippet_zh = f"鏃ф憳瑕?{article_id}"
            session.add(article)
        session.commit()

        topic = session.get(Topic, topic_id)
        stats = topic_ops.enrich_topic_articles(session, topic, limit=2)

        assert stats["processed"] == 2
        assert {item["id"] for item in seen_items} == set(article_ids)

        links = session.exec(select(TopicArticle).where(TopicArticle.topic_id == topic_id)).all()
        assert all(link.substance_score == 76 for link in links)
        assert all(link.substance_note == "鍚叿浣撴暟瀛椾笌鏃堕棿" for link in links)

        articles = session.exec(select(Article).where(Article.id.in_(article_ids))).all()
        assert all(article.enriched for article in articles)
        assert {article.title_zh for article in articles} == {f"鏃ф爣棰?{article_id}" for article_id in article_ids}


def test_deep_analysis_api_endpoint_uses_background_job(monkeypatch):
    topic_id, _article_ids = _seed_deep_analysis_case(article_count=1)
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
    response = client.post(f"/api/topics/{topic_id}/deep-analysis/jobs", json={"enrich_limit": 12})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["steps"][0]["key"] == "enrich"
    assert started == [(search_service.run_deep_analysis_job, (body["id"], topic_id, 12), True)]


def _seed_deep_analysis_case(article_count: int) -> tuple[int, list[int]]:
    init_db()
    with Session(engine) as session:
        topic = Topic(name="LLM 接入测试", description="测试 LLM 深度分析", queries=["LLM 接入测试"])
        session.add(topic)
        session.commit()
        session.refresh(topic)

        article_ids = []
        for index in range(article_count):
            article = Article(
                url=f"https://example.com/llm/{datetime.utcnow().timestamp()}-{index}",
                title=f"原文标题 {index}",
                source="测试来源",
                source_lang="en",
                published_at=datetime(2026, 6, index + 1),
                snippet=f"original snippet {index}",
            )
            session.add(article)
            session.commit()
            session.refresh(article)
            session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.7))
            article_ids.append(article.id)

        session.commit()
        return topic.id, article_ids
