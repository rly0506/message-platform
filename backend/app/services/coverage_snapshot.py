from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from sqlmodel import Session, select

from app.db import Article, Event, SourceRegistry, Topic, TopicArticle


SAMPLE_NOTE = (
    'Counts describe persisted articles collected for this scope; '
    'absence is not proof that a source did not report.'
)


class TopicNotFoundError(LookupError):
    pass


class EventNotFoundError(LookupError):
    pass


def build_coverage_snapshot(
    session: Session,
    topic_id: int,
    event_id: int | None = None,
) -> dict[str, Any]:
    topic = session.get(Topic, topic_id)
    if not topic:
        raise TopicNotFoundError(topic_id)

    rows = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic_id)
    ).all()
    articles = [article for _, article in rows if article.id is not None]
    basis = 'persisted_topic_articles'

    if event_id is not None:
        event = session.get(Event, event_id)
        if not event or event.topic_id != topic_id:
            raise EventNotFoundError(event_id)
        evidence_ids = _integer_ids(event.article_ids)
        articles = [article for article in articles if article.id in evidence_ids]
        basis = 'persisted_event_articles'

    articles.sort(key=lambda article: article.id or 0)
    return _snapshot_payload(session, topic_id, event_id, basis, articles)


def _snapshot_payload(
    session: Session,
    topic_id: int,
    event_id: int | None,
    basis: str,
    articles: list[Article],
) -> dict[str, Any]:
    article_ids = [article.id for article in articles if article.id is not None]
    source_names = {
        _normalize(article.source)
        for article in articles
        if _normalize(article.source)
    }
    registry = _registry_payload(session, articles)
    return {
        'topic_id': topic_id,
        'event_id': event_id,
        'sample': {
            'basis': basis,
            'article_count': len(article_ids),
            'article_ids': article_ids,
            'note': SAMPLE_NOTE,
        },
        'independent_source_count': len(source_names),
        'source_distribution': _buckets(articles, lambda item: item.source),
        'collector_distribution': _buckets(articles, lambda item: item.collector),
        'language_distribution': _buckets(articles, lambda item: item.source_lang),
        'country_distribution': _buckets(articles, lambda item: item.source_country),
        'url_decoding': _decoding_payload(articles),
        'source_registry': registry,
        'fulltext': {
            'status': 'unknown',
            'reason': 'article_bodies_not_persisted',
        },
    }


def _buckets(
    articles: list[Article],
    value: Callable[[Article], str],
) -> list[dict[str, Any]]:
    evidence: dict[str, list[int]] = defaultdict(list)
    for article in articles:
        if article.id is None:
            continue
        key = _display_value(value(article))
        evidence[key].append(article.id)
    return _bucket_payload(evidence)


def _bucket_payload(evidence: dict[str, list[int]]) -> list[dict[str, Any]]:
    buckets = [
        {'key': key, 'count': len(ids), 'article_ids': sorted(ids)}
        for key, ids in evidence.items()
    ]
    return sorted(buckets, key=lambda item: (-item['count'], item['key']))


def _registry_payload(session: Session, articles: list[Article]) -> dict[str, Any]:
    registry_rows = session.exec(select(SourceRegistry)).all()
    lookup = {
        _normalize(row.name): row
        for row in registry_rows
        if _normalize(row.name)
    }
    type_evidence: dict[str, list[int]] = defaultdict(list)
    tier_evidence: dict[str, list[int]] = defaultdict(list)
    unclassified: list[int] = []

    for article in articles:
        if article.id is None:
            continue
        registry = lookup.get(_normalize(article.source))
        if not registry:
            unclassified.append(article.id)
            continue
        type_evidence[_display_value(registry.source_type)].append(article.id)
        tier_evidence[_display_value(registry.quality_tier)].append(article.id)

    return {
        'type_distribution': _bucket_payload(type_evidence),
        'tier_distribution': _bucket_payload(tier_evidence),
        'unclassified_article_ids': sorted(unclassified),
    }


def _decoding_payload(articles: list[Article]) -> dict[str, Any]:
    eligible = [
        article
        for article in articles
        if _normalize(article.collector) == 'gnews' and article.id is not None
    ]
    decoded_ids = sorted(article.id for article in eligible if article.url_decoded)
    not_decoded_ids = sorted(article.id for article in eligible if not article.url_decoded)
    return {
        'eligible_count': len(eligible),
        'decoded_count': len(decoded_ids),
        'rate': len(decoded_ids) / len(eligible) if eligible else None,
        'decoded_article_ids': decoded_ids,
        'not_decoded_article_ids': not_decoded_ids,
    }


def _integer_ids(values: list[Any]) -> set[int]:
    ids: set[int] = set()
    for value in values or []:
        try:
            ids.add(int(value))
        except (TypeError, ValueError):
            continue
    return ids


def _normalize(value: Any) -> str:
    return ' '.join(str(value or '').split()).casefold()


def _display_value(value: Any) -> str:
    cleaned = ' '.join(str(value or '').split())
    return cleaned if cleaned else 'unknown'
