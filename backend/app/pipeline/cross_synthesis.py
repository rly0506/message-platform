"""Cross-voice synthesis: media, academic, and public sentiment."""
from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app import config, llm
from app.db import CrossSynthesis, SearchJob, SentimentPost, SourceFraming, TimelineEvent, Topic


MISSING_NOTE = "该声部暂无数据"


def run_cross_synthesis(
    session: Session,
    topic: Topic,
    *,
    on_step: Any | None = None,
) -> dict[str, Any]:
    if on_step:
        on_step("gather", "running")
    voices = gather_voices(session, topic)
    if on_step:
        on_step("gather", "done", {"voices_used": voices.get("available_voices", [])})

    if on_step:
        on_step("synthesize", "running")
    content_md = cross_synthesize(topic, voices)
    if on_step:
        on_step("synthesize", "done")

    if on_step:
        on_step("persist", "running")
    row = persist_cross_synthesis(
        session,
        topic_id=topic.id,
        content_md=content_md,
        voices_used=voices.get("available_voices", []),
    )
    if on_step:
        on_step("persist", "done")

    return cross_synthesis_payload(topic, row)


def gather_voices(session: Session, topic: Topic) -> dict[str, Any]:
    media = gather_media_voice(session, topic)
    academic = gather_job_summary(session, topic, kind="academic_analysis", query_prefix="academic")
    sentiment = gather_sentiment_voice(session, topic)
    voices = {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "media": media,
        "academic": academic,
        "sentiment": sentiment,
    }
    voices["available_voices"] = [
        key for key in ("media", "academic", "sentiment") if voices[key].get("available")
    ]
    return voices


def cross_synthesize(topic: Topic, voices: dict[str, Any]) -> str:
    available = voices.get("available_voices") or []
    prompt = f"""请为专题「{topic.name}」生成“三方对照”综合。

可用声部: {", ".join(available) if available else "无"}。
如果不是三方齐全，请明确说明：仅基于现有 {len(available)} 方，缺失声部不能被当成沉默或同意。

必须按以下五块输出中文 markdown，标题名称保持一致:
1. 三方共识：媒体、学界、民间都支持或至少相互印证的判断。
2. 三方矛盾：媒体说 A、学界说 B、民间说 C 的冲突点；如果只有两方，写“两方矛盾”但仍放在本节。
3. 各自盲区：分别说明媒体、学界、民间各看漏了什么。
4. 机制重建：按“事情怎么一步步发生的”梳理机制链条。必须明确写入“分析机制与因果，不做道德归责”，不要把本节写成追责。
5. 批判提示：列出信息缺口、证据弱点、各声部偏见。尤其提醒：民间情绪是非事实源，高赞不等于事实，只能作为待核实线索。

缺失声部说明:
- 媒体：{voices.get("media", {}).get("note") or "有数据"}
- 学界：{voices.get("academic", {}).get("note") or "有数据"}
- 民间：{voices.get("sentiment", {}).get("note") or "有数据"}

媒体声部:
{voices.get("media")}

学界声部:
{voices.get("academic")}

民间声部:
{voices.get("sentiment")}
"""
    return llm.chat(
        config.SYNTH_MODEL,
        prompt,
        max_tokens=1800,
        system="你是严谨的跨声部分析助手，只基于给定声部做对照，不引入外部事实。",
    )


def persist_cross_synthesis(
    session: Session,
    *,
    topic_id: int,
    content_md: str,
    voices_used: list[str],
) -> CrossSynthesis:
    row = CrossSynthesis(
        topic_id=topic_id,
        content_md=content_md,
        voices_used=voices_used,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def cross_synthesis_payload_from_db(session: Session, topic: Topic) -> dict[str, Any]:
    row = session.exec(
        select(CrossSynthesis)
        .where(CrossSynthesis.topic_id == topic.id)
        .order_by(CrossSynthesis.generated_at.desc(), CrossSynthesis.id.desc())
    ).first()
    if not row:
        return {
            "topic_id": topic.id,
            "topic_name": topic.name,
            "content_md": "",
            "voices_used": [],
            "generated_at": None,
        }
    return cross_synthesis_payload(topic, row)


def cross_synthesis_payload(topic: Topic, row: CrossSynthesis) -> dict[str, Any]:
    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "content_md": row.content_md,
        "voices_used": row.voices_used,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }


def gather_media_voice(session: Session, topic: Topic) -> dict[str, Any]:
    timeline = session.exec(
        select(TimelineEvent)
        .where(TimelineEvent.topic_id == topic.id)
        .order_by(TimelineEvent.date)
    ).all()
    framing = session.exec(
        select(SourceFraming).where(SourceFraming.topic_id == topic.id)
    ).all()
    available = bool(timeline or framing)
    return {
        "available": available,
        "note": "" if available else MISSING_NOTE,
        "timeline": [
            {
                "date": item.date.isoformat() if item.date else None,
                "title_zh": item.title_zh,
                "summary_zh": item.summary_zh,
                "article_ids": item.article_ids,
            }
            for item in timeline
        ],
        "framing": [
            {
                "party": item.party,
                "stance": item.stance,
                "summary_zh": item.summary_zh,
                "article_ids": item.article_ids,
            }
            for item in framing
        ],
    }


def gather_sentiment_voice(session: Session, topic: Topic) -> dict[str, Any]:
    summary = gather_job_summary(session, topic, kind="sentiment_analysis", query_prefix="sentiment")
    posts = session.exec(
        select(SentimentPost)
        .where(SentimentPost.topic_id == topic.id)
        .order_by(SentimentPost.score.desc(), SentimentPost.num_comments.desc())
    ).all()
    top_posts = [
        {
            "platform": post.platform,
            "subreddit": post.subreddit,
            "title": post.title,
            "author": post.author,
            "score": post.score,
            "num_comments": post.num_comments,
            "url": post.url,
            "created_utc": post.created_utc,
            "selftext_snippet": post.selftext_snippet,
        }
        for post in posts[:8]
    ]
    available = bool(summary.get("summary_md") or top_posts)
    return {
        "available": available,
        "note": "" if available else MISSING_NOTE,
        "summary_md": summary.get("summary_md", ""),
        "top_posts": top_posts,
    }


def gather_job_summary(session: Session, topic: Topic, *, kind: str, query_prefix: str) -> dict[str, Any]:
    jobs = session.exec(
        select(SearchJob)
        .where(SearchJob.status == "done")
        .order_by(SearchJob.updated_at.desc(), SearchJob.created_at.desc())
    ).all()
    for job in jobs:
        payload = job.payload or {}
        if payload.get("kind") != kind:
            continue
        if _safe_int(payload.get("topic_id")) != topic.id:
            continue
        result = job.result or {}
        summary = result.get("summary_md")
        if isinstance(summary, str) and summary.strip():
            return {"available": True, "note": "", "summary_md": summary}
    return {"available": False, "note": MISSING_NOTE, "summary_md": ""}


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
