"""方案B 自动刷新测试。

覆盖 GPT 列的 7 点:
1. refresh_once 只刷 stale active topic, 不刷 fresh/archived/空 topic。
2. 新闻刷新调 collect_topic(use_curated_feeds=True) 后调 analyze_topic(persist=True)。
3. 单 topic 异常不阻断下一个, 状态记录不崩。
4. discovery 只在超间隔时跑, 且 annotate=False。
5. 存在 active job 时跳过该 topic。
6. 绝不调 LLM/OpenCLI/学界/民间/三方(monkeypatch 为 raise 证明未被调)。
7. start 幂等 / stop 可停, 不留跑着的线程。
"""
from datetime import datetime, timedelta

from sqlmodel import Session, select

import pytest

from app import config, topic_ops
from app.db import Article, SearchJob, Topic, TopicArticle, engine, init_db
from app.discovery import run as discovery_run
from app.services import auto_refresh


@pytest.fixture(autouse=True)
def _clean_db():
    """每个测试前清空相关表 —— 自动刷新按"全库 stale 话题"查, 累积会污染断言。"""
    init_db()
    with Session(engine) as session:
        for model in (SearchJob, TopicArticle, Article, Topic):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()
    yield


def _seed_topic(name: str, latest: datetime | None, status: str = "active", n: int = 2) -> int:
    """建一个话题 + n 篇文章, 最新文章 published_at = latest。latest=None 则建空话题。"""
    init_db()
    with Session(engine) as session:
        topic = Topic(name=name, description="", queries=[name], status=status)
        session.add(topic)
        session.commit()
        session.refresh(topic)
        if latest is not None:
            for i in range(n):
                art = Article(
                    url=f"https://example.com/{name}/{datetime.utcnow().timestamp()}-{i}",
                    title=f"t{i}", source="s", source_lang="en",
                    published_at=latest - timedelta(days=i), snippet="x",
                )
                session.add(art)
                session.commit()
                session.refresh(art)
                session.add(TopicArticle(topic_id=topic.id, article_id=art.id, relevance=0.7))
            session.commit()
        return topic.id


def _patch_collectors(monkeypatch, calls: dict):
    """把 collect/analyze 换成记录调用的假函数; discovery 也假化。"""
    def fake_collect(session, topic, **kw):
        calls.setdefault("collect", []).append((topic.id, kw))
        return {}
    def fake_analyze(session, topic, persist=True):
        calls.setdefault("analyze", []).append((topic.id, persist))
        return {}
    monkeypatch.setattr(topic_ops, "collect_topic", fake_collect)
    monkeypatch.setattr(topic_ops, "analyze_topic", fake_analyze)


def _forbid_llm_opencli(monkeypatch):
    """把 LLM/学界/民间/三方 全 patch 成 raise, 证明自动刷新不碰它们。"""
    def boom(*a, **k):
        raise AssertionError("auto-refresh must NOT call LLM/OpenCLI/academic/sentiment/cross")
    monkeypatch.setattr(topic_ops, "run_deep_analysis", boom, raising=False)
    from app.pipeline import academic, sentiment, cross_synthesis
    monkeypatch.setattr(academic, "run_academic_analysis", boom, raising=False)
    monkeypatch.setattr(sentiment, "run_sentiment_analysis", boom, raising=False)
    monkeypatch.setattr(cross_synthesis, "run_cross_synthesis", boom, raising=False)


def test_refresh_only_stale_active_topics(monkeypatch):
    now = datetime(2026, 7, 4, 12, 0, 0)
    stale = _seed_topic("stale", now - timedelta(hours=10))       # 超6h → 刷
    fresh = _seed_topic("fresh", now - timedelta(hours=1))        # 新鲜 → 不刷
    empty = _seed_topic("empty", None)                            # 空 → 不刷
    archived = _seed_topic("archived", now - timedelta(hours=99), status="archived")  # 归档 → 不刷
    calls: dict = {}
    _patch_collectors(monkeypatch, calls)
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260704T115900Z"})
    monkeypatch.setattr(discovery_run, "run_and_save", lambda annotate=False: {})

    auto_refresh.refresh_once(now=now)

    collected_ids = {c[0] for c in calls.get("collect", [])}
    assert stale in collected_ids
    assert fresh not in collected_ids
    assert empty not in collected_ids
    assert archived not in collected_ids


def test_collect_then_analyze_with_curated_feeds(monkeypatch):
    now = datetime(2026, 7, 4, 12, 0, 0)
    tid = _seed_topic("t", now - timedelta(hours=10))
    calls: dict = {}
    _patch_collectors(monkeypatch, calls)
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260704T115900Z"})

    auto_refresh.refresh_once(now=now)

    assert any(cid == tid and kw.get("use_curated_feeds") is True for cid, kw in calls.get("collect", []))
    assert any(cid == tid and persist is True for cid, persist in calls.get("analyze", []))


def test_topic_error_isolated(monkeypatch):
    now = datetime(2026, 7, 4, 12, 0, 0)
    t1 = _seed_topic("boom", now - timedelta(hours=10))
    t2 = _seed_topic("ok", now - timedelta(hours=11))
    seen: list = []
    def collect(session, topic, **kw):
        seen.append(topic.id)
        if topic.id == t1:
            raise RuntimeError("collect failed")
        return {}
    monkeypatch.setattr(topic_ops, "collect_topic", collect)
    monkeypatch.setattr(topic_ops, "analyze_topic", lambda s, t, persist=True: {})
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260704T115900Z"})

    result = auto_refresh.refresh_once(now=now)  # 不应抛
    assert t1 in seen and t2 in seen   # 失败的 t1 不阻断 t2
    # 失败原因要记进状态(失败可见), 且 running 已复位为 False
    assert any("collect failed" in e for e in result["news_errors"])
    assert result["running"] is False


def test_frontier_only_when_stale(monkeypatch):
    now = datetime(2026, 7, 4, 12, 0, 0)
    _seed_topic("t", now - timedelta(hours=1))  # fresh, 新闻不刷
    monkeypatch.setattr(topic_ops, "collect_topic", lambda s, t, **k: {})
    monkeypatch.setattr(topic_ops, "analyze_topic", lambda s, t, persist=True: {})
    ran = {"count": 0, "annotate": None}
    def fake_save(annotate=False):
        ran["count"] += 1
        ran["annotate"] = annotate
        return {}
    monkeypatch.setattr(discovery_run, "run_and_save", fake_save)

    # 最新报告 1h 前(未超12h)→ 不跑
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260704T110000Z"})
    auto_refresh.refresh_once(now=now)
    assert ran["count"] == 0

    # 最新报告 20h 前(超12h)→ 跑, 且 annotate=False
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260703T160000Z"})
    auto_refresh.refresh_once(now=now)
    assert ran["count"] == 1
    assert ran["annotate"] is False


def test_skip_topic_with_active_job(monkeypatch):
    now = datetime(2026, 7, 4, 12, 0, 0)
    tid = _seed_topic("busy", now - timedelta(hours=10))
    with Session(engine) as session:
        session.add(SearchJob(id="j1", query="x", status="running",
                              payload={"topic_id": tid, "kind": "deep_analysis"}))
        session.commit()
    calls: dict = {}
    _patch_collectors(monkeypatch, calls)
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260704T115900Z"})

    result = auto_refresh.refresh_once(now=now)
    assert tid not in {c[0] for c in calls.get("collect", [])}
    assert result["skipped_active"] >= 1


def test_never_calls_llm_or_opencli(monkeypatch):
    now = datetime(2026, 7, 4, 12, 0, 0)
    _seed_topic("t", now - timedelta(hours=10))
    calls: dict = {}
    _patch_collectors(monkeypatch, calls)
    monkeypatch.setattr(discovery_run, "latest_report", lambda: {"run_id": "20260703T160000Z"})
    monkeypatch.setattr(discovery_run, "run_and_save", lambda annotate=False: {})
    _forbid_llm_opencli(monkeypatch)

    auto_refresh.refresh_once(now=now)  # 若碰到 LLM/OpenCLI 会 AssertionError


def test_scheduler_start_idempotent_and_stop(monkeypatch):
    monkeypatch.setattr(config, "AUTO_REFRESH_ENABLED", True)
    monkeypatch.setattr(config, "AUTO_REFRESH_INITIAL_DELAY_SECONDS", 999)  # 首跑延迟很长, 测试期不真跑
    auto_refresh.stop_auto_refresh_scheduler()
    auto_refresh.start_auto_refresh_scheduler()
    t1 = auto_refresh._thread
    auto_refresh.start_auto_refresh_scheduler()  # 幂等: 不应起第二个
    assert auto_refresh._thread is t1
    auto_refresh.stop_auto_refresh_scheduler()
    assert auto_refresh._thread is None or not auto_refresh._thread.is_alive()


def test_disabled_does_not_start(monkeypatch):
    monkeypatch.setattr(config, "AUTO_REFRESH_ENABLED", False)
    auto_refresh.stop_auto_refresh_scheduler()
    auto_refresh._thread = None
    auto_refresh.start_auto_refresh_scheduler()
    assert auto_refresh._thread is None or not auto_refresh._thread.is_alive()
