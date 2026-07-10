"""Event-level multi-source contrast payloads.

This module is intentionally read-only and rule-based: it compares the
articles already anchored to a local evidence Event, without LLM inference or
new collection.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import unicodedata

from sqlmodel import Session, select

from app.db import Article, Event, Topic, TopicArticle
from app.pipeline import local_analyze
from app.services import payloads

CONTRAST_NOTE = "覆盖差异仅基于当前样本文章；未观察不等于不存在，也不表示蓄意遗漏。"
ENTITY_LIMIT = 10
KEYWORD_LIMIT = 10
COVERAGE_GAP_LIMIT = 30


class EventNotFoundInTopic(LookupError):
    """Raised when the requested event is not anchored to the topic."""


@dataclass(frozen=True)
class SourceBundle:
    source: str
    rows: list[tuple[TopicArticle, Article]]


def event_contrast_payload(session: Session, topic: Topic, event_id: int) -> dict[str, Any]:
    event = session.get(Event, event_id)
    if not event or event.topic_id != topic.id:
        raise EventNotFoundInTopic("Event not found in topic")

    rows = _event_article_rows(session, topic.id, event.article_ids or [])
    bundles = _source_bundles(rows)
    sources = [_source_payload(bundle) for bundle in bundles]

    if not rows:
        return {
            "event": _event_payload(event, source_count=0, article_count=0),
            "sources": [],
            "coverage_gaps": [],
            "degraded": True,
            "note": "该事件没有可用文章样本，无法生成多源对照。",
        }

    if len(sources) < 2:
        return {
            "event": _event_payload(event, source_count=len(sources), article_count=len(rows)),
            "sources": sources,
            "coverage_gaps": [],
            "degraded": True,
            "note": f"至少需要 2 个来源才能生成覆盖差异；当前仅 {len(sources)} 个来源。{CONTRAST_NOTE}",
        }

    return {
        "event": _event_payload(event, source_count=len(sources), article_count=len(rows)),
        "sources": sources,
        "coverage_gaps": _coverage_gaps(sources),
        "degraded": False,
        "note": CONTRAST_NOTE,
    }


def _event_article_rows(
    session: Session,
    topic_id: int,
    article_ids: list[Any],
) -> list[tuple[TopicArticle, Article]]:
    ids = _int_ids(article_ids)
    if not ids:
        return []
    id_order = {article_id: index for index, article_id in enumerate(ids)}
    rows = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic_id)
        .where(Article.id.in_(ids))
    ).all()
    return sorted(rows, key=lambda pair: id_order.get(pair[1].id or 0, len(id_order)))


def _source_bundles(rows: list[tuple[TopicArticle, Article]]) -> list[SourceBundle]:
    grouped: dict[str, list[tuple[TopicArticle, Article]]] = defaultdict(list)
    for topic_article, article in rows:
        grouped[article.source or "未知来源"].append((topic_article, article))
    bundles = [SourceBundle(source=source, rows=_sort_rows(items)) for source, items in grouped.items()]
    return sorted(
        bundles,
        key=lambda bundle: (
            _tier_rank(local_analyze._source_tier(bundle.source)),
            -len(bundle.rows),
            _first_published_at(bundle.rows) or datetime.max,
            bundle.source,
        ),
    )


def _source_payload(bundle: SourceBundle) -> dict[str, Any]:
    rows = bundle.rows
    source = bundle.source
    article_rows = [_article_row(topic_article, article) for topic_article, article in rows]
    representative = _representative_article(rows)
    tier = local_analyze._source_tier(source)
    substance_score, substance_note = _score_and_note(rows, "substance_score", "substance_note")
    emotion_score, emotion_note = _score_and_note(rows, "emotion_score", "emotion_note")
    stance = _dominant_stance(article_rows)

    return {
        "source": source,
        "tier": tier,
        "tier_label": local_analyze.MEDIA_TIER_LABELS.get(tier, "其他来源"),
        "article_count": len(rows),
        "stance": stance,
        "stance_summary": _stance_summary(rows, stance),
        "substance_score": substance_score,
        "substance_note": substance_note,
        "emotion_score": emotion_score,
        "emotion_note": emotion_note,
        "emphasized_entities": _emphasized_entities(source, rows),
        "emphasized_keywords": _emphasized_keywords(article_rows),
        "representative_title": _article_title(representative),
        "url": representative.url,
        "article_ids": [article.id for _, article in rows if article.id is not None],
        "articles": [_article_brief(article) for _, article in rows],
    }


def _coverage_gaps(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_sources = [source["source"] for source in sources]
    entries: list[dict[str, Any]] = []
    for kind, field in (("entity", "emphasized_entities"), ("keyword", "emphasized_keywords")):
        term_map: dict[str, dict[str, Any]] = {}
        for source in sources:
            for item in source.get(field, []) or []:
                normalized = _normalize_term(item.get("term", ""))
                if not normalized:
                    continue
                entry = term_map.setdefault(
                    normalized,
                    {
                        "term": item.get("term", ""),
                        "kind": kind,
                        "covered_by": set(),
                        "evidence_article_ids": set(),
                        "salience": 0,
                    },
                )
                entry["covered_by"].add(source["source"])
                entry["evidence_article_ids"].update(item.get("evidence_article_ids", []))
                entry["salience"] = max(entry["salience"], int(item.get("count") or 0))

        for entry in term_map.values():
            covered_by = sorted(entry["covered_by"], key=all_sources.index)
            not_observed = [source for source in all_sources if source not in entry["covered_by"]]
            if not covered_by or not not_observed or not entry["evidence_article_ids"]:
                continue
            entries.append({
                "term": entry["term"],
                "kind": entry["kind"],
                "covered_by": covered_by,
                "not_observed_in": not_observed,
                "evidence_article_ids": sorted(entry["evidence_article_ids"]),
                "salience": entry["salience"],
            })

    return sorted(entries, key=_gap_sort_key)[:COVERAGE_GAP_LIMIT]


def _event_payload(event: Event, source_count: int, article_count: int) -> dict[str, Any]:
    return {
        "id": event.id,
        "date": event.date.date().isoformat() if event.date else None,
        "title_zh": event.title_zh,
        "summary_zh": event.summary_zh,
        "source_count": source_count,
        "article_count": article_count,
    }


def _emphasized_entities(source: str, rows: list[tuple[TopicArticle, Article]]) -> list[dict[str, Any]]:
    text = " ".join(f"{_article_title(article)} {_article_snippet(article)}" for _, article in rows)
    entities = local_analyze._entities_for_text(text, limit=ENTITY_LIMIT, source_names=[source], use_spacy=False)
    evidence_by_term = _entity_evidence_by_term(source, rows)
    return [
        {
            "term": str(item.get("term", "")),
            "count": int(item.get("count") or 0),
            "evidence_article_ids": evidence_by_term.get(_normalize_term(item.get("term", "")), []),
        }
        for item in entities
        if item.get("term") and int(item.get("count") or 0) > 0
    ]


def _emphasized_keywords(rows: list[local_analyze.ArticleRow]) -> list[dict[str, Any]]:
    keywords = local_analyze._keywords_for_rows(rows, limit=KEYWORD_LIMIT)
    evidence_by_term = _keyword_evidence_by_term(rows)
    return [
        {
            "term": str(item.get("term", "")),
            "count": int(item.get("count") or 0),
            "evidence_article_ids": evidence_by_term.get(_normalize_term(item.get("term", "")), []),
        }
        for item in keywords
        if item.get("term") and int(item.get("count") or 0) > 0
    ]


def _entity_evidence_by_term(
    source: str,
    rows: list[tuple[TopicArticle, Article]],
) -> dict[str, list[int]]:
    evidence: dict[str, set[int]] = defaultdict(set)
    for _, article in rows:
        if article.id is None:
            continue
        text = f"{_article_title(article)} {_article_snippet(article)}"
        entities = local_analyze._entities_for_text(
            text,
            limit=max(ENTITY_LIMIT, len(text)),
            source_names=[source],
            use_spacy=False,
        )
        for item in entities:
            normalized = _normalize_term(item.get("term", ""))
            if normalized:
                evidence[normalized].add(article.id)
    return {term: sorted(article_ids) for term, article_ids in evidence.items()}


def _keyword_evidence_by_term(rows: list[local_analyze.ArticleRow]) -> dict[str, list[int]]:
    evidence: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        for term in local_analyze._signature(f"{row.title} {row.snippet}"):
            normalized = _normalize_term(term)
            if normalized:
                evidence[normalized].add(row.id)
    return {term: sorted(article_ids) for term, article_ids in evidence.items()}


def _score_and_note(rows: list[tuple[TopicArticle, Article]], score_attr: str, note_attr: str) -> tuple[int, str]:
    scores = [int(getattr(topic_article, score_attr)) for topic_article, _ in rows if int(getattr(topic_article, score_attr)) >= 0]
    notes = [str(getattr(topic_article, note_attr) or "").strip() for topic_article, _ in rows]
    notes = [note for note in notes if note]
    if not scores:
        return -1, "未评分"
    return round(sum(scores) / len(scores)), notes[0] if notes else f"基于 {len(scores)} 篇已评分报道。"


def _dominant_stance(rows: list[local_analyze.ArticleRow]) -> str:
    stances = Counter(row.stance or local_analyze.infer_stance(row.title, row.snippet) for row in rows)
    return stances.most_common(1)[0][0] if stances else "中性观察"


def _stance_summary(rows: list[tuple[TopicArticle, Article]], stance: str) -> str:
    for topic_article, _ in rows:
        if topic_article.stance_summary.strip():
            return topic_article.stance_summary.strip()
    return f"主要立场：{stance}"


def _article_row(topic_article: TopicArticle, article: Article) -> local_analyze.ArticleRow:
    return local_analyze.ArticleRow(
        id=article.id or 0,
        title=_article_title(article),
        source=article.source,
        published_at=article.published_at,
        snippet=_article_snippet(article),
        relevance=topic_article.relevance,
        stance=topic_article.stance,
    )


def _representative_article(rows: list[tuple[TopicArticle, Article]]) -> Article:
    return _sort_rows(rows)[0][1]


def _sort_rows(rows: list[tuple[TopicArticle, Article]]) -> list[tuple[TopicArticle, Article]]:
    return sorted(rows, key=lambda pair: (pair[1].published_at or datetime.max, pair[1].id or 0))


def _first_published_at(rows: list[tuple[TopicArticle, Article]]) -> datetime | None:
    ordered = _sort_rows(rows)
    return ordered[0][1].published_at if ordered else None


def _article_brief(article: Article) -> dict[str, Any]:
    return {
        "id": article.id,
        "title": _article_title(article),
        "url": article.url,
        "published_at": payloads.iso(article.published_at),
    }


def _article_title(article: Article) -> str:
    return article.title_zh or article.title


def _article_snippet(article: Article) -> str:
    return article.snippet_zh or article.snippet


def _normalize_term(term: Any) -> str:
    value = unicodedata.normalize("NFKC", str(term or ""))
    return local_analyze._normalize_entity_token(value)


def _gap_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    kind_rank = 0 if item["kind"] == "entity" else 1
    return (-int(item.get("salience") or 0), kind_rank, -len(item.get("not_observed_in") or []), item["term"])


def _tier_rank(tier: str) -> int:
    labels = list(local_analyze.MEDIA_TIER_LABELS)
    return labels.index(tier) if tier in labels else 99


def _int_ids(values: list[Any]) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for value in values:
        try:
            item = int(value)
        except (TypeError, ValueError):
            continue
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
