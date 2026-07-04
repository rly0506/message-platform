from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.db import CrossSynthesis, SearchJob, SentimentPost, SourceFraming, TimelineEvent, Topic, engine, init_db
from app.services import search_service


def test_gather_voices_collects_existing_media_academic_and_sentiment_outputs():
    from app.pipeline import cross_synthesis

    topic_id = _seed_topic("Cross Voice Topic")
    with Session(engine) as session:
        session.add(
            TimelineEvent(
                topic_id=topic_id,
                date=datetime(2026, 6, 1),
                title_zh="冲突升级",
                summary_zh="媒体时间线认为冲突先由军事行动升级。",
                article_ids=[1, 2],
            )
        )
        session.add(
            SourceFraming(
                topic_id=topic_id,
                party="国际媒体",
                stance="强调升级风险",
                summary_zh="媒体聚焦即时风险和各方回应。",
                article_ids=[1],
            )
        )
        session.add(
            SearchJob(
                id="academic-cross",
                query="academic:Cross Voice Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "academic_analysis"},
                result={"summary_md": "学界认为这是长期敌对关系的阶段性爆发。"},
            )
        )
        session.add(
            SentimentPost(
                topic_id=topic_id,
                platform="reddit",
                subreddit="worldnews",
                title="People think this is WW3",
                author="commenter",
                score=88,
                num_comments=40,
                url="https://reddit.com/thread",
                created_utc="1760000000",
                selftext_snippet="Mostly panic, some useful logistics comments.",
            )
        )
        session.add(
            SearchJob(
                id="sentiment-cross",
                query="sentiment:Cross Voice Topic",
                status="done",
                steps=[],
                payload={"topic_id": topic_id, "kind": "sentiment_analysis"},
                result={"summary_md": "民间情绪以恐慌和站队为主，高赞不等于事实。"},
            )
        )
        session.commit()

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        voices = cross_synthesis.gather_voices(session, topic)

    assert voices["available_voices"] == ["media", "academic", "sentiment"]
    assert voices["media"]["available"] is True
    assert voices["media"]["timeline"][0]["title_zh"] == "冲突升级"
    assert voices["media"]["framing"][0]["party"] == "国际媒体"
    assert voices["academic"]["summary_md"].startswith("学界认为")
    assert voices["sentiment"]["summary_md"].startswith("民间情绪")
    assert voices["sentiment"]["top_posts"][0]["score"] == 88


def test_gather_voices_marks_missing_voices_without_crashing():
    from app.pipeline import cross_synthesis

    topic_id = _seed_topic("Only Topic")

    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        voices = cross_synthesis.gather_voices(session, topic)

    assert voices["available_voices"] == []
    assert voices["media"]["available"] is False
    assert voices["media"]["note"] == "该声部暂无数据"
    assert voices["academic"]["note"] == "该声部暂无数据"
    assert voices["sentiment"]["note"] == "该声部暂无数据"


def test_cross_synthesize_prompt_requires_five_sections_and_critical_framing(monkeypatch):
    from app.pipeline import cross_synthesis

    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        captured["system"] = system
        return "## 三方共识\n## 三方矛盾\n## 各自盲区\n## 机制重建\n## 批判提示"

    monkeypatch.setattr(cross_synthesis.llm, "chat", fake_chat)
    topic = Topic(id=1, name="美伊战争")
    voices = {
        "available_voices": ["media", "academic", "sentiment"],
        "media": {"available": True, "timeline": [{"title_zh": "冲突升级"}], "framing": []},
        "academic": {"available": True, "summary_md": "长期敌对关系。"},
        "sentiment": {"available": True, "summary_md": "高赞不等于事实。", "top_posts": []},
    }

    result = cross_synthesis.cross_synthesize(topic, voices)

    assert "三方共识" in result
    prompt = captured["prompt"]
    assert "三方共识" in prompt
    assert "三方矛盾" in prompt
    assert "各自盲区" in prompt
    assert "机制重建" in prompt
    assert "分析机制与因果，不做道德归责" in prompt
    assert "批判提示" in prompt
    assert "民间情绪" in prompt and "非事实源" in prompt


def test_cross_synthesize_prompt_notes_missing_voices(monkeypatch):
    from app.pipeline import cross_synthesis

    captured = {}

    def fake_chat(model, prompt, max_tokens, system):
        captured["prompt"] = prompt
        return "only media summary"

    monkeypatch.setattr(cross_synthesis.llm, "chat", fake_chat)
    topic = Topic(id=1, name="Only Media")
    voices = {
        "available_voices": ["media"],
        "media": {"available": True, "timeline": [], "framing": [{"party": "媒体"}]},
        "academic": {"available": False, "note": "该声部暂无数据", "summary_md": ""},
        "sentiment": {"available": False, "note": "该声部暂无数据", "summary_md": "", "top_posts": []},
    }

    cross_synthesis.cross_synthesize(topic, voices)

    assert "仅基于现有 1 方" in captured["prompt"]
    assert "学界：该声部暂无数据" in captured["prompt"]
    assert "民间：该声部暂无数据" in captured["prompt"]


def test_cross_synthesis_table_round_trips_in_isolated_db():
    topic_id = _seed_topic("Cross Table Topic")

    with Session(engine) as session:
        row = CrossSynthesis(
            topic_id=topic_id,
            content_md="## consensus\nshared points",
            voices_used=["media", "academic"],
            generated_at=datetime(2026, 6, 27, 9, 0, 0),
        )
        session.add(row)
        session.commit()

        stored = session.exec(
            select(CrossSynthesis).where(CrossSynthesis.topic_id == topic_id)
        ).one()

    assert stored.content_md == "## consensus\nshared points"
    assert stored.voices_used == ["media", "academic"]


def test_run_cross_synthesis_job_gathers_synthesizes_and_persists(monkeypatch):
    from app import topic_ops
    from app.pipeline import academic, sentiment
    from app.pipeline import cross_synthesis

    topic_id = _seed_topic("Cross Job Topic")
    job = SearchJob(
        id="cross-job",
        query="cross-synthesis:Cross Job Topic",
        status="queued",
        steps=search_service.cross_synthesis_steps(refresh_voices=True),
        payload={"topic_id": topic_id, "kind": "cross_synthesis", "refresh_voices": True},
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()

    voices = {
        "available_voices": ["media", "sentiment"],
        "media": {"available": True, "timeline": [], "framing": []},
        "academic": {"available": False, "note": "missing", "summary_md": ""},
        "sentiment": {"available": True, "summary_md": "public mood", "top_posts": []},
    }
    monkeypatch.setattr(cross_synthesis, "gather_voices", lambda session, topic: voices)
    monkeypatch.setattr(
        cross_synthesis,
        "cross_synthesize",
        lambda topic, gathered: "## cross synthesis\ncontent",
    )
    monkeypatch.setattr(topic_ops, "run_deep_analysis", lambda session, topic, enrich_limit: {"ok": True})
    monkeypatch.setattr(academic, "run_academic_analysis", lambda session, topic, top_n: {"ok": True})
    monkeypatch.setattr(sentiment, "run_sentiment_analysis", lambda session, topic, limit: {"ok": True})

    search_service.run_cross_synthesis_job("cross-job", topic_id, refresh_voices=True)

    with Session(engine) as session:
        saved_job = session.get(SearchJob, "cross-job")
        saved_rows = session.exec(
            select(CrossSynthesis).where(CrossSynthesis.topic_id == topic_id)
        ).all()

    assert saved_job.status == "done"
    assert [step["status"] for step in saved_job.steps] == ["done", "done", "done", "done", "done", "done"]
    assert saved_job.result["content_md"] == "## cross synthesis\ncontent"
    assert saved_job.result["voices_used"] == ["media", "sentiment"]
    assert saved_job.result["chain"]["media"]["status"] == "done"
    assert saved_job.result["chain"]["academic"]["status"] == "done"
    assert saved_job.result["chain"]["sentiment"]["status"] == "done"
    assert len(saved_rows) == 1
    assert saved_rows[0].content_md == "## cross synthesis\ncontent"


def test_run_cross_synthesis_job_reuse_voices_skips_voice_reruns(monkeypatch):
    """refresh_voices=False(深度分析 bundle 内): 不重跑三声部, 只 gather/synth/persist, 3 步。"""
    from app import topic_ops
    from app.pipeline import academic, cross_synthesis, sentiment

    topic_id = _seed_topic("Reuse Voices Topic")
    job = SearchJob(
        id="cross-reuse-job",
        query="cross-synthesis:Reuse Voices Topic",
        status="queued",
        steps=search_service.cross_synthesis_steps(refresh_voices=False),
        payload={"topic_id": topic_id, "kind": "cross_synthesis", "refresh_voices": False},
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()

    voices = {
        "available_voices": ["media", "sentiment"],
        "media": {"available": True, "timeline": [], "framing": []},
        "academic": {"available": False, "note": "missing", "summary_md": ""},
        "sentiment": {"available": True, "summary_md": "public mood", "top_posts": []},
    }
    monkeypatch.setattr(cross_synthesis, "gather_voices", lambda session, topic: voices)
    monkeypatch.setattr(
        cross_synthesis, "cross_synthesize", lambda topic, gathered: "## cross\nreused"
    )
    # 若这三个被调用即失败 —— 证明轻量路径确实没重跑声部。
    def _boom(*a, **k):
        raise AssertionError("voice re-run must NOT happen when refresh_voices=False")
    monkeypatch.setattr(topic_ops, "run_deep_analysis", _boom)
    monkeypatch.setattr(academic, "run_academic_analysis", _boom)
    monkeypatch.setattr(sentiment, "run_sentiment_analysis", _boom)

    search_service.run_cross_synthesis_job("cross-reuse-job", topic_id, refresh_voices=False)

    with Session(engine) as session:
        saved_job = session.get(SearchJob, "cross-reuse-job")
        saved_rows = session.exec(
            select(CrossSynthesis).where(CrossSynthesis.topic_id == topic_id)
        ).all()

    assert saved_job.status == "done"
    # 只有 3 步, 全 done。
    assert [step["key"] for step in saved_job.steps] == ["gather", "synthesize", "persist"]
    assert [step["status"] for step in saved_job.steps] == ["done", "done", "done"]
    assert saved_job.result["content_md"] == "## cross\nreused"
    # chain 为空(没跑声部层)。
    assert saved_job.result.get("chain") == {}
    assert len(saved_rows) == 1


def test_run_cross_synthesis_job_chains_voice_layers_and_continues_after_failure(monkeypatch):
    from app import topic_ops
    from app.pipeline import academic, cross_synthesis, sentiment

    topic_id = _seed_topic("Cross Chain Topic")
    job = SearchJob(
        id="cross-chain-job",
        query="cross-synthesis:Cross Chain Topic",
        status="queued",
        steps=search_service.cross_synthesis_steps(refresh_voices=True),
        payload={"topic_id": topic_id, "kind": "cross_synthesis", "refresh_voices": True},
    )
    with Session(engine) as session:
        session.add(job)
        session.commit()

    calls = []

    def fake_deep(session, topic, enrich_limit, on_step=None):
        calls.append("media")
        return {"analysis": "media ok"}

    def fake_academic(session, topic, top_n, on_step=None):
        calls.append("academic")
        raise RuntimeError("OpenAlex timeout")

    def fake_sentiment(session, topic, limit, on_step=None):
        calls.append("sentiment")
        return {"summary_md": "sentiment ok", "posts": [{"title": "post"}]}

    def fake_cross(session, topic, on_step=None):
        calls.append("cross")
        if on_step:
            on_step("gather", "done", {"voices_used": ["media", "sentiment"]})
            on_step("synthesize", "done")
            on_step("persist", "done")
        return {
            "topic_id": topic.id,
            "topic_name": topic.name,
            "content_md": "## chained cross",
            "voices_used": ["media", "sentiment"],
            "generated_at": None,
        }

    monkeypatch.setattr(topic_ops, "run_deep_analysis", fake_deep)
    monkeypatch.setattr(academic, "run_academic_analysis", fake_academic)
    monkeypatch.setattr(sentiment, "run_sentiment_analysis", fake_sentiment)
    monkeypatch.setattr(cross_synthesis, "run_cross_synthesis", fake_cross)

    search_service.run_cross_synthesis_job("cross-chain-job", topic_id, refresh_voices=True)

    with Session(engine) as session:
        saved_job = session.get(SearchJob, "cross-chain-job")

    assert calls == ["media", "academic", "sentiment", "cross"]
    assert saved_job.status == "done"
    assert saved_job.error == ""
    assert saved_job.result["content_md"] == "## chained cross"
    assert saved_job.result["voices_used"] == ["media", "sentiment"]
    assert saved_job.result["chain"]["media"]["status"] == "done"
    assert saved_job.result["chain"]["academic"]["status"] == "failed"
    assert "OpenAlex timeout" in saved_job.result["chain"]["academic"]["error"]
    assert saved_job.result["chain"]["sentiment"]["status"] == "done"
    assert [step["key"] for step in saved_job.steps] == ["media", "academic", "sentiment", "gather", "synthesize", "persist"]
    assert [step["status"] for step in saved_job.steps] == ["done", "failed", "done", "done", "done", "done"]


def test_cross_synthesis_api_endpoints_use_background_job_and_return_latest_payload(monkeypatch):
    topic_id = _seed_topic("Cross API Topic")
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

    response = client.post(f"/api/topics/{topic_id}/cross-synthesis/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert [step["key"] for step in body["steps"]] == ["gather", "synthesize", "persist"]
    assert started == [(search_service.run_cross_synthesis_job, (body["id"], topic_id, False), True)]

    refresh_response = client.post(f"/api/topics/{topic_id}/cross-synthesis/jobs", json={"refresh_voices": True})
    refresh_body = refresh_response.json()
    assert [step["key"] for step in refresh_body["steps"]] == ["media", "academic", "sentiment", "gather", "synthesize", "persist"]
    assert started[-1] == (search_service.run_cross_synthesis_job, (refresh_body["id"], topic_id, True), True)

    with Session(engine) as session:
        session.add(
            CrossSynthesis(
                topic_id=topic_id,
                content_md="old cross synthesis",
                voices_used=["media"],
                generated_at=datetime(2026, 1, 1, 10, 0, 0),
            )
        )
        session.add(
            CrossSynthesis(
                topic_id=topic_id,
                content_md="new cross synthesis",
                voices_used=["media", "academic", "sentiment"],
                generated_at=datetime(2026, 1, 1, 10, 5, 0),
            )
        )
        session.commit()

    payload = client.get(f"/api/topics/{topic_id}/cross-synthesis").json()

    assert payload["topic_id"] == topic_id
    assert payload["topic_name"] == "Cross API Topic"
    assert payload["content_md"] == "new cross synthesis"
    assert payload["voices_used"] == ["media", "academic", "sentiment"]
    assert payload["generated_at"] is not None


def test_cross_synthesis_view_returns_empty_payload_before_job_runs():
    topic_id = _seed_topic("Cross Empty Topic")

    payload = TestClient(api.app).get(f"/api/topics/{topic_id}/cross-synthesis").json()

    assert payload["topic_id"] == topic_id
    assert payload["topic_name"] == "Cross Empty Topic"
    assert payload["content_md"] == ""
    assert payload["voices_used"] == []
    assert payload["generated_at"] is None


def _seed_topic(name: str) -> int:
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, description="三方对照测试", queries=[name])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        return topic.id
