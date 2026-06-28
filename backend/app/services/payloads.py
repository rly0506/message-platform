"""Payload serializers shared by API routes and background services."""
from __future__ import annotations

import re
from datetime import datetime
from html import unescape
from typing import Any

from sqlmodel import Session, select

from app.db import (
    Analysis,
    Article,
    SourceFraming,
    TimelineEvent,
    Topic,
    TopicArticle,
)
from app.pipeline import local_analyze


def topic_summary(session: Session, topic: Topic) -> dict[str, Any]:
    links = session.exec(
        select(TopicArticle).where(TopicArticle.topic_id == topic.id)
    ).all()
    article_ids = [link.article_id for link in links]
    articles = (
        session.exec(select(Article).where(Article.id.in_(article_ids))).all()
        if article_ids
        else []
    )
    latest = max((article.published_at for article in articles if article.published_at), default=None)
    source_count = len({article.source for article in articles if article.source})
    enriched_count = sum(1 for article in articles if article.enriched)
    relevant_count = sum(1 for link in links if link.relevant)

    return {
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "queries": topic.queries,
        "status": topic.status,
        "created_at": iso(topic.created_at),
        "article_count": len(links),
        "source_count": source_count,
        "enriched_count": enriched_count,
        "relevant_count": relevant_count,
        "latest_published_at": iso(latest),
    }


def article_payload(topic_article: TopicArticle, article: Article) -> dict[str, Any]:
    title = article.title_zh or article.title
    snippet = article.snippet_zh or article.snippet
    category = local_analyze.infer_report_category(title, snippet)
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "title_zh": article.title_zh,
        "source": article.source,
        "source_lang": article.source_lang,
        "source_country": article.source_country,
        "published_at": iso(article.published_at),
        "snippet": article.snippet,
        "snippet_zh": article.snippet_zh,
        "collector": article.collector,
        "enriched": article.enriched,
        "relevance": topic_article.relevance,
        "relevant": topic_article.relevant,
        "stance": topic_article.stance,
        "stance_summary": topic_article.stance_summary,
        "category": category,
        "category_reason": local_analyze.report_category_reason(category, title, snippet),
    }


def topic_evidence_lookup(session: Session, topic_id: int) -> dict[int, dict[str, Any]]:
    rows = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic_id)
    ).all()
    return article_evidence_lookup(rows)


def article_evidence_lookup(rows: list[tuple[TopicArticle, Article]]) -> dict[int, dict[str, Any]]:
    out = {}
    for topic_article, article in rows:
        if article.id is None:
            continue
        title = article.title_zh or article.title
        snippet = clean_snippet(article.snippet_zh or article.snippet)
        category = local_analyze.infer_report_category(title, snippet)
        out[article.id] = {
            "id": article.id,
            "url": article.url,
            "title": title,
            "source": article.source,
            "published_at": iso(article.published_at),
            "snippet": snippet,
            "collector": article.collector,
            "relevance": topic_article.relevance,
            "stance": topic_article.stance,
            "category": category,
            "category_reason": local_analyze.report_category_reason(category, title, snippet),
        }
    return out


def attach_event_evidence(
    events: list[dict[str, Any]],
    evidence_lookup: dict[int, dict[str, Any]],
    limit: int = 8,
) -> list[dict[str, Any]]:
    for event in events:
        event["evidence_articles"] = [
            evidence_lookup[article_id]
            for article_id in event.get("article_ids", [])[:limit]
            if article_id in evidence_lookup
        ]
    return events


def clean_snippet(value: str) -> str:
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def timeline_event(row: TimelineEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": iso(row.date),
        "title_zh": row.title_zh,
        "summary_zh": row.summary_zh,
        "article_ids": row.article_ids,
    }


def source_framing(row: SourceFraming) -> dict[str, Any]:
    return {
        "id": row.id,
        "party": row.party,
        "stance": row.stance,
        "summary_zh": row.summary_zh,
        "article_ids": row.article_ids,
    }


def analysis_payload(row: Analysis) -> dict[str, Any]:
    return {
        "id": row.id,
        "generated_at": iso(row.generated_at),
        "content_md": row.content_md,
    }


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
