"""Search request orchestration and background job lifecycle management."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Thread
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app import topic_ops
from app.db import SearchJob, Topic, engine, init_db
from app.pipeline import academic, cross_synthesis, sentiment
from app.schemas.search import SearchRequest
from app.services import payloads


MAX_SEARCH_JOBS = 50


def enqueue_search_job(payload: SearchRequest) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        job = SearchJob(
            id=job_id,
            query=payload.query.strip(),
            status="queued",
            steps=search_steps(payload.collect),
            payload=request_payload(payload),
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=run_search_job, args=(job_id, payload), daemon=True).start()
    return job_snapshot(job_id)


def rerun_search_job(job_id: str) -> dict[str, Any]:
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Search job not found")
        if job.status not in {"interrupted", "failed"}:
            raise HTTPException(status_code=409, detail="Only interrupted or failed jobs can be rerun")
        payload = search_request_from_job(job)
    return enqueue_search_job(payload)


def enqueue_deep_analysis_job(topic_id: int, enrich_limit: int = 30) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        job = SearchJob(
            id=job_id,
            query=f"deep-analysis:{topic.name}",
            status="queued",
            steps=deep_analysis_steps(),
            payload={"topic_id": topic_id, "enrich_limit": enrich_limit, "kind": "deep_analysis"},
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=run_deep_analysis_job, args=(job_id, topic_id, enrich_limit), daemon=True).start()
    return job_snapshot(job_id)


def enqueue_academic_analysis_job(topic_id: int, top_n: int = 30) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        job = SearchJob(
            id=job_id,
            query=f"academic:{topic.name}",
            status="queued",
            steps=academic_analysis_steps(),
            payload={"topic_id": topic_id, "top_n": top_n, "kind": "academic_analysis"},
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=run_academic_analysis_job, args=(job_id, topic_id, top_n), daemon=True).start()
    return job_snapshot(job_id)


def enqueue_sentiment_analysis_job(topic_id: int, limit: int = 25) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        job = SearchJob(
            id=job_id,
            query=f"sentiment:{topic.name}",
            status="queued",
            steps=sentiment_analysis_steps(),
            payload={"topic_id": topic_id, "limit": limit, "kind": "sentiment_analysis"},
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=run_sentiment_analysis_job, args=(job_id, topic_id, limit), daemon=True).start()
    return job_snapshot(job_id)


def enqueue_cross_synthesis_job(topic_id: int) -> dict[str, Any]:
    job_id = uuid4().hex
    init_db()
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        job = SearchJob(
            id=job_id,
            query=f"cross-synthesis:{topic.name}",
            status="queued",
            steps=cross_synthesis_steps(),
            payload={"topic_id": topic_id, "kind": "cross_synthesis"},
        )
        session.add(job)
        session.commit()

    trim_search_jobs()
    Thread(target=run_cross_synthesis_job, args=(job_id, topic_id), daemon=True).start()
    return job_snapshot(job_id)


def run_search(payload: SearchRequest, job_id: str | None = None) -> dict[str, Any]:
    init_db()
    with Session(engine) as session:
        query = payload.query.strip()
        steps = search_steps(payload.collect)
        set_step(steps, "topic", "running", job_id)
        topic = topic_ops.get_or_create_topic(
            session,
            query,
            topic_ops.query_variants(query),
        )
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
        }


def run_search_job(job_id: str, payload: SearchRequest) -> None:
    update_job(job_id, status="running")
    try:
        result = run_search(payload, job_id=job_id)
        update_job(
            job_id,
            status="done" if result.get("events") else "empty",
            result=result,
            error="",
        )
    except Exception as exc:  # pragma: no cover - defensive task boundary
        update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        steps = job_snapshot(job_id)["steps"]
        for step in steps:
            if step["status"] == "running":
                step["status"] = "failed"
        sync_job_steps(steps, job_id)


def run_deep_analysis_job(job_id: str, topic_id: int, enrich_limit: int) -> None:
    update_job(job_id, status="running")
    steps = deep_analysis_steps()

    def on_step(key: str, status: str, details: dict[str, Any] | None = None) -> None:
        set_step(steps, key, status, job_id)
        if details is not None:
            update_job(job_id, result={"progress": {"step": key, **details}})

    try:
        init_db()
        with Session(engine) as session:
            topic = session.get(Topic, topic_id)
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            result = topic_ops.run_deep_analysis(
                session,
                topic,
                enrich_limit=enrich_limit,
                on_step=on_step,
            )
        set_step(steps, "synthesize", "done", job_id)
        set_step(steps, "persist", "done", job_id)
        update_job(
            job_id,
            status="done",
            result=result,
            error="",
        )
    except Exception as exc:  # pragma: no cover - defensive task boundary
        update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        snapshot_steps = job_snapshot(job_id)["steps"]
        for step in snapshot_steps:
            if step["status"] == "running":
                step["status"] = "failed"
        sync_job_steps(snapshot_steps, job_id)


def run_academic_analysis_job(job_id: str, topic_id: int, top_n: int) -> None:
    update_job(job_id, status="running")
    steps = academic_analysis_steps()

    def on_step(key: str, status: str, details: dict[str, Any] | None = None) -> None:
        set_step(steps, key, status, job_id)
        if details is not None:
            update_job(job_id, result={"progress": {"step": key, **details}})

    try:
        init_db()
        with Session(engine) as session:
            topic = session.get(Topic, topic_id)
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            result = academic.run_academic_analysis(
                session,
                topic,
                top_n=top_n,
                on_step=on_step,
            )
        for step in steps:
            step["status"] = "done"
        sync_job_steps(steps, job_id)
        update_job(job_id, status="done", result=result, error="")
    except Exception as exc:  # pragma: no cover - defensive task boundary
        update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        snapshot_steps = job_snapshot(job_id)["steps"]
        for step in snapshot_steps:
            if step["status"] == "running":
                step["status"] = "failed"
        sync_job_steps(snapshot_steps, job_id)


def run_sentiment_analysis_job(job_id: str, topic_id: int, limit: int) -> None:
    update_job(job_id, status="running")
    steps = sentiment_analysis_steps()

    def on_step(key: str, status: str, details: dict[str, Any] | None = None) -> None:
        set_step(steps, key, status, job_id)
        if details is not None:
            update_job(job_id, result={"progress": {"step": key, **details}})

    try:
        init_db()
        with Session(engine) as session:
            topic = session.get(Topic, topic_id)
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            result = sentiment.run_sentiment_analysis(
                session,
                topic,
                limit=limit,
                on_step=on_step,
            )
        for step in steps:
            step["status"] = "done"
        sync_job_steps(steps, job_id)
        update_job(job_id, status="done" if result.get("posts") else "empty", result=result, error="")
    except Exception as exc:  # pragma: no cover - defensive task boundary
        update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        snapshot_steps = job_snapshot(job_id)["steps"]
        for step in snapshot_steps:
            if step["status"] == "running":
                step["status"] = "failed"
        sync_job_steps(snapshot_steps, job_id)


def run_cross_synthesis_job(job_id: str, topic_id: int) -> None:
    update_job(job_id, status="running")
    steps = cross_synthesis_steps()
    chain: dict[str, dict[str, Any]] = {}

    def on_step(key: str, status: str, details: dict[str, Any] | None = None) -> None:
        set_step(steps, key, status, job_id)
        if details is not None:
            update_job(job_id, result={"progress": {"step": key, **details}})

    try:
        init_db()
        with Session(engine) as session:
            topic = session.get(Topic, topic_id)
            if not topic:
                raise HTTPException(status_code=404, detail="Topic not found")
            run_cross_voice_step(
                steps,
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
                steps,
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
                steps,
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
                on_step=on_step,
            )
        result["chain"] = chain
        for step in steps:
            if step["status"] == "running":
                step["status"] = "done"
        sync_job_steps(steps, job_id)
        update_job(job_id, status="done", result=result, error="")
    except Exception as exc:  # pragma: no cover - defensive task boundary
        update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")
        snapshot_steps = job_snapshot(job_id)["steps"]
        for step in snapshot_steps:
            if step["status"] == "running":
                step["status"] = "failed"
        sync_job_steps(snapshot_steps, job_id)


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


def cross_synthesis_steps() -> list[dict[str, str]]:
    return [
        {"key": "media", "label": "媒体声部：LLM 深度分析", "status": "pending"},
        {"key": "academic", "label": "学界声部：论文与共识", "status": "pending"},
        {"key": "sentiment", "label": "民间声部：多平台情绪", "status": "pending"},
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
