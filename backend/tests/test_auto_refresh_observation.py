"""RM-055 integration: only committed auto-refresh topics become evidence."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.db import Article, Topic, TopicArticle, engine, init_db
from app.discovery import run as discovery_run
from app.services import auto_refresh


@pytest.fixture(autouse=True)
def _clean_topics():
    init_db()
    with Session(engine) as session:
        for model in (TopicArticle, Article, Topic):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()


def _seed_stale_topic(now: datetime, name: str = "stale") -> int:
    with Session(engine) as session:
        topic = Topic(name=name, description="", queries=[name], status="active")
        session.add(topic)
        session.commit()
        session.refresh(topic)
        article = Article(
            url=f"https://example.test/{name}", title=name, source="Wire", source_lang="en",
            published_at=now - timedelta(hours=25), snippet="old",
        )
        session.add(article)
        session.commit()
        session.refresh(article)
        session.add(TopicArticle(topic_id=topic.id, article_id=article.id, relevance=0.8))
        session.commit()
        return topic.id


class _Recorder:
    def __init__(self):
        self.committed: list[tuple[int, dict]] = []
        self.failed: list[int] = []
        self.skipped: list[int] = []
        self.finalized = False

    def record_committed(self, *, topic_id, collection_result):
        self.committed.append((topic_id, collection_result))

    def record_failed(self, *, topic_id, error):
        self.failed.append(topic_id)

    def record_skipped(self, *, topic_id, reason):
        self.skipped.append(topic_id)

    def finalize(self):
        self.finalized = True
        return {"status": "finalized"}


def test_refresh_records_exact_collect_result_only_after_the_write_session_closes(monkeypatch):
    now = datetime(2026, 7, 15, 12, 0, 0)
    topic_id = _seed_stale_topic(now)
    recorder = _Recorder()
    events: list[str] = []
    real_session = auto_refresh.Session

    class TrackingSession(real_session):
        def __exit__(self, *args):
            events.append("closed")
            return super().__exit__(*args)

    collection_result = {"requests": [{"source": "wire", "status": "ok"}], "errors": ["one collector degraded"]}
    monkeypatch.setattr(auto_refresh, "Session", TrackingSession)
    monkeypatch.setattr("app.topic_ops.collect_topic", lambda _s, _t, **_kw: collection_result)
    monkeypatch.setattr("app.topic_ops.analyze_topic", lambda _s, _t, **_kw: {})
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260715T115900Z"})

    def begin(**_kwargs):
        original = recorder.record_committed

        def committed(**kwargs):
            assert events[-1] == "closed"
            original(**kwargs)

        recorder.record_committed = committed
        return recorder

    monkeypatch.setattr("app.services.coverage_observation.begin_observation_run", begin)

    result = auto_refresh.refresh_once(now=now)

    assert result["news_refreshed"] == 1
    assert result["news_errors"] == []
    assert recorder.committed == [(topic_id, collection_result)]
    assert recorder.finalized is True


def test_commit_failure_creates_no_expected_observation(monkeypatch):
    now = datetime(2026, 7, 15, 12, 0, 0)
    topic_id = _seed_stale_topic(now)
    recorder = _Recorder()
    monkeypatch.setattr("app.topic_ops.collect_topic", lambda _s, _t, **_kw: {"requests": [], "errors": []})
    monkeypatch.setattr("app.topic_ops.analyze_topic", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("analysis failed")))
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260715T115900Z"})
    monkeypatch.setattr("app.services.coverage_observation.begin_observation_run", lambda **_kwargs: recorder)

    result = auto_refresh.refresh_once(now=now)

    assert result["news_refreshed"] == 0
    assert any("analysis failed" in error for error in result["news_errors"])
    assert recorder.committed == []
    assert recorder.failed == [topic_id]
    assert recorder.finalized is True


def test_observation_infrastructure_failure_never_decrements_refresh_or_enters_news_errors(monkeypatch):
    now = datetime(2026, 7, 15, 12, 0, 0)
    _seed_stale_topic(now)
    recorder = _Recorder()
    monkeypatch.setattr("app.topic_ops.collect_topic", lambda _s, _t, **_kw: {"requests": [], "errors": []})
    monkeypatch.setattr("app.topic_ops.analyze_topic", lambda _s, _t, **_kw: {})
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260715T115900Z"})
    monkeypatch.setattr("app.services.coverage_observation.begin_observation_run", lambda **_kwargs: recorder)

    def broken_record(**_kwargs):
        raise OSError("evidence disk unavailable")

    recorder.record_committed = broken_record
    recorder.finalize = lambda: {"status": "unfinalized", "error": "evidence disk unavailable"}

    result = auto_refresh.refresh_once(now=now)

    assert result["news_refreshed"] == 1
    assert result["news_errors"] == []
