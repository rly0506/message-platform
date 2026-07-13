import asyncio
from contextlib import contextmanager
from uuid import uuid4

from app import api, db
from app.db import SearchJob, Topic, engine, init_db
from app.schemas.search import SearchRequest
from app.services import payloads, search_service
from fastapi import HTTPException
from sqlmodel import Session, create_engine


def test_api_lifespan_runs_startup_and_shutdown_hooks(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(api, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(
        api.search_service,
        "mark_interrupted_search_jobs",
        lambda: calls.append("mark_interrupted"),
    )
    monkeypatch.setattr(
        api.auto_refresh,
        "start_auto_refresh_scheduler",
        lambda: calls.append("start_scheduler"),
    )
    monkeypatch.setattr(
        api.auto_refresh,
        "stop_auto_refresh_scheduler",
        lambda: calls.append("stop_scheduler"),
    )

    async def exercise_lifespan() -> None:
        async with api.lifespan(api.app):
            assert calls == ["init_db", "mark_interrupted", "start_scheduler"]

    asyncio.run(exercise_lifespan())

    assert calls == ["init_db", "mark_interrupted", "start_scheduler", "stop_scheduler"]


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


def test_article_payload_includes_info_value_labels():
    topic_article = api.TopicArticle(
        topic_id=1,
        article_id=1,
        relevance=0.8,
        relevant=True,
        substance_score=22,
        emotion_score=88,
    )
    article = api.Article(
        id=1,
        url="https://example.com/a",
        title="Markets panic over alleged breakthrough",
        source="Example",
        snippet="Lots of rhetoric with little verifiable detail.",
    )

    payload = payloads.article_payload(topic_article, article)

    assert payload["info_value_labels"] == [
        {
            "code": "suspected_hype",
            "label": "疑似造势",
            "note": "情绪强度高且干货密度低，提示先核查事实支撑，不把语气当证据。",
            "severity": "hint",
        },
        {
            "code": "availability_high",
            "label": "可得性偏高",
            "note": "这条材料很醒目，但当前可核查细节偏少，避免因容易想起而高估重要性。",
            "severity": "hint",
        },
    ]


def test_article_payload_includes_url_decode_trace():
    topic_article = api.TopicArticle(topic_id=1, article_id=1, relevance=0.8, relevant=True)
    article = api.Article(
        id=1,
        url="https://www.reuters.com/world/story",
        original_url="https://news.google.com/rss/articles/CBMiSample?oc=5",
        url_decoded=True,
        title="Reuters story",
        source="Reuters",
        snippet="A story resolved from Google News.",
    )

    payload = payloads.article_payload(topic_article, article)

    assert payload["url"] == "https://www.reuters.com/world/story"
    assert payload["original_url"] == "https://news.google.com/rss/articles/CBMiSample?oc=5"
    assert payload["url_decoded"] is True


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


def test_rerun_search_job_rejects_non_search_job_kinds(monkeypatch):
    job_id = 'test-rerun-deep-analysis'
    init_db()
    with Session(engine) as session:
        session.add(SearchJob(
            id=job_id,
            query='deep-analysis:Ukraine',
            status='failed',
            steps=[],
            payload={'topic_id': 1, 'enrich_limit': 30, 'kind': 'deep_analysis'},
        ))
        session.commit()

    monkeypatch.setattr(
        search_service,
        'enqueue_search_job',
        lambda payload: {'unexpected_query': payload.query},
    )
    try:
        try:
            search_service.rerun_search_job(job_id)
        except HTTPException as exc:
            assert exc.status_code == 409
            assert 'search' in str(exc.detail).lower()
        else:
            raise AssertionError('non-search jobs must not be converted into search reruns')
    finally:
        with Session(engine) as session:
            job = session.get(SearchJob, job_id)
            if job:
                session.delete(job)
                session.commit()


def test_run_search_claims_blocking_topic_write_guard(monkeypatch):
    claims: list[tuple[int, bool]] = []

    @contextmanager
    def fake_claim(topic_id: int, *, blocking: bool):
        claims.append((topic_id, blocking))
        yield True

    monkeypatch.setattr(search_service, 'claim_topic', fake_claim, raising=False)
    monkeypatch.setattr(
        search_service.topic_ops,
        'analyze_topic',
        lambda session, topic, persist=True: {
            'events': [],
            'framing': [],
            'analysis_md': '',
            'stance_evolution': [],
            'keywords': [],
            'entities': [],
            'entity_groups': {},
            'criteria': {},
        },
    )

    result = search_service.run_search(SearchRequest(query=f'guard-{uuid4().hex}', collect=False))

    assert result['events'] == []
    assert len(claims) == 1
    assert claims[0][1] is True


def test_run_topic_job_claims_blocking_topic_write_guard(monkeypatch):
    init_db()
    job_id = f'guard-job-{uuid4().hex}'
    with Session(engine) as session:
        topic = Topic(name=f'guard-topic-{uuid4().hex}', queries=['guard'])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        topic_id = topic.id
        session.add(SearchJob(id=job_id, query='guard', status='queued', steps=[], payload={'topic_id': topic_id}))
        session.commit()

    claims: list[tuple[int, bool]] = []

    @contextmanager
    def fake_claim(claimed_topic_id: int, *, blocking: bool):
        claims.append((claimed_topic_id, blocking))
        yield True

    monkeypatch.setattr(search_service, 'claim_topic', fake_claim, raising=False)
    search_service.run_topic_job(
        job_id,
        topic_id,
        [],
        lambda session, topic, runner: {'topic_id': topic.id},
    )

    assert claims == [(topic_id, True)]


def test_migrate_adds_analysis_sample_metadata_columns(tmp_path, monkeypatch):
    legacy_path = tmp_path / 'legacy.db'
    legacy_engine = create_engine(f'sqlite:///{legacy_path}')
    tables = (
        'topicarticle', 'article', 'sentimentpost', 'cognitionmark',
        'cognitionprofile', 'digqueueitem', 'paper', 'topic', 'sourceregistry',
    )
    with legacy_engine.connect() as conn:
        for table in tables:
            conn.exec_driver_sql(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY)')
        conn.exec_driver_sql(
            'CREATE TABLE analysis ('
            'id INTEGER PRIMARY KEY, topic_id INTEGER, '
            'generated_at DATETIME, content_md VARCHAR)'
        )
        conn.commit()

    monkeypatch.setattr(db, 'engine', legacy_engine)
    db._migrate()

    with legacy_engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql('PRAGMA table_info(analysis)')}
        dig_queue_columns = {
            row[1] for row in conn.exec_driver_sql('PRAGMA table_info(digqueueitem)')
        }

    assert {'sample_article_count', 'sample_latest_published_at'} <= columns
    assert {'revision', 'deleted'} <= dig_queue_columns
