"""Search request orchestration and background job lifecycle management."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Thread
from typing import Any, Callable
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app import topic_ops
from app.db import SearchJob, Topic, engine, init_db
from app.pipeline import academic, cross_synthesis, sentiment
from app.schemas.search import SearchRequest
from app.services import payloads
from app.services.topic_locks import claim_topic


MAX_SEARCH_JOBS = 50

# 展开撒网: 主题拆出的子角度最多并进多少条进采集 queries。
# 限量是因为每条子角度 = 一次额外 gnews 采集请求, 太多会放大采集超时面。
EXPAND_SUBTOPIC_LIMIT = 3


class JobRunner:
    def __init__(self, job_id: str, steps: list[dict[str, str]]) -> None:
        self.job_id = job_id
        self.steps = steps

    def run(
        self,
        work: Callable[["JobRunner"], dict[str, Any]],
        status_for_result: Callable[[dict[str, Any]], str] | str = "done",
    ) -> None:
        update_job(self.job_id, status="running")
        try:
            result = work(self)
            status = status_for_result(result) if callable(status_for_result) else status_for_result
            update_job(self.job_id, status=status, result=result, error="")
        except Exception as exc:  # pragma: no cover - defensive task boundary
            fail_job(self.job_id, exc)

    def on_step(self, key: str, status: str, details: dict[str, Any] | None = None) -> None:
        self.set_step(key, status)
        if details is not None:
            update_job(self.job_id, result={"progress": {"step": key, **details}})

    def set_step(self, key: str, status: str) -> None:
        set_step(self.steps, key, status, self.job_id)

    def mark_all_steps_done(self) -> None:
        for step in self.steps:
            step["status"] = "done"
        sync_job_steps(self.steps, self.job_id)

    def mark_running_steps_done(self) -> None:
        for step in self.steps:
            if step["status"] == "running":
                step["status"] = "done"
        sync_job_steps(self.steps, self.job_id)


def enqueue_job(
    *,
    query: str,
    steps: list[dict[str, str]],
    payload: dict[str, Any],
    target: Callable[..., None],
    args: tuple[Any, ...],
) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        job = SearchJob(
            id=job_id,
            query=query,
            status="queued",
            steps=steps,
            payload=payload,
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=target, args=(job_id, *args), daemon=True).start()
    return job_snapshot(job_id)


def enqueue_topic_job(
    topic_id: int,
    *,
    query_prefix: str,
    steps: list[dict[str, str]],
    payload: dict[str, Any],
    target: Callable[..., None],
    args: tuple[Any, ...],
) -> dict[str, Any]:
    topic_name = topic_name_or_404(topic_id)
    return enqueue_job(
        query=f"{query_prefix}:{topic_name}",
        steps=steps,
        payload=payload,
        target=target,
        args=args,
    )


def topic_name_or_404(topic_id: int) -> str:
    init_db()
    with Session(engine) as session:
        return topic_or_404(session, topic_id).name


def topic_or_404(session: Session, topic_id: int) -> Topic:
    topic = session.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


def run_topic_job(
    job_id: str,
    topic_id: int,
    steps: list[dict[str, str]],
    work: Callable[[Session, Topic, JobRunner], dict[str, Any]],
    status_for_result: Callable[[dict[str, Any]], str] | str = "done",
) -> None:
    runner = JobRunner(job_id, steps)

    def run_with_topic(runner: JobRunner) -> dict[str, Any]:
        init_db()
        with claim_topic(topic_id, blocking=True):
            with Session(engine) as session:
                topic = topic_or_404(session, topic_id)
                return work(session, topic, runner)

    runner.run(run_with_topic, status_for_result)


def enqueue_search_job(payload: SearchRequest) -> dict[str, Any]:
    return enqueue_job(
        query=payload.query.strip(),
        steps=search_steps(payload.collect),
        payload=request_payload(payload),
        target=run_search_job,
        args=(payload,),
    )


def rerun_search_job(job_id: str) -> dict[str, Any]:
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Search job not found")
        if job.status not in {"interrupted", "failed"}:
            raise HTTPException(status_code=409, detail="Only interrupted or failed jobs can be rerun")
        if (job.payload or {}).get("kind") not in {None, "search"}:
            raise HTTPException(status_code=409, detail="Only search jobs can be rerun")
        payload = search_request_from_job(job)
    return enqueue_search_job(payload)


def enqueue_deep_analysis_job(topic_id: int, enrich_limit: int = 30) -> dict[str, Any]:
    return enqueue_topic_job(
        topic_id,
        query_prefix="deep-analysis",
        steps=deep_analysis_steps(),
        payload={"topic_id": topic_id, "enrich_limit": enrich_limit, "kind": "deep_analysis"},
        target=run_deep_analysis_job,
        args=(topic_id, enrich_limit),
    )


def enqueue_academic_analysis_job(topic_id: int, top_n: int = 30) -> dict[str, Any]:
    return enqueue_topic_job(
        topic_id,
        query_prefix="academic",
        steps=academic_analysis_steps(),
        payload={"topic_id": topic_id, "top_n": top_n, "kind": "academic_analysis"},
        target=run_academic_analysis_job,
        args=(topic_id, top_n),
    )


def enqueue_sentiment_analysis_job(topic_id: int, limit: int = 25) -> dict[str, Any]:
    return enqueue_topic_job(
        topic_id,
        query_prefix="sentiment",
        steps=sentiment_analysis_steps(),
        payload={"topic_id": topic_id, "limit": limit, "kind": "sentiment_analysis"},
        target=run_sentiment_analysis_job,
        args=(topic_id, limit),
    )


def enqueue_cross_synthesis_job(topic_id: int, refresh_voices: bool = False) -> dict[str, Any]:
    return enqueue_topic_job(
        topic_id,
        query_prefix="cross-synthesis",
        steps=cross_synthesis_steps(refresh_voices),
        payload={"topic_id": topic_id, "kind": "cross_synthesis", "refresh_voices": refresh_voices},
        target=run_cross_synthesis_job,
        args=(topic_id, refresh_voices),
    )


def run_search(payload: SearchRequest, job_id: str | None = None) -> dict[str, Any]:
    init_db()
    with Session(engine) as session:
        query = payload.query.strip()
        steps = search_steps(payload.collect)
        set_step(steps, "topic", "running", job_id)

        # 可选: LLM 把宏观/单薄主题拆成可深挖的相关线索。
        # subtopics 前 N 条本次撒网 (采得更厚, 但不持久化进 topic); analogues 仅回传供前端点击, 不撒网。
        subtopics: list[str] = []
        analogues: list[str] = []
        extra_queries: list[str] = []
        if payload.decompose:
            from app.discovery.decompose import decompose_topic
            decomposed = decompose_topic(query)
            subtopics = decomposed.subtopics
            analogues = decomposed.analogues
            extra_queries = subtopics[:EXPAND_SUBTOPIC_LIMIT]

        topic = topic_ops.get_or_create_topic(
            session,
            query,
            topic_ops.query_variants(query),
        )
        with claim_topic(topic.id, blocking=True):
            set_step(steps, "topic", "done", job_id)
            collect_stats = {"raw": 0, "kept": 0, "new_articles": 0, "new_links": 0}
            if payload.collect:
                set_step(steps, "collect", "running", job_id)
                collect_stats = topic_ops.collect_topic(
                    session,
                    topic,
                    gnews=True,
                    gdelt_on=payload.gdelt,
                    years=payload.years,
                    min_rel=payload.min_relevance,
                    extra_queries=extra_queries,
                )
                steps[1]["status"] = "warning" if collect_stats.get("errors") else "done"
                if collect_stats["raw"] == 0 and not collect_stats.get("errors"):
                    steps[1]["status"] = "empty"
                    collect_stats["errors"] = ["采集源返回 0 条结果，请尝试更具体或中英文混合的关键词。"]
                sync_job_steps(steps, job_id)
            else:
                set_step(steps, "collect", "skipped", job_id)
            set_step(steps, "analyze", "running", job_id)
            data = topic_ops.analyze_topic(session, topic, persist=True)
            evidence_lookup = payloads.topic_evidence_lookup(session, topic.id)
            data["events"] = payloads.attach_event_evidence(data["events"], evidence_lookup)
            steps[2]["status"] = "done" if data.get("events") else "empty"
            sync_job_steps(steps, job_id)
            return {
                "topic": payloads.topic_summary(session, topic),
                "collect": collect_stats,
                "steps": steps,
                "events": data["events"],
                "framing": data["framing"],
                "analysis_md": data["analysis_md"],
                "stance_evolution": data["stance_evolution"],
                "keywords": data["keywords"],
                "entities": data["entities"],
                "entity_groups": data["entity_groups"],
                "criteria": data["criteria"],
                "subtopics": subtopics,
                "analogues": analogues,
            }


def run_search_job(job_id: str, payload: SearchRequest) -> None:
    def work(_runner: JobRunner) -> dict[str, Any]:
        return run_search(payload, job_id=job_id)

    JobRunner(job_id, search_steps(payload.collect)).run(
        work,
        lambda result: "done" if result.get("events") else "empty",
    )


def run_deep_analysis_job(job_id: str, topic_id: int, enrich_limit: int) -> None:
    def work(session: Session, topic: Topic, runner: JobRunner) -> dict[str, Any]:
        result = topic_ops.run_deep_analysis(
            session,
            topic,
            enrich_limit=enrich_limit,
            on_step=runner.on_step,
        )
        runner.set_step("synthesize", "done")
        runner.set_step("persist", "done")
        return result

    run_topic_job(job_id, topic_id, deep_analysis_steps(), work)


def run_academic_analysis_job(job_id: str, topic_id: int, top_n: int) -> None:
    def work(session: Session, topic: Topic, runner: JobRunner) -> dict[str, Any]:
        result = academic.run_academic_analysis(
            session,
            topic,
            top_n=top_n,
            on_step=runner.on_step,
        )
        # 只收尾仍在 running 的步骤; 保留 synthesize 可能的 "warning"(LLM 综述超时降级),
        # 不要用 mark_all_steps_done 把警告抹成 done, 否则用户看不到"综述降级了"。
        runner.mark_running_steps_done()
        return result

    run_topic_job(job_id, topic_id, academic_analysis_steps(), work)


def run_sentiment_analysis_job(job_id: str, topic_id: int, limit: int) -> None:
    def work(session: Session, topic: Topic, runner: JobRunner) -> dict[str, Any]:
        result = sentiment.run_sentiment_analysis(
            session,
            topic,
            limit=limit,
            on_step=runner.on_step,
        )
        runner.mark_all_steps_done()
        return result

    run_topic_job(
        job_id,
        topic_id,
        sentiment_analysis_steps(),
        work,
        lambda result: "done" if result.get("posts") else "empty",
    )


def run_cross_synthesis_job(job_id: str, topic_id: int, refresh_voices: bool = False) -> None:
    chain: dict[str, dict[str, Any]] = {}

    def work(session: Session, topic: Topic, runner: JobRunner) -> dict[str, Any]:
        # refresh_voices=False(深度分析 bundle 内): 三声部刚已跑并落库, 直接从 DB 合成,
        # 不重跑, 避免三声部各跑两遍(重复采集+双倍 LLM)。缺声部由 gather_voices 兜底照常合成。
        if refresh_voices:
            run_cross_voice_step(
                runner.steps,
                job_id,
                chain,
                "media",
                lambda: topic_ops.run_deep_analysis(
                    session,
                    topic,
                    enrich_limit=30,
                ),
            )
            run_cross_voice_step(
                runner.steps,
                job_id,
                chain,
                "academic",
                lambda: academic.run_academic_analysis(
                    session,
                    topic,
                    top_n=30,
                ),
            )
            run_cross_voice_step(
                runner.steps,
                job_id,
                chain,
                "sentiment",
                lambda: sentiment.run_sentiment_analysis(
                    session,
                    topic,
                    limit=25,
                ),
            )
        result = cross_synthesis.run_cross_synthesis(
            session,
            topic,
            on_step=runner.on_step,
        )
        result["chain"] = chain
        runner.mark_running_steps_done()
        return result

    run_topic_job(job_id, topic_id, cross_synthesis_steps(refresh_voices), work)


def discovery_steps() -> list[dict[str, str]]:
    return [
        {"key": "fetch", "label": "拉取注意力前沿 (HN + arXiv)", "status": "pending"},
        {"key": "annotate", "label": "LLM 标注种子 (这是什么/为何重要)", "status": "pending"},
        {"key": "persist", "label": "落盘认知前沿日报", "status": "pending"},
    ]


def enqueue_discovery_job(annotate: bool = True) -> dict[str, Any]:
    """全局发现任务 (不绑定专题), 复用通用 enqueue_job。"""
    return enqueue_job(
        query="discovery:frontier",
        steps=discovery_steps(),
        payload={"kind": "discovery", "annotate": annotate},
        target=run_discovery_job,
        args=(annotate,),
    )


def run_discovery_job(job_id: str, annotate: bool) -> None:
    from app.discovery import run as discovery_run

    runner = JobRunner(job_id, discovery_steps())

    def work(runner: JobRunner) -> dict[str, Any]:
        def on_step(key: str, status: str) -> None:
            runner.set_step(key, status)

        if not annotate:
            runner.set_step("annotate", "skipped")
        result = discovery_run.run_and_save(annotate=annotate, on_step=on_step)
        # annotate=True 时, 拉取/落盘由 on_step 推进; 标注步骤在 run_discovery 内部完成,
        # 这里补标 done (无 LLM 时优雅降级, 仍算完成)。
        if annotate:
            runner.set_step("annotate", "done")
        result["kind"] = "discovery"
        runner.mark_running_steps_done()
        return result

    runner.run(work)


def fail_job(job_id: str, exc: Exception) -> None:
    update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
    steps = job_snapshot(job_id)["steps"]
    for step in steps:
        if step["status"] == "running":
            step["status"] = "failed"
    sync_job_steps(steps, job_id)


def run_cross_voice_step(
    steps: list[dict[str, str]],
    job_id: str,
    chain: dict[str, dict[str, Any]],
    key: str,
    runner: Any,
) -> None:
    set_step(steps, key, "running", job_id)
    try:
        runner()
    except Exception as exc:  # pragma: no cover - exercised via orchestration tests
        message = f"{type(exc).__name__}: {exc}"
        chain[key] = {"status": "failed", "error": message}
        set_step(steps, key, "failed", job_id)
        update_job(job_id, result={"chain": deepcopy(chain)})
        return
    chain[key] = {"status": "done", "error": ""}
    set_step(steps, key, "done", job_id)
    update_job(job_id, result={"chain": deepcopy(chain)})


def search_steps(collect: bool) -> list[dict[str, str]]:
    return [
        {"key": "topic", "label": "创建/复用专题", "status": "pending"},
        {"key": "collect", "label": "采集新闻", "status": "pending" if collect else "skipped"},
        {"key": "analyze", "label": "本地分析", "status": "pending"},
    ]


def deep_analysis_steps() -> list[dict[str, str]]:
    return [
        {"key": "enrich", "label": "LLM 富化报道", "status": "pending"},
        {"key": "synthesize", "label": "LLM 综合分析", "status": "pending"},
        {"key": "persist", "label": "写入专题档案", "status": "pending"},
    ]


def academic_analysis_steps() -> list[dict[str, str]]:
    return [
        {"key": "fetch", "label": "拉取 OpenAlex 论文", "status": "pending"},
        {"key": "graph", "label": "构建收敛引用图与学派", "status": "pending"},
        {"key": "synthesize", "label": "LLM 综合学界共识", "status": "pending"},
        {"key": "persist", "label": "写入学界层", "status": "pending"},
    ]


def sentiment_analysis_steps() -> list[dict[str, str]]:
    return [
        {"key": "fetch", "label": "拉取多平台民间讨论", "status": "pending"},
        {"key": "summarize", "label": "LLM 批判性总结民间情绪", "status": "pending"},
        {"key": "persist", "label": "写入民间情绪层", "status": "pending"},
    ]


def cross_synthesis_steps(refresh_voices: bool = False) -> list[dict[str, str]]:
    # refresh_voices=False(深度分析 bundle 内): 只用已落库声部, 不重跑三声部, 故只有 3 步。
    # 否则前端会显示 6 步但轻量 job 只跑 3 步。
    voice_steps = [
        {"key": "media", "label": "媒体声部：LLM 深度分析", "status": "pending"},
        {"key": "academic", "label": "学界声部：论文与共识", "status": "pending"},
        {"key": "sentiment", "label": "民间声部：多平台情绪", "status": "pending"},
    ] if refresh_voices else []
    return [
        *voice_steps,
        {"key": "gather", "label": "汇总可用声部", "status": "pending"},
        {"key": "synthesize", "label": "综合三方对照", "status": "pending"},
        {"key": "persist", "label": "写入三方对照", "status": "pending"},
    ]


def set_step(
    steps: list[dict[str, str]],
    key: str,
    status: str,
    job_id: str | None = None,
) -> None:
    for step in steps:
        if step["key"] == key:
            step["status"] = status
            break
    sync_job_steps(steps, job_id)


def sync_job_steps(steps: list[dict[str, str]], job_id: str | None) -> None:
    if job_id:
        update_job(job_id, steps=deepcopy(steps))


def update_job(job_id: str, **updates: Any) -> None:
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            return
        for key, value in updates.items():
            setattr(job, key, value)
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()


def job_snapshot(job_id: str) -> dict[str, Any]:
    init_db()
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Search job not found")
        return search_job_payload(job)


def trim_search_jobs() -> None:
    with Session(engine) as session:
        jobs = session.exec(select(SearchJob).order_by(SearchJob.updated_at.desc())).all()
        if len(jobs) <= MAX_SEARCH_JOBS:
            return
        removable = [
            job
            for job in reversed(jobs)
            if job.status in {"done", "empty", "failed", "interrupted"}
        ]
        for job in removable[: max(0, len(jobs) - MAX_SEARCH_JOBS)]:
            session.delete(job)
        session.commit()


def mark_interrupted_search_jobs(job_ids: set[str] | None = None) -> int:
    with Session(engine) as session:
        stmt = select(SearchJob).where(SearchJob.status.in_(["queued", "running"]))
        if job_ids is not None:
            stmt = stmt.where(SearchJob.id.in_(job_ids))
        jobs = session.exec(stmt).all()
        for job in jobs:
            job.status = "interrupted"
            job.error = "服务重启或进程退出时任务尚未完成，已标记为中断。请重新提交搜索。"
            job.steps = interrupted_steps(job.steps)
            job.updated_at = datetime.utcnow()
            session.add(job)
        if jobs:
            session.commit()
        return len(jobs)


def interrupted_steps(steps: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for step in steps or []:
        next_step = dict(step)
        if next_step.get("status") in {"pending", "running"}:
            next_step["status"] = "interrupted"
        out.append(next_step)
    return out


def search_job_payload(job: SearchJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "query": job.query,
        "status": job.status,
        "steps": job.steps,
        "created_at": payloads.iso(job.created_at),
        "updated_at": payloads.iso(job.updated_at),
        "result": job.result,
        "error": job.error,
    }


def request_payload(payload: SearchRequest) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def search_request_from_job(job: SearchJob) -> SearchRequest:
    data = dict(job.payload or {})
    data.setdefault("query", job.query)
    return SearchRequest(**data)
