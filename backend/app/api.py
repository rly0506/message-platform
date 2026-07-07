"""Read-only FastAPI surface for the dossier database."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app import topic_ops
from app.db import (
    Analysis,
    Article,
    CognitionMark,
    CognitionProfile,
    Project,
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
from app.services import article_perspective, auto_refresh, country_compare, evidence_package, opencli_diagnostics, payloads, search_service, source_registry
from app.pipeline import academic, cross_synthesis, sentiment

DEFAULT_COGNITION_PROFILE = [
    {
        "domain_key": "ai_infra",
        "domain_label": "AI / 算力基础设施",
        "level": "partial",
        "note": "知晓 CPU、GPU、CPO、算力中心、大模型等词，但不懂具体机制与实现。",
        "depth": "terms",
        "interest": "high",
        "confidence": 60,
        "evidence": "用户自述知道 CPU/GPU/CPO/算力中心/大模型，但不懂具体实现。",
        "recommended_seed_style": "mechanism",
    },
    {
        "domain_key": "finance",
        "domain_label": "金融 / 经济 / 公司财务",
        "level": "strong_partial",
        "note": "修过货币银行学、微观、宏观、公司理财、会计、财报分析、国际商务与国际金融。",
        "depth": "coursework",
        "interest": "high",
        "confidence": 75,
        "evidence": "用户列出金融、会计、财报和国际金融课程背景。",
        "recommended_seed_style": "financial_model",
    },
    {
        "domain_key": "macro_finance",
        "domain_label": "宏观金融 / 流动性",
        "level": "partial",
        "note": "能调用货币理论、利率、投资、汇率和资产配置框架，但需要继续校准现实口径。",
        "depth": "model",
        "interest": "high",
        "confidence": 65,
        "evidence": "用户用凯恩斯货币理论和国际金融解释降息影响。",
        "recommended_seed_style": "macro_model",
    },
    {
        "domain_key": "open_source",
        "domain_label": "开源生态 / GitHub",
        "level": "partial",
        "note": "主要知道 GitHub 和 star，开始意识到安全性与商业使用风险。",
        "depth": "terms",
        "interest": "high",
        "confidence": 58,
        "evidence": "用户选择 GitHub/技术前沿，并提到 star 与开源安全风险。",
        "recommended_seed_style": "evaluation",
    },
    {
        "domain_key": "energy",
        "domain_label": "能源 / 核能 / 新能源",
        "level": "unfamiliar",
        "note": "只在身边新闻中听说，没有主动了解。",
        "depth": "none",
        "interest": "medium",
        "confidence": 55,
        "evidence": "用户自述能源、新能源、核能较陌生。",
        "recommended_seed_style": "mechanism",
    },
    {
        "domain_key": "electricity",
        "domain_label": "电力系统 / 数据中心供能",
        "level": "unfamiliar",
        "note": "能判断电力是 AI 底层，但对发电结构、电网、用电曲线和替代能源机制不熟。",
        "depth": "intuition",
        "interest": "medium",
        "confidence": 55,
        "evidence": "用户质疑核电公司是否一定最受益，并追问聚变/裂变和其他能源。",
        "recommended_seed_style": "comparison",
    },
    {
        "domain_key": "biotech",
        "domain_label": "生物医药 / 生命科学",
        "level": "unfamiliar",
        "note": "一窍不通，看到突破类新闻容易惊叹后划走。",
        "depth": "none",
        "interest": "low",
        "confidence": 70,
        "evidence": "用户自述对生物和医药一窍不通。",
        "recommended_seed_style": "paper_check",
    },
    {
        "domain_key": "crypto",
        "domain_label": "加密 / 稳定币",
        "level": "unfamiliar",
        "note": "听说过稳定币、比特币、以太币，但没有持有、交易或亲眼所见。",
        "depth": "terms",
        "interest": "medium",
        "confidence": 60,
        "evidence": "用户能从货币锚定、储备资产、世界央行缺位等角度提出疑问。",
        "recommended_seed_style": "risk_check",
    },
    {
        "domain_key": "geopolitics",
        "domain_label": "地缘政治 / 产业竞争",
        "level": "partial",
        "note": "主要来自中国教科书、文科背景和 B 站时政博主分析。",
        "depth": "narrative",
        "interest": "medium",
        "confidence": 58,
        "evidence": "用户能用替代品、产业建设和算法突破解释芯片出口限制。",
        "recommended_seed_style": "multi_angle",
    },
    {
        "domain_key": "industrial_policy",
        "domain_label": "产业政策",
        "level": "unfamiliar",
        "note": "只在身边新闻中有所耳闻。",
        "depth": "none",
        "interest": "medium",
        "confidence": 50,
        "evidence": "用户将产业政策列为陌生领域。",
        "recommended_seed_style": "mechanism",
    },
    {
        "domain_key": "law_regulation",
        "domain_label": "法律 / 监管",
        "level": "unfamiliar",
        "note": "监管框架、合规责任、支付/数据/平台规则需要从案例中补。",
        "depth": "none",
        "interest": "medium",
        "confidence": 45,
        "evidence": "规划中需要拓展到法律监管，当前缺少稳定画像证据。",
        "recommended_seed_style": "risk_check",
    },
    {
        "domain_key": "social_structure",
        "domain_label": "社会结构 / 人群变化",
        "level": "partial",
        "note": "能通过社交媒体感受到社会情绪，但机制和结构解释仍需校准。",
        "depth": "intuition",
        "interest": "medium",
        "confidence": 50,
        "evidence": "用户自述能通过社交媒体感受到一些社会情绪。",
        "recommended_seed_style": "multi_angle",
    },
    {
        "domain_key": "engineering_infra",
        "domain_label": "工程基础 / 基础设施",
        "level": "unfamiliar",
        "note": "对工程实现、基础设施约束和物理系统机制仍需要补课。",
        "depth": "none",
        "interest": "medium",
        "confidence": 45,
        "evidence": "用户多次追问机制和实现，但对工程细节自述陌生。",
        "recommended_seed_style": "mechanism",
    },
    {
        "domain_key": "media_literacy",
        "domain_label": "媒体识读 / 话术识别",
        "level": "partial",
        "note": "能识别绝对化、焦虑贩卖和缺乏事实依据的表达，但需要沉淀成工作流。",
        "depth": "pattern",
        "interest": "high",
        "confidence": 65,
        "evidence": "用户会追问“如何证明”“6个月如何得出”“是否传播焦虑”。",
        "recommended_seed_style": "rhetoric_check",
    },
]

SEED_DOMAIN_PROFILE_MAP = {
    "tech": "ai_infra",
    "finance": "finance",
    "geopolitics": "geopolitics",
    "science": "biotech",
    "society": "social_structure",
}

COGNITION_MARK_DELTAS = {
    "known": 5,
    "doubtful": 0,
    "unfamiliar": -5,
}

app = FastAPI(
    title="Dossier API",
    version="0.1.0",
    description="Read-only API for collected topic dossiers.",
)

app.add_middleware(
    CORSMiddleware,
    # Dev only: allow localhost, private LAN, and Tailscale origins so Vite
    # port drift and phone debugging can still reach the API.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    search_service.mark_interrupted_search_jobs()
    auto_refresh.start_auto_refresh_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    auto_refresh.stop_auto_refresh_scheduler()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/integrations/opencli/diagnostics")
def opencli_diagnostics_view() -> dict[str, Any]:
    return opencli_diagnostics.diagnose_opencli()


@app.get("/api/sources")
def list_sources() -> list[dict[str, Any]]:
    with Session(engine) as session:
        return source_registry.list_sources(session)


@app.post("/api/sources")
def create_source(payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        return source_registry.create_source(session, payload)


@app.post("/api/sources/import")
def import_sources(payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        return source_registry.import_sources(session, payload)


@app.patch("/api/sources/{source_id}")
def update_source(source_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        return source_registry.update_source(session, source_id, payload)


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    with Session(engine) as session:
        ensure_topic_projects(session)
        projects = session.exec(select(Project).order_by(Project.created_at.desc())).all()
        return [payloads.project_summary(session, project) for project in projects]


@app.post("/api/projects")
def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    name = clean_required_text(payload.get("name"), "Project name is required")
    with Session(engine) as session:
        project = Project(
            name=name,
            description=clean_text(payload.get("description")),
            status=clean_status(payload.get("status"), "active"),
        )
        if project.status == "archived":
            project.archived_at = datetime.utcnow()
        session.add(project)
        session.commit()
        session.refresh(project)
        return payloads.project_summary(session, project)


@app.patch("/api/projects/{project_id}")
def update_project(project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if "name" in payload:
            project.name = clean_required_text(payload.get("name"), "Project name is required")
        if "description" in payload:
            project.description = clean_text(payload.get("description"))
        if "status" in payload:
            apply_status(project, clean_status(payload.get("status"), project.status))
        project.updated_at = datetime.utcnow()
        session.add(project)
        session.commit()
        session.refresh(project)
        return payloads.project_summary(session, project)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        topics = session.exec(select(Topic).where(Topic.project_id == project_id)).all()
        if topics:
            raise HTTPException(status_code=409, detail="Project still has topics")
        session.delete(project)
        session.commit()
        return {"deleted": True, "project_id": project_id}


@app.get("/api/topics")
def list_topics() -> list[dict[str, Any]]:
    with Session(engine) as session:
        ensure_topic_projects(session)
        topics = session.exec(select(Topic).order_by(Topic.created_at.desc())).all()
        return [payloads.topic_summary(session, topic) for topic in topics]


@app.post("/api/topics")
def create_topic(payload: dict[str, Any]) -> dict[str, Any]:
    name = clean_required_text(payload.get("name"), "Topic name is required")
    with Session(engine) as session:
        project = project_for_topic_payload(session, payload, name)
        topic = Topic(
            project_id=project.id,
            name=name,
            description=clean_text(payload.get("description")),
            queries=clean_queries(payload.get("queries"), name),
            status=clean_status(payload.get("status"), "active"),
        )
        if topic.status == "archived":
            topic.archived_at = datetime.utcnow()
        session.add(topic)
        session.commit()
        session.refresh(topic)
        return payloads.topic_summary(session, topic)


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


@app.patch("/api/topics/{topic_id}")
def update_topic(topic_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        if "project_id" in payload:
            project_id = int(payload.get("project_id") or 0)
            if not session.get(Project, project_id):
                raise HTTPException(status_code=404, detail="Project not found")
            topic.project_id = project_id
        if "name" in payload:
            topic.name = clean_required_text(payload.get("name"), "Topic name is required")
        if "description" in payload:
            topic.description = clean_text(payload.get("description"))
        if "queries" in payload:
            topic.queries = clean_queries(payload.get("queries"), topic.name)
        if "status" in payload:
            apply_status(topic, clean_status(payload.get("status"), topic.status))
        topic.updated_at = datetime.utcnow()
        session.add(topic)
        session.commit()
        session.refresh(topic)
        return payloads.topic_summary(session, topic)


@app.delete("/api/topics/{topic_id}")
def delete_topic(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        result = topic_ops.remove_topic(session, topic_id, dry_run=False)
        if not result.get("found"):
            raise HTTPException(status_code=404, detail="Topic not found")
        return result


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


@app.get("/api/topics/{topic_id}/evidence-package")
def topic_evidence_package(topic_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        return evidence_package.build_evidence_package(session, topic)


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
            errors=latest_sentiment_errors(session, topic),
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
    refresh_voices = payload.refresh_voices if payload else False
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


@app.get("/api/discovery/reports")
def list_discovery_reports() -> list[dict[str, Any]]:
    from app.discovery import run as discovery_run

    return discovery_run.list_reports()


@app.get("/api/discovery/reports/{run_id}")
def get_discovery_report(run_id: str) -> dict[str, Any]:
    from app.discovery import run as discovery_run

    report = discovery_run.report_by_run_id(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Discovery report not found")
    return report


@app.get("/api/discovery/timeline-tree")
def get_discovery_timeline_tree() -> dict[str, Any]:
    from app.discovery import run as discovery_run

    return discovery_run.timeline_tree()


@app.get("/api/auto-refresh/status")
def get_auto_refresh_status() -> dict[str, Any]:
    """自动刷新状态(供前端显示"上次自动更新 X 前"、开关状态)。"""
    return auto_refresh.status_snapshot()


@app.post("/api/auto-refresh/run")
def trigger_auto_refresh() -> dict[str, Any]:
    """手动立即触发一轮自动刷新(自动之外的兜底按钮)。同步跑一轮并返回统计。"""
    return auto_refresh.refresh_once()


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
        previous_label = mark.label if mark else ""
        previous_domain = mark.domain if mark else ""
        is_new_mark = mark is None
        if not mark:
            mark = CognitionMark(
                target_type=payload.target_type,
                target_id=payload.target_id,
                target_key=payload.target_key,
                topic_id=payload.topic_id,
            )
        mark.domain = payload.domain.strip().lower()
        mark.label = payload.label
        mark.note = payload.note.strip()
        mark.updated_at = datetime.utcnow()
        session.add(mark)
        if is_new_mark or mark.label != previous_label or mark.domain != previous_domain:
            apply_cognition_mark_calibration(session, mark)
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
            item.depth = str(row.get("depth", item.depth)).strip() or item.depth
            item.interest = str(row.get("interest", item.interest)).strip() or item.interest
            item.confidence = clamp_int(row.get("confidence", item.confidence), 0, 100, item.confidence)
            item.evidence = str(row.get("evidence", item.evidence)).strip()
            item.recommended_seed_style = (
                str(row.get("recommended_seed_style", item.recommended_seed_style)).strip()
                or item.recommended_seed_style
            )
            item.updated_at = datetime.utcnow()
            session.add(item)
        session.commit()
        return [cognition_profile_payload(item) for item in ensure_cognition_profile(session)]


@app.get("/api/search/jobs/{job_id}")
def get_search_job(job_id: str) -> dict[str, Any]:
    return search_service.job_snapshot(job_id)


def ensure_topic_projects(session: Session) -> None:
    topics = session.exec(select(Topic)).all()
    changed = False
    for topic in topics:
        if topic.project_id:
            continue
        project = Project(
            name=topic.name,
            description=topic.description,
            status=topic.status or "active",
            archived_at=topic.archived_at,
            created_at=topic.created_at,
            updated_at=topic.updated_at or datetime.utcnow(),
        )
        session.add(project)
        session.flush()
        topic.project_id = project.id
        topic.updated_at = datetime.utcnow()
        session.add(topic)
        changed = True
    if changed:
        session.commit()


def project_for_topic_payload(session: Session, payload: dict[str, Any], topic_name: str) -> Project:
    project_id = payload.get("project_id")
    if project_id:
        project = session.get(Project, int(project_id))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    project = Project(
        name=topic_name,
        description=clean_text(payload.get("description")),
        status="active",
    )
    session.add(project)
    session.flush()
    return project


def clean_required_text(value: Any, message: str) -> str:
    text = clean_text(value)
    if not text:
        raise HTTPException(status_code=422, detail=message)
    return text


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def clean_queries(value: Any, fallback: str) -> list[str]:
    if not isinstance(value, list):
        return [fallback]
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return list(dict.fromkeys(cleaned)) or [fallback]


def clean_status(value: Any, fallback: str) -> str:
    status = str(value or fallback).strip() or fallback
    if status not in {"active", "archived"}:
        raise HTTPException(status_code=422, detail="status must be active or archived")
    return status


def apply_status(item: Any, status: str) -> None:
    previous = getattr(item, "status", "active")
    item.status = status
    if status == "archived" and previous != "archived":
        item.archived_at = datetime.utcnow()
    if status == "active":
        item.archived_at = None


def cognition_mark_payload(mark: CognitionMark) -> dict[str, Any]:
    return {
        "id": mark.id,
        "target_type": mark.target_type,
        "target_id": mark.target_id,
        "target_key": mark.target_key,
        "topic_id": mark.topic_id,
        "domain": mark.domain,
        "label": mark.label,
        "note": mark.note,
        "updated_at": payloads.iso(mark.updated_at),
    }


def ensure_cognition_profile(session: Session) -> list[CognitionProfile]:
    rows = session.exec(select(CognitionProfile).order_by(CognitionProfile.id)).all()
    if rows:
        defaults = {row["domain_key"]: row for row in DEFAULT_COGNITION_PROFILE}
        changed = False
        existing_keys = {item.domain_key for item in rows}
        for item in rows:
            default = defaults.get(item.domain_key, {})
            changed = apply_cognition_profile_defaults(item, default) or changed
            session.add(item)
        for default in DEFAULT_COGNITION_PROFILE:
            if default["domain_key"] not in existing_keys:
                session.add(CognitionProfile(**default))
                changed = True
        if changed:
            session.commit()
            rows = session.exec(select(CognitionProfile).order_by(CognitionProfile.id)).all()
        return rows
    for item in DEFAULT_COGNITION_PROFILE:
        session.add(CognitionProfile(**item))
    session.commit()
    return session.exec(select(CognitionProfile).order_by(CognitionProfile.id)).all()


def cognition_profile_payload(item: CognitionProfile) -> dict[str, Any]:
    return {
        "id": item.id,
        "domain_key": item.domain_key,
        "domain_label": item.domain_label,
        "level": item.level,
        "note": item.note,
        "depth": item.depth,
        "interest": item.interest,
        "confidence": item.confidence,
        "evidence": item.evidence,
        "recommended_seed_style": item.recommended_seed_style,
        "updated_at": payloads.iso(item.updated_at),
    }


def apply_cognition_profile_defaults(item: CognitionProfile, default: dict[str, Any]) -> bool:
    changed = False
    for key, fallback, generic_default in (
        ("depth", "none", "none"),
        ("interest", "medium", "medium"),
        ("evidence", "", ""),
        ("recommended_seed_style", "mechanism", "mechanism"),
    ):
        value = getattr(item, key, "")
        if not value or (default and value == generic_default and default.get(key) != generic_default):
            setattr(item, key, default.get(key, fallback))
            changed = True
    if item.confidence is None or (default and item.confidence == 50 and default.get("confidence") != 50):
        item.confidence = int(default.get("confidence", 50))
        changed = True
    return changed


def apply_cognition_mark_calibration(session: Session, mark: CognitionMark) -> None:
    if mark.target_type != "seed":
        return
    domain = (mark.domain or "").strip()
    domain_key = SEED_DOMAIN_PROFILE_MAP.get(domain)
    if not domain_key:
        return
    delta = COGNITION_MARK_DELTAS.get(mark.label)
    if delta is None:
        return
    profile = session.exec(select(CognitionProfile).where(CognitionProfile.domain_key == domain_key)).first()
    if not profile:
        ensure_cognition_profile(session)
        profile = session.exec(select(CognitionProfile).where(CognitionProfile.domain_key == domain_key)).first()
    if not profile:
        return
    before = clamp_int(profile.confidence, 0, 100, 50)
    after = max(0, min(100, before + delta))
    if after != before:
        profile.confidence = after
    label_text = {
        "known": "已懂",
        "doubtful": "存疑",
        "unfamiliar": "陌生",
    }.get(mark.label, mark.label)
    lesson = f"{datetime.utcnow().date().isoformat()} 标 {domain} 种子{label_text} confidence {before}→{after}"
    profile.evidence = append_profile_evidence(profile.evidence, lesson)
    profile.updated_at = datetime.utcnow()
    session.add(profile)


def append_profile_evidence(existing: str, lesson: str) -> str:
    existing = (existing or "").strip()
    if not existing:
        return lesson
    if lesson in existing:
        return existing
    return f"{existing}\n{lesson}"


def clamp_int(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, parsed))


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


def latest_sentiment_errors(session: Session, topic: Topic) -> list[dict[str, str]]:
    """从最近一次民间情绪 job 取平台失败信息, 让"某平台不可用"在重载后仍可见,
    而不是静默变成"没声音"(用户困惑: 开了 Chrome 仍看不到小红书/雪球)。"""
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
        errors = result.get("errors")
        if isinstance(errors, list):
            return errors
    return []
