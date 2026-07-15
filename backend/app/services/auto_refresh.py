"""后端运行期自动刷新 (方案B)。

仅在后端进程开着时, 定时自动重采「过期活跃话题的新闻」+「前沿日报」。
本地工具: 关机不更新。红线:
  - 绝不自动跑 LLM / 学界 / 民间情绪(OpenCLI) / 三方对照。
  - collect 只采集(不 enrich), analyze 只本地(persist), discovery annotate=False。
  - 单话题失败只记录, 不崩后端。

调度用 stop_event 循环(可干净停止), 独立 daemon 线程, 不伪装成 SearchJob
(不污染用户任务列表)。每 tick 新建短生命 Session, 不跨 tick 持有。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app import config
from app.db import Article, SearchJob, Topic, TopicArticle, engine
from app.services.topic_locks import claim_topic

_lock = threading.Lock()          # 只防调度器自身重入
_stop_event = threading.Event()
_thread: threading.Thread | None = None
LOGGER = logging.getLogger(__name__)
_state: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "last_started_at": None,
    "last_finished_at": None,
    "last_error": "",
    "news_refreshed": 0,
    "news_errors": [],
    "frontier_refreshed": False,
    "skipped_active": 0,
}


def status_snapshot() -> dict[str, Any]:
    """供 API/前端读取:开关、上次运行、统计。"""
    return dict(_state)


def start_auto_refresh_scheduler() -> None:
    """幂等启动调度线程。AUTO_REFRESH_ENABLED=0 时不启动。"""
    global _thread
    _state["enabled"] = config.AUTO_REFRESH_ENABLED
    if not config.AUTO_REFRESH_ENABLED:
        return
    if _thread is not None and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name="auto-refresh", daemon=True)
    _thread.start()


def stop_auto_refresh_scheduler(timeout: float = 2.0) -> None:
    """停止调度线程并短等待 join(便于测试/dev reload)。"""
    _stop_event.set()
    if _thread is not None and _thread.is_alive():
        _thread.join(timeout=timeout)


def _loop() -> None:
    # 首跑前先等一个 grace, 避开 FastAPI 启动/迁移/前端首拉/测试。
    if _stop_event.wait(config.AUTO_REFRESH_INITIAL_DELAY_SECONDS):
        return
    # 用最短间隔作为轮询节拍; 各任务内部再按自己的间隔判 stale。
    tick_hours = min(config.AUTO_REFRESH_NEWS_INTERVAL_HOURS,
                     config.AUTO_REFRESH_FRONTIER_INTERVAL_HOURS)
    tick_seconds = max(60.0, tick_hours * 3600.0)
    while True:
        refresh_once()
        if _stop_event.wait(tick_seconds):
            return


def refresh_once(now: datetime | None = None, *, observation_root: Path | None = None) -> dict[str, Any]:
    """跑一轮自动刷新。测试可直接调用, 不依赖真实 sleep。

    返回本轮统计。任何单项异常都被隔离, 不抛出。
    """
    now = now or datetime.utcnow()
    if not _lock.acquire(blocking=False):
        return dict(_state)  # 上一轮还没跑完, 跳过防重入
    try:
        _state["running"] = True
        _state["last_started_at"] = now.isoformat()
        _state["last_error"] = ""
        news = 0
        skipped = 0
        news_errors: list[str] = []
        try:
            news, skipped, news_errors = _refresh_due_news(now, observation_root=observation_root)
        except Exception as exc:  # pragma: no cover - defensive
            _state["last_error"] = f"news: {type(exc).__name__}: {exc}"
        frontier = False
        try:
            frontier = _refresh_due_frontier(now)
        except Exception as exc:  # pragma: no cover - defensive
            _state["last_error"] = (_state["last_error"] + f" | frontier: {type(exc).__name__}: {exc}").strip(" |")
        _state["news_refreshed"] = news
        _state["skipped_active"] = skipped
        _state["news_errors"] = news_errors  # 单话题失败原因, 供用户看"哪个源/话题没刷成"
        _state["frontier_refreshed"] = frontier
        _state["last_finished_at"] = datetime.utcnow().isoformat()
    finally:
        _state["running"] = False   # 先落 running=False, 再返回快照, 避免同步返回显示"仍在跑"
        _lock.release()
    return dict(_state)


def _active_job_topic_ids(session: Session) -> set[int]:
    """所有 queued/running 任务关联的 topic_id 集合(这些话题本轮跳过, 防和手动操作串写)。

    一次查出整个集合, 避免对每个话题重复全表扫描。
    """
    jobs = session.exec(
        select(SearchJob).where(SearchJob.status.in_(("queued", "running")))  # type: ignore[attr-defined]
    ).all()
    return {int((job.payload or {}).get("topic_id") or 0) for job in jobs}


def _topic_latest_published(session: Session, topic_id: int) -> datetime | None:
    rows = session.exec(
        select(Article.published_at)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic_id)
    ).all()
    dates = [d for d in rows if d]
    return max(dates) if dates else None


def _refresh_due_news(
    now: datetime, *, observation_root: Path | None = None
) -> tuple[int, int, list[str]]:
    """重采过期活跃话题的新闻。返回 (刷新数, 因活跃任务跳过数, 单话题失败原因列表)。

    只刷: status=active + 已有文章 + latest_published_at 超过新闻间隔。
    空话题不碰(交用户首次手动/搜索创建, 不无限扫网)。每轮限 MAX。

    RM-055: Post-commit coverage observation. After session.commit() for each topic,
    capture coverage snapshot via short read-only Session to gitignored local evidence.
    """
    # 延迟导入, 避免顶层循环依赖。
    from app import topic_ops
    from app.services import coverage_observation

    interval = timedelta(hours=config.AUTO_REFRESH_NEWS_INTERVAL_HOURS)
    refreshed = 0
    skipped = 0
    errors: list[str] = []
    try:
        observation_run = coverage_observation.begin_observation_run(
            root=observation_root,
            observed_at=now,
        )
    except Exception as exc:  # collision or unexpected setup error must not block a committed refresh
        observation_run = None
        LOGGER.error("RM-055 observation run setup failed: %s: %s", type(exc).__name__, exc)
    with Session(engine) as session:
        topics = session.exec(select(Topic).where(Topic.status == "active")).all()
        # 先算 stale 候选(有文章且过期), 按最旧优先。
        candidates: list[tuple[datetime, int, str]] = []
        for topic in topics:
            latest = _topic_latest_published(session, topic.id)
            if latest is None:
                continue  # 空话题不自动刷
            if now - latest < interval:
                continue  # 还新鲜
            candidates.append((latest, topic.id, topic.name))
        candidates.sort(key=lambda t: t[0])  # 最旧的先刷
    for candidate_index, (_latest, topic_id, topic_name) in enumerate(candidates):
        if refreshed >= config.AUTO_REFRESH_MAX_TOPICS_PER_CYCLE:
            if observation_run is not None:
                for _later_latest, later_id, _later_name in candidates[candidate_index:]:
                    _record_observation_safely(observation_run.record_skipped, topic_id=later_id, reason="cycle topic limit")
            break
        with claim_topic(topic_id, blocking=False) as acquired:
            if not acquired:
                skipped += 1
                if observation_run is not None:
                    _record_observation_safely(observation_run.record_skipped, topic_id=topic_id, reason="topic lock held")
                continue
            # Commit success retains the exact collection result for a new read Session.
            committed_result: dict[str, Any] | None = None
            with Session(engine) as session:
                topic = session.get(Topic, topic_id)
                if not topic or topic.status != "active":
                    if observation_run is not None:
                        _record_observation_safely(observation_run.record_skipped, topic_id=topic_id, reason="topic is no longer active")
                    continue
                if topic_id in _active_job_topic_ids(session):
                    skipped += 1
                    if observation_run is not None:
                        _record_observation_safely(observation_run.record_skipped, topic_id=topic_id, reason="active job guard")
                    continue
                try:
                    collection_result = topic_ops.collect_topic(
                        session,
                        topic,
                        gnews=True,
                        gdelt_on=False,
                        use_curated_feeds=True,
                        min_rel=0.2,
                        commit=False,
                    )
                    topic_ops.analyze_topic(session, topic, persist=True, commit=False)
                    session.commit()
                    refreshed += 1
                    committed_result = collection_result
                except Exception as exc:  # 单话题失败隔离, 继续下一个, 但记录原因(失败可见)
                    session.rollback()
                    errors.append(f"{topic_name}: {type(exc).__name__}: {str(exc)[:80]}")
                    if observation_run is not None:
                        _record_observation_safely(
                            observation_run.record_failed,
                            topic_id=topic_id,
                            error=f"{type(exc).__name__}: {str(exc)[:80]}",
                        )

            # The write Session is now closed. Capture failure is visible in the
            # run manifest/log only; it never changes refresh success accounting.
            if committed_result is not None and observation_run is not None:
                _record_observation_safely(
                    observation_run.record_committed,
                    topic_id=topic_id,
                    collection_result=committed_result,
                )
    if observation_run is not None:
        _record_observation_safely(observation_run.finalize)
    return refreshed, skipped, errors


def _record_observation_safely(callback: Any, **kwargs: Any) -> None:
    try:
        callback(**kwargs)
    except Exception as exc:
        LOGGER.error("RM-055 observation bookkeeping failed: %s: %s", type(exc).__name__, exc)


def _refresh_due_frontier(now: datetime) -> bool:
    """前沿日报: 最新报告超过间隔或不存在时, 跑一次基线(annotate=False, 不烧 LLM)。"""
    from app.discovery import run as discovery_run

    interval = timedelta(hours=config.AUTO_REFRESH_FRONTIER_INTERVAL_HOURS)
    latest = discovery_run.latest_report()
    if latest:
        run_id = latest.get("run_id") or ""
        # run_id 形如 20260704T120000Z; 解析出时间判 stale。
        stamp = _parse_run_id(run_id)
        if stamp is not None and now - stamp < interval:
            return False  # 还新鲜
    discovery_run.run_and_save(annotate=False)
    return True


def _parse_run_id(run_id: str) -> datetime | None:
    compact = run_id.replace("-", "").replace(":", "")
    try:
        return datetime.strptime(compact[:15], "%Y%m%dT%H%M%S")
    except (ValueError, IndexError):
        return None
