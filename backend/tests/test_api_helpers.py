from app import api
from app.db import SearchJob, engine, init_db
from app.services import payloads, search_service
from fastapi import HTTPException
from sqlmodel import Session


def test_attach_event_evidence_adds_article_payloads_and_respects_limit():
    events = [{"title_zh": "节点", "article_ids": [3, 2, 1, 99]}]
    lookup = {
        1: {"id": 1, "title": "third"},
        2: {"id": 2, "title": "second"},
        3: {"id": 3, "title": "first"},
    }

    out = payloads.attach_event_evidence(events, lookup, limit=2)

    assert out[0]["evidence_articles"] == [
        {"id": 3, "title": "first"},
        {"id": 2, "title": "second"},
    ]


def test_clean_snippet_strips_rss_html():
    raw = '<a href="https://example.com">标题</a>&nbsp;&nbsp;<font color="#666">来源</font>'

    assert payloads.clean_snippet(raw) == "标题 来源"


def test_article_payload_includes_report_category():
    topic_article = api.TopicArticle(topic_id=1, article_id=1, relevance=0.8, relevant=True)
    article = api.Article(
        id=1,
        url="https://example.com/a",
        title="油价上涨，美伊战争影响市场",
        source="Reuters",
        snippet="黄金和供应链成为报道重点",
    )

    payload = payloads.article_payload(topic_article, article)

    assert payload["category"] == "影响后果"
    assert "命中阶段词" in payload["category_reason"]


def test_article_evidence_lookup_includes_report_category():
    topic_article = api.TopicArticle(topic_id=1, article_id=1, relevance=0.8, relevant=True)
    article = api.Article(
        id=1,
        url="https://example.com/a",
        title="白宫回应伊朗警告",
        source="BBC",
        snippet="<b>response</b>",
    )

    lookup = payloads.article_evidence_lookup([(topic_article, article)])

    assert lookup[1]["category"] == "各方回应"
    assert lookup[1]["snippet"] == "response"


def test_search_job_snapshot_and_step_updates():
    job_id = "test-job"
    init_db()
    with Session(engine) as session:
        old = session.get(SearchJob, job_id)
        if old:
            session.delete(old)
            session.commit()
        session.add(SearchJob(
            id=job_id,
            query="美伊战争",
            status="queued",
            steps=search_service.search_steps(True),
            payload={"query": "美伊战争"},
        ))
        session.commit()
    try:
        steps = search_service.search_steps(True)
        search_service.set_step(steps, "topic", "running", job_id)

        snapshot = search_service.job_snapshot(job_id)
        assert snapshot["steps"][0]["status"] == "running"

        snapshot["steps"][0]["status"] = "mutated"
        assert search_service.job_snapshot(job_id)["steps"][0]["status"] == "running"
    finally:
        with Session(engine) as session:
            job = session.get(SearchJob, job_id)
            if job:
                session.delete(job)
                session.commit()


def test_mark_interrupted_search_jobs_updates_unfinished_jobs():
    job_id = "test-interrupted-job"
    init_db()
    with Session(engine) as session:
        old = session.get(SearchJob, job_id)
        if old:
            session.delete(old)
            session.commit()
        session.add(SearchJob(
            id=job_id,
            query="中断测试",
            status="running",
            steps=[
                {"key": "topic", "label": "创建/复用专题", "status": "done"},
                {"key": "collect", "label": "采集新闻", "status": "running"},
                {"key": "analyze", "label": "本地分析", "status": "pending"},
            ],
            payload={"query": "中断测试"},
        ))
        session.commit()
    try:
        count = search_service.mark_interrupted_search_jobs({job_id})
        snapshot = search_service.job_snapshot(job_id)

        assert count == 1
        assert snapshot["status"] == "interrupted"
        assert "中断" in snapshot["error"]
        assert snapshot["steps"][0]["status"] == "done"
        assert snapshot["steps"][1]["status"] == "interrupted"
        assert snapshot["steps"][2]["status"] == "interrupted"
    finally:
        with Session(engine) as session:
            job = session.get(SearchJob, job_id)
            if job:
                session.delete(job)
                session.commit()


def test_search_request_from_job_uses_persisted_payload():
    job = SearchJob(
        id="payload-test",
        query="旧查询",
        status="interrupted",
        payload={
            "query": "原始查询",
            "collect": False,
            "gdelt": True,
            "years": 3,
            "min_relevance": 0.4,
        },
    )

    payload = search_service.search_request_from_job(job)

    assert payload.query == "原始查询"
    assert payload.collect is False
    assert payload.gdelt is True
    assert payload.years == 3
    assert payload.min_relevance == 0.4


def test_rerun_search_job_rejects_completed_jobs():
    job_id = "test-rerun-done"
    init_db()
    with Session(engine) as session:
        old = session.get(SearchJob, job_id)
        if old:
            session.delete(old)
            session.commit()
        session.add(SearchJob(
            id=job_id,
            query="完成任务",
            status="done",
            steps=[],
            payload={"query": "完成任务", "collect": False},
        ))
        session.commit()
    try:
        try:
            api.rerun_search_job(job_id)
        except HTTPException as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("completed jobs should not be rerun")
    finally:
        with Session(engine) as session:
            job = session.get(SearchJob, job_id)
            if job:
                session.delete(job)
                session.commit()
