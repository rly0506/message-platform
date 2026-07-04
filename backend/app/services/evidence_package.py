from __future__ import annotations

from collections import Counter
from typing import Any

from sqlmodel import Session, select

from app.db import Article, SourceRegistry, Topic, TopicArticle
from app.pipeline import local_analyze, narrative_signals
from app.services import payloads


def build_evidence_package(session: Session, topic: Topic) -> dict[str, Any]:
    rows = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic.id)
        .where(TopicArticle.relevant == True)  # noqa: E712
    ).all()
    sources = source_lookup(session)
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
        if article.id is not None
    ]
    analysis = local_analyze.analyze_topic(topic.name, article_rows)
    articles = [
        article_evidence_payload(topic_article, article, sources)
        for topic_article, article in rows
        if article.id is not None
    ]
    articles.sort(key=lambda item: item.get("published_at") or "", reverse=True)
    evidence_lookup = {item["id"]: item for item in articles}
    events = payloads.attach_event_evidence(analysis["events"], evidence_lookup)

    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "article_count": len(articles),
        "source_count": len({item["source"] for item in articles if item.get("source")}),
        "source_types": counted_summary(item["source_type"] for item in articles),
        "quality_tiers": counted_summary(item["quality_tier"] for item in articles),
        "sources": source_summary(articles),
        "articles": articles,
        "events": events,
        "framing": analysis["framing"],
        "stance_evolution": analysis["stance_evolution"],
        "keywords": analysis["keywords"],
        "entities": analysis["entities"],
        "entity_groups": analysis["entity_groups"],
        "criteria": analysis["criteria"],
        "narrative_signals": narrative_signals.detect_narrative_signals(article_rows),
    }


def source_lookup(session: Session) -> dict[str, SourceRegistry]:
    rows = session.exec(select(SourceRegistry)).all()
    return {source.name.lower(): source for source in rows if source.name}


def article_evidence_payload(
    topic_article: TopicArticle,
    article: Article,
    sources: dict[str, SourceRegistry],
) -> dict[str, Any]:
    registry_source = sources.get((article.source or "").lower())
    source_type = registry_source.source_type if registry_source else (article.collector or "unknown")
    quality_tier = registry_source.quality_tier if registry_source else local_analyze._source_tier(article.source)
    title = article.title_zh or article.title
    snippet = payloads.clean_snippet(article.snippet_zh or article.snippet)
    category = local_analyze.infer_report_category(title, snippet)
    return {
        "id": article.id,
        "url": article.url,
        "title": title,
        "source": article.source,
        "source_country": article.source_country,
        "source_lang": article.source_lang,
        "source_type": source_type or "unknown",
        "quality_tier": quality_tier or "other",
        "collector": article.collector,
        "published_at": payloads.iso(article.published_at),
        "snippet": snippet,
        "relevance": topic_article.relevance,
        "stance": topic_article.stance,
        "category": category,
        "category_reason": local_analyze.report_category_reason(category, title, snippet),
        "requires_login": bool(registry_source.requires_login) if registry_source else False,
        "fulltext_support": bool(registry_source.fulltext_support) if registry_source else False,
    }


def counted_summary(values: Any) -> list[dict[str, Any]]:
    counts = Counter(value or "unknown" for value in values)
    return [{"key": key, "count": count} for key, count in counts.most_common()]


def source_summary(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        grouped.setdefault(article.get("source") or "unknown", []).append(article)
    return [
        {
            "name": name,
            "article_count": len(items),
            "source_type": items[0]["source_type"],
            "quality_tier": items[0]["quality_tier"],
            "country": items[0]["source_country"],
        }
        for name, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
