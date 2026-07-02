"""Read-only FastAPI surface for the dossier database."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.db import (
    Analysis,
    Article,
    CognitionMark,
    CognitionProfile,
    SentimentPost,
    SourceFraming,
    TimelineEvent,
    Topic,
    TopicArticle,
    SearchJob,
    engine,
    init_db,
)
from app.pipeline import local_analyze, narrative_signals
from app.schemas.search import AcademicAnalysisRequest, CognitionMarkRequest, CrossSynthesisRequest, DeepAnalysisRequest, DiscoveryDistillRequest, SearchRequest, SentimentAnalysisRequest
from app.services import article_perspective, country_compare, payloads, search_service
from app.pipeline import academic, cross_synthesis, sentiment

DEFAULT_COGNITION_PROFILE = [
    ("ai_infra", "AI / 算力基础设施", "partial", "知晓 CPU、GPU、CPO、算力中心、大模型等词，但不懂具体机制与实现。"),
    ("geopolitics", "地缘政治基础", "partial", "主要来自中国教科书和文科背景。"),
    ("finance", "金融 / 经济 / 公司财务", "strong_partial", "修过货币银行学、微观、宏观、公司理财、会计、财报分析、国际商务与国际金融。"),
    ("energy", "能源 / 核能 / 新能源", "unfamiliar", "只在身边新闻中听说，没有主动了解。"),
    ("biotech", "生物科技", "unfamiliar", "一窍不通。"),
    ("open_source", "开源社区", "partial", "主要知道 GitHub。"),
    ("crypto", "加密 / 稳定币", "unfamiliar", "听说过稳定币、比特币、以太币，但没有持有、交易或亲眼所见。"),
    ("middle_east_security", "中东安全 / 国际冲突", "partial", "主要来自 B 站时政博主分析。"),
    ("industrial_policy", "产业政策", "unfamiliar", "只在身边新闻中有所耳闻。"),
    ("social_mood", "社会情绪", "partial", "能通过社交媒体感受到一些。"),
]

app = FastAPI(
    title="Dossier API",
    version="0.1.0",
    description="Read-only API for collected topic dossiers.",
)

app.add_middleware(
    CORSMiddleware,
    # 本地开发: 放行任意 localhost / 127.0.0.1 端口 (Vite 端口被占时会自动跳 5174/5175...),
    # 避免端口漂移导致前端跨域报"无法连接后端"。仅匹配本地回环, 不放行外部来源。
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    search_service.mark_interrupted_search_jobs()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/topics")
def list_topics() -> list[dict[str, Any]]:
    with Session(engine) as session:
        topics = session.exec(select(Topic).order_by(Topic.created_at.desc())).all()
        return [payloads.topic_summary(session, topic) for topic in topics]


@app.get("/api/topics/{topic_id}")
def get_topic(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        summary = payloads.topic_summary(session, topic)
        timeline = session.exec(
            select(TimelineEvent)
            .where(TimelineEvent.topic_id == topic_id)
            .order_by(TimelineEvent.date)
        ).all()
        framing = session.exec(
            select(SourceFraming).where(SourceFraming.topic_id == topic_id)
        ).all()
        analyses = session.exec(
            select(Analysis)
            .where(Analysis.topic_id == topic_id)
            .order_by(Analysis.generated_at.desc())
        ).all()

        summary["timeline"] = [payloads.timeline_event(row) for row in timeline]
        summary["framing"] = [payloads.source_framing(row) for row in framing]
        summary["analysis"] = payloads.analysis_payload(analyses[0]) if analyses else None
        return summary


@app.get("/api/topics/{topic_id}/articles")
def list_articles(
    topic_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        rows = session.exec(
            select(TopicArticle, Article)
            .where(TopicArticle.article_id == Article.id)
            .where(TopicArticle.topic_id == topic_id)
        ).all()
        rows.sort(key=lambda pair: pair[1].published_at or datetime.min, reverse=True)
        page = rows[offset : offset + limit]

        return {
            "total": len(rows),
            "limit": limit,
            "offset": offset,
            "items": [payloads.article_payload(topic_article, article) for topic_article, article in page],
        }


@app.get("/api/topics/{topic_id}/articles/{article_id}/perspective")
def article_perspective_view(topic_id: int, article_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        link = session.get(TopicArticle, (topic_id, article_id))
        article = session.get(Article, article_id) if link else None
        if not article:
            raise HTTPException(status_code=404, detail="Article not found in topic")
        return article_perspective.analyze_article(article)


@app.get("/api/topics/{topic_id}/local-events")
def local_events(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        rows = session.exec(
            select(TopicArticle, Article)
            .where(TopicArticle.article_id == Article.id)
            .where(TopicArticle.topic_id == topic_id)
            .where(TopicArticle.relevant == True)  # noqa: E712
        ).all()
        evidence_lookup = payloads.article_evidence_lookup(rows)
        article_rows = [
            local_analyze.ArticleRow(
                id=article.id,
                title=article.title_zh or article.title,
                source=article.source,
                published_at=article.published_at,
                snippet=article.snippet_zh or article.snippet,
                relevance=topic_article.relevance,
                stance=topic_article.stance
                or local_analyze.infer_stance(
                    article.title_zh or article.title,
                    article.snippet_zh or article.snippet,
                ),
            )
            for topic_article, article in rows
        ]
        data = local_analyze.analyze_topic(topic.name, article_rows)
        data["events"] = payloads.attach_event_evidence(data["events"], evidence_lookup)
        return {
            "topic_id": topic_id,
            "events": data["events"],
            "framing": data["framing"],
            "analysis_md": data["analysis_md"],
            "stance_evolution": data["stance_evolution"],
            "keywords": data["keywords"],
            "entities": data["entities"],
            "entity_groups": data["entity_groups"],
            "criteria": data["criteria"],
            "narrative_signals": narrative_signals.detect_narrative_signals(article_rows),
        }


@app.get("/api/topics/{topic_id}/country-compare")
def country_compare_view(
    topic_id: int,
    article_ids: list[str] | None = Query(default=None),
) -> dict[str, Any]:
    scoped_article_ids = parse_article_ids(article_ids)
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return country_compare.build_country_compare(session, topic, scoped_article_ids)


@app.get("/api/topics/{topic_id}/academic")
def academic_view(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return academic.academic_payload(
            session,
            topic,
            summary_md=latest_academic_summary(session, topic),
        )


@app.get("/api/topics/{topic_id}/sentiment")
def sentiment_view(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return sentiment.sentiment_payload_from_db(
            session,
            topic,
            summary_md=latest_sentiment_summary(session, topic),
        )


@app.get("/api/topics/{topic_id}/cross-synthesis")
def cross_synthesis_view(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return cross_synthesis.cross_synthesis_payload_from_db(session, topic)


@app.post("/api/search")
def search_and_collect(payload: SearchRequest) -> dict[str, Any]:
    return search_service.run_search(payload)


@app.post("/api/search/jobs")
def create_search_job(payload: SearchRequest) -> dict[str, Any]:
    return search_service.enqueue_search_job(payload)


@app.post("/api/topics/{topic_id}/deep-analysis/jobs")
def create_deep_analysis_job(
    topic_id: int,
    payload: DeepAnalysisRequest | None = None,
) -> dict[str, Any]:
    enrich_limit = payload.enrich_limit if payload else 30
    return search_service.enqueue_deep_analysis_job(topic_id, enrich_limit)


@app.post("/api/topics/{topic_id}/academic/jobs")
def create_academic_analysis_job(
    topic_id: int,
    payload: AcademicAnalysisRequest | None = None,
) -> dict[str, Any]:
    top_n = payload.top_n if payload else 30
    return search_service.enqueue_academic_analysis_job(topic_id, top_n)


@app.post("/api/topics/{topic_id}/sentiment/jobs")
def create_sentiment_analysis_job(
    topic_id: int,
    payload: SentimentAnalysisRequest | None = None,
) -> dict[str, Any]:
    limit = payload.limit if payload else 25
    return search_service.enqueue_sentiment_analysis_job(topic_id, limit)


@app.post("/api/topics/{topic_id}/cross-synthesis/jobs")
def create_cross_synthesis_job(
    topic_id: int,
    payload: CrossSynthesisRequest | None = None,
) -> dict[str, Any]:
    refresh_voices = payload.refresh_voices if payload else True
    return search_service.enqueue_cross_synthesis_job(topic_id, refresh_voices=refresh_voices)


@app.post("/api/search/jobs/{job_id}/rerun")
def rerun_search_job(job_id: str) -> dict[str, Any]:
    return search_service.rerun_search_job(job_id)


@app.get("/api/discovery/latest")
def get_latest_discovery() -> dict[str, Any]:
    from app.discovery import run as discovery_run

    report = discovery_run.latest_report()
    if report is None:
        raise HTTPException(status_code=404, detail="还没有任何认知前沿日报。点击「立即分析」生成第一份。")
    return report


@app.post("/api/discovery/jobs")
def create_discovery_job(annotate: bool = Query(default=True)) -> dict[str, Any]:
    return search_service.enqueue_discovery_job(annotate=annotate)


@app.post("/api/discovery/distill")
def distill_discovery_seed(payload: DiscoveryDistillRequest) -> dict[str, Any]:
    """把一条发现种子的长标题提炼成简短新闻话题词 (供事件分析台搜索)。

    同步单次调用 (非后台 job); 无 LLM 时降级返回启发式截断, llm=false。
    """
    from app.discovery import annotate as discovery_annotate

    return discovery_annotate.distill_topic(payload.title, payload.domain or "")


@app.put("/api/cognition/marks")
def upsert_cognition_mark(payload: CognitionMarkRequest) -> dict[str, Any]:
    if payload.target_type == "seed" and not payload.target_key:
        raise HTTPException(status_code=422, detail="seed mark requires target_key")
    if payload.target_type != "seed" and payload.target_id < 1:
        raise HTTPException(status_code=422, detail="target_id must be >= 1")
    with Session(engine) as session:
        statement = select(CognitionMark).where(CognitionMark.target_type == payload.target_type)
        if payload.target_type == "seed":
            statement = statement.where(CognitionMark.target_key == payload.target_key)
        else:
            statement = (
                statement
                .where(CognitionMark.target_id == payload.target_id)
                .where(CognitionMark.topic_id == payload.topic_id)
            )
        mark = session.exec(statement).first()
        if not mark:
            mark = CognitionMark(
                target_type=payload.target_type,
                target_id=payload.target_id,
                target_key=payload.target_key,
                topic_id=payload.topic_id,
            )
        mark.label = payload.label
        mark.note = payload.note.strip()
        mark.updated_at = datetime.utcnow()
        session.add(mark)
        session.commit()
        session.refresh(mark)
        return cognition_mark_payload(mark)


@app.get("/api/cognition/marks")
def list_cognition_marks(
    topic_id: int | None = Query(default=None),
    target_type: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    with Session(engine) as session:
        statement = select(CognitionMark).order_by(CognitionMark.updated_at.desc())
        if topic_id is not None:
            statement = statement.where(CognitionMark.topic_id == topic_id)
        if target_type:
            statement = statement.where(CognitionMark.target_type == target_type)
        return [cognition_mark_payload(mark) for mark in session.exec(statement).all()]


@app.get("/api/cognition/marks/summary")
def cognition_mark_summary() -> dict[str, Any]:
    with Session(engine) as session:
        marks = session.exec(select(CognitionMark).order_by(CognitionMark.updated_at.desc())).all()
        counts: dict[str, int] = {}
        for mark in marks:
            counts[mark.label] = counts.get(mark.label, 0) + 1
        return {
            "counts": counts,
            "recent": [cognition_mark_payload(mark) for mark in marks[:20]],
            "unfamiliar_topics": cognition_unfamiliar_topics(session, marks),
        }


@app.get("/api/cognition/profile")
def cognition_profile() -> list[dict[str, Any]]:
    with Session(engine) as session:
        return [cognition_profile_payload(item) for item in ensure_cognition_profile(session)]


@app.put("/api/cognition/profile")
def update_cognition_profile(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with Session(engine) as session:
        existing = {item.domain_key: item for item in ensure_cognition_profile(session)}
        for row in items:
            key = str(row.get("domain_key", "")).strip()
            if key not in existing:
                continue
            item = existing[key]
            item.level = str(row.get("level", item.level)).strip() or item.level
            item.note = str(row.get("note", item.note)).strip()
            item.updated_at = datetime.utcnow()
            session.add(item)
        session.commit()
        return [cognition_profile_payload(item) for item in ensure_cognition_profile(session)]


@app.get("/api/search/jobs/{job_id}")
def get_search_job(job_id: str) -> dict[str, Any]:
    return search_service.job_snapshot(job_id)


def cognition_mark_payload(mark: CognitionMark) -> dict[str, Any]:
    return {
        "id": mark.id,
        "target_type": mark.target_type,
        "target_id": mark.target_id,
        "target_key": mark.target_key,
        "topic_id": mark.topic_id,
        "label": mark.label,
        "note": mark.note,
        "updated_at": payloads.iso(mark.updated_at),
    }


def ensure_cognition_profile(session: Session) -> list[CognitionProfile]:
    rows = session.exec(select(CognitionProfile).order_by(CognitionProfile.id)).all()
    if rows:
        return rows
    for domain_key, domain_label, level, note in DEFAULT_COGNITION_PROFILE:
        session.add(CognitionProfile(
            domain_key=domain_key,
            domain_label=domain_label,
            level=level,
            note=note,
        ))
    session.commit()
    return session.exec(select(CognitionProfile).order_by(CognitionProfile.id)).all()


def cognition_profile_payload(item: CognitionProfile) -> dict[str, Any]:
    return {
        "id": item.id,
        "domain_key": item.domain_key,
        "domain_label": item.domain_label,
        "level": item.level,
        "note": item.note,
        "updated_at": payloads.iso(item.updated_at),
    }


def cognition_unfamiliar_topics(session: Session, marks: list[CognitionMark]) -> list[dict[str, Any]]:
    counts: dict[int, int] = {}
    for mark in marks:
        if mark.label == "unfamiliar" and mark.topic_id:
            counts[mark.topic_id] = counts.get(mark.topic_id, 0) + 1
    if not counts:
        return []

    topics = {
        topic.id: topic.name
        for topic in session.exec(select(Topic).where(Topic.id.in_(counts.keys()))).all()
        if topic.id is not None
    }
    return [
        {"topic_id": topic_id, "topic": topics.get(topic_id, f"#{topic_id}"), "count": count}
        for topic_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]


def parse_article_ids(values: list[str] | None) -> list[int] | None:
    if not values:
        return None
    ids: list[int] = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                ids.append(int(part))
    return ids or None


def latest_academic_summary(session: Session, topic: Topic) -> str:
    jobs = session.exec(
        select(SearchJob)
        .where(SearchJob.status == "done")
        .where(SearchJob.query == f"academic:{topic.name}")
        .order_by(SearchJob.updated_at.desc(), SearchJob.created_at.desc())
    ).all()
    for job in jobs:
        payload = job.payload or {}
        if payload.get("kind") != "academic_analysis":
            continue
        if int(payload.get("topic_id") or 0) != topic.id:
            continue
        result = job.result or {}
        summary = result.get("summary_md")
        if isinstance(summary, str) and summary.strip():
            return summary
    return ""


def latest_sentiment_summary(session: Session, topic: Topic) -> str:
    jobs = session.exec(
        select(SearchJob)
        .where(SearchJob.status == "done")
        .where(SearchJob.query == f"sentiment:{topic.name}")
        .order_by(SearchJob.updated_at.desc(), SearchJob.created_at.desc())
    ).all()
    for job in jobs:
        payload = job.payload or {}
        if payload.get("kind") != "sentiment_analysis":
            continue
        if int(payload.get("topic_id") or 0) != topic.id:
            continue
        result = job.result or {}
        summary = result.get("summary_md")
        if isinstance(summary, str) and summary.strip():
            return summary
    return ""
