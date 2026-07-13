"""Read-only, evidence-based analogues between events in different topics."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import unicodedata

from sqlmodel import Session, select

from app.db import Article, Event, Topic, TopicArticle
from app.pipeline import local_analyze, narrative_signals

ANALOGUE_NOTE = "类比不等于预测；请同时阅读差异提醒。"
ITEM_NOTE = "相似仅表示样本内结构信号重合，不代表同因、同果或会重演。"
CANDIDATE_SCAN_CAP = 500
RESULT_LIMIT = 8
KEYWORD_LIMIT = 12
NARRATIVE_LIMIT = 8


class EventNotFoundInTopic(LookupError):
    """Raised when a topic has events but not the requested event."""


@dataclass(frozen=True)
class EventFeatures:
    event: Event
    rows: list[local_analyze.ArticleRow]
    evidence_articles: list[dict[str, Any]]
    entities: dict[str, str]
    keywords: dict[str, dict[str, Any]]
    narratives: dict[str, str]
    source_tiers: set[str]
    tier_counts: Counter[str]
    article_ids: list[int]


@dataclass(frozen=True)
class EventArticle:
    row: local_analyze.ArticleRow
    article: Article


def event_analogues_payload(session: Session, topic: Topic, event_id: int) -> dict[str, Any]:
    all_events = session.exec(
        select(Event).order_by(Event.date.desc(), Event.updated_at.desc(), Event.id.desc())
    ).all()
    topic_events = [event for event in all_events if event.topic_id == topic.id]
    if not topic_events:
        return _degraded_payload(topic, event_id, len(all_events))

    target = next((event for event in topic_events if event.id == event_id), None)
    if not target:
        raise EventNotFoundInTopic("Event not found in topic")

    eligible = [event for event in all_events if event.topic_id != topic.id]
    truncated = len(eligible) > CANDIDATE_SCAN_CAP
    candidates = eligible[:CANDIDATE_SCAN_CAP]
    rows_by_event = _rows_by_event([target, *candidates], session)
    target_features = _features(target, rows_by_event.get(target.id or 0, []))
    topic_lookup = _topics_by_id(session, candidates)

    items = []
    for candidate in candidates:
        features = _features(candidate, rows_by_event.get(candidate.id or 0, []))
        score, basis = _similarity(target_features, features)
        label = _score_label(score)
        if not label:
            continue
        candidate_topic = topic_lookup.get(candidate.topic_id)
        items.append({
            "topic_id": candidate.topic_id,
            "topic_name": candidate_topic.name if candidate_topic else "未知话题",
            "event_id": candidate.id,
            "date": _date_label(candidate.date),
            "title_zh": candidate.title_zh or candidate.title,
            "similarity_score": score,
            "score_label": label,
            "basis": basis,
            "differences": _differences(target_features, features),
            "evidence_article_ids": features.article_ids,
            "evidence_articles": features.evidence_articles,
            "note": ITEM_NOTE,
        })

    items.sort(key=lambda item: (-item["similarity_score"], item["date"] or "", item["event_id"] or 0))
    return {
        "target": _target_payload(topic, target_features),
        "items": items[:RESULT_LIMIT],
        "scan": _scan_payload(len(all_events), len(eligible), len(candidates), truncated),
        "degraded": False,
        "degraded_reason": "",
        "note": ANALOGUE_NOTE,
    }


def _degraded_payload(topic: Topic, event_id: int, total_events: int) -> dict[str, Any]:
    reason = "该话题没有持久化事件；只读类比不会自动同步或创建事件。"
    return {
        "target": {"topic_id": topic.id, "event_id": event_id, "title_zh": "", "entities": [], "keywords": []},
        "items": [],
        "scan": _scan_payload(total_events, 0, 0, False),
        "degraded": True,
        "degraded_reason": reason,
        "note": ANALOGUE_NOTE,
    }


def _rows_by_event(events: list[Event], session: Session) -> dict[int, list[EventArticle]]:
    article_ids = _unique_ints([article_id for event in events for article_id in (event.article_ids or [])])
    if not article_ids:
        return {event.id: [] for event in events if event.id is not None}
    pairs = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(Article.id.in_(article_ids))
    ).all()
    pair_lookup = {(link.topic_id, article.id): (link, article) for link, article in pairs if article.id is not None}
    result: dict[int, list[EventArticle]] = {}
    for event in events:
        rows: list[EventArticle] = []
        for article_id in _unique_ints(event.article_ids or []):
            pair = pair_lookup.get((event.topic_id, article_id))
            if not pair:
                continue
            link, article = pair
            title = article.title_zh or article.title
            snippet = article.snippet_zh or article.snippet
            rows.append(EventArticle(
                row=local_analyze.ArticleRow(
                    id=article.id or 0,
                    title=title,
                    source=article.source,
                    published_at=article.published_at,
                    snippet=snippet,
                    relevance=link.relevance,
                    stance=link.stance or local_analyze.infer_stance(title, snippet),
                ),
                article=article,
            ))
        if event.id is not None:
            result[event.id] = rows
    return result


def _features(event: Event, event_articles: list[EventArticle]) -> EventFeatures:
    rows = [item.row for item in event_articles]
    entities = _named_terms(event.entities or [])
    keyword_items = local_analyze._keywords_for_rows(rows, limit=KEYWORD_LIMIT)
    keywords = {_normalize(item.get("term")): item for item in keyword_items if _normalize(item.get("term"))}
    signals = narrative_signals.detect_narrative_signals(rows, limit=NARRATIVE_LIMIT)
    narratives = {_normalize(item.get("claim")): str(item.get("claim") or "") for item in signals if _normalize(item.get("claim"))}
    source_names = _source_names(event, rows)
    tier_counts = Counter(local_analyze._source_tier(source) for source in source_names)
    article_ids = _unique_ints(event.article_ids or [])
    return EventFeatures(
        event=event,
        rows=rows,
        evidence_articles=[_evidence_article_payload(item.article) for item in event_articles],
        entities=entities,
        keywords=keywords,
        narratives=narratives,
        source_tiers=set(tier_counts),
        tier_counts=tier_counts,
        article_ids=article_ids,
    )


def _evidence_article_payload(article: Article) -> dict[str, Any]:
    return {
        "id": article.id,
        "title": article.title_zh or article.title or f"#{article.id}",
        "url": article.url,
        "source": article.source,
        "published_at": article.published_at.isoformat() if article.published_at else None,
    }


def _similarity(target: EventFeatures, candidate: EventFeatures) -> tuple[int, list[dict[str, Any]]]:
    basis: list[dict[str, Any]] = []
    shared_entities = sorted(set(target.entities) & set(candidate.entities))
    _add_basis(basis, "shared_entity", [target.entities[item] for item in shared_entities], min(40, len(shared_entities) * 20))

    shared_keywords = sorted(set(target.keywords) & set(candidate.keywords))
    _add_basis(basis, "shared_keyword", [target.keywords[item]["term"] for item in shared_keywords], min(24, len(shared_keywords) * 8))

    shared_narratives = sorted(set(target.narratives) & set(candidate.narratives))
    _add_basis(basis, "shared_narrative_signal", [target.narratives[item] for item in shared_narratives], min(16, len(shared_narratives) * 8))

    tier_union = target.source_tiers | candidate.source_tiers
    shared_tiers = sorted(target.source_tiers & candidate.source_tiers)
    tier_weight = round(10 * len(shared_tiers) / len(tier_union)) if tier_union else 0
    tier_labels = [local_analyze.MEDIA_TIER_LABELS.get(tier, tier) for tier in shared_tiers]
    _add_basis(basis, "shared_source_tier", tier_labels, tier_weight)

    shape_weight, shape_items = _shape_similarity(target.event, candidate.event)
    _add_basis(basis, "similar_sample_shape", shape_items, shape_weight)
    return min(100, sum(item["weight"] for item in basis)), basis


def _shape_similarity(target: Event, candidate: Event) -> tuple[int, list[str]]:
    article_weight = _ratio_weight(target.article_count, candidate.article_count, 4)
    source_weight = _ratio_weight(target.source_count, candidate.source_count, 3)
    days = _day_gap(target.date, candidate.date)
    time_weight = 3 if days is not None and days <= 30 else 2 if days is not None and days <= 180 else 1 if days is not None and days <= 365 else 0
    items = [f"文章数 {target.article_count} vs {candidate.article_count}", f"来源数 {target.source_count} vs {candidate.source_count}"]
    if days is not None:
        items.append(f"日期间隔 {days} 天")
    return article_weight + source_weight + time_weight, items


def _differences(target: EventFeatures, candidate: EventFeatures) -> list[str]:
    differences = [_date_difference(target.event.date, candidate.event.date)]
    candidate_only = [candidate.entities[item] for item in candidate.entities if item not in target.entities]
    target_only = [target.entities[item] for item in target.entities if item not in candidate.entities]
    if candidate_only:
        differences.append(f"对方 top 实体含{'、'.join(candidate_only[:3])}，本事件无。")
    if target_only:
        differences.append(f"本事件 top 实体含{'、'.join(target_only[:3])}，对方无。")

    target_tier = _dominant_tier(target.tier_counts)
    candidate_tier = _dominant_tier(candidate.tier_counts)
    if target_tier and candidate_tier:
        target_label = local_analyze.MEDIA_TIER_LABELS.get(target_tier, target_tier)
        candidate_label = local_analyze.MEDIA_TIER_LABELS.get(candidate_tier, candidate_tier)
        if target_tier != candidate_tier:
            differences.append(f"对方以{candidate_label}为主，本事件以{target_label}为主。")
    if target.event.article_count != candidate.event.article_count or target.event.source_count != candidate.event.source_count:
        differences.append(
            f"对方样本为 {candidate.event.article_count} 篇、{candidate.event.source_count} 个来源；"
            f"本事件为 {target.event.article_count} 篇、{target.event.source_count} 个来源。"
        )
    return differences[:4]


def _target_payload(topic: Topic, features: EventFeatures) -> dict[str, Any]:
    return {
        "topic_id": topic.id,
        "event_id": features.event.id,
        "title_zh": features.event.title_zh or features.event.title,
        "entities": list(features.entities.values()),
        "keywords": list(features.keywords.values()),
    }


def _scan_payload(total: int, eligible: int, scanned: int, truncated: bool) -> dict[str, Any]:
    note = f"线性检查全库 {total} 个事件；排除目标话题后 {eligible} 个候选，实际扫描 {scanned} 个。"
    if truncated:
        note += f"候选池已按 {CANDIDATE_SCAN_CAP} 个上限截断。"
    return {
        "total_events": total,
        "eligible_candidates": eligible,
        "scanned_candidates": scanned,
        "candidate_cap": CANDIDATE_SCAN_CAP,
        "truncated": truncated,
        "note": note,
    }


def _topics_by_id(session: Session, events: list[Event]) -> dict[int, Topic]:
    topic_ids = sorted({event.topic_id for event in events})
    if not topic_ids:
        return {}
    return {topic.id: topic for topic in session.exec(select(Topic).where(Topic.id.in_(topic_ids))).all() if topic.id is not None}


def _score_label(score: int) -> str | None:
    if score >= 70:
        return "较强相似"
    if score >= 40:
        return "有限相似"
    return None


def _add_basis(basis: list[dict[str, Any]], kind: str, items: list[str], weight: int) -> None:
    if items and weight > 0:
        basis.append({"kind": kind, "items": items, "weight": weight})


def _named_terms(values: list[Any]) -> dict[str, str]:
    terms: dict[str, str] = {}
    for value in values:
        display = str(value.get("term") or "") if isinstance(value, dict) else str(value or "")
        normalized = _normalize(display)
        if normalized and normalized not in terms:
            terms[normalized] = display
    return terms


def _source_names(event: Event, rows: list[local_analyze.ArticleRow]) -> list[str]:
    names = [row.source for row in rows if row.source]
    for value in event.sources or []:
        name = str(value.get("name") or value.get("source") or "") if isinstance(value, dict) else str(value or "")
        if name:
            names.append(name)
    return list(dict.fromkeys(names))


def _dominant_tier(counts: Counter[str]) -> str:
    return counts.most_common(1)[0][0] if counts else ""


def _ratio_weight(left: int, right: int, maximum: int) -> int:
    high = max(left, right)
    return round(maximum * min(left, right) / high) if high > 0 else 0


def _date_difference(left: datetime | None, right: datetime | None) -> str:
    if left and right:
        months = abs((right.year - left.year) * 12 + right.month - left.month)
        return f"目标事件为 {left.date().isoformat()}，对方为 {right.date().isoformat()}，时间相差 {months} 个月。"
    if left:
        return f"目标事件日期为 {left.date().isoformat()}，对方日期缺失，无法量化时间差。"
    if right:
        return f"目标事件日期缺失，对方日期为 {right.date().isoformat()}，无法量化时间差。"
    return "双方事件日期均缺失，无法量化时间差。"


def _day_gap(left: datetime | None, right: datetime | None) -> int | None:
    return abs((right - left).days) if left and right else None


def _date_label(value: datetime | None) -> str | None:
    return value.date().isoformat() if value else None


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    return local_analyze._normalize_entity_token(text)


def _unique_ints(values: list[Any]) -> list[int]:
    result = []
    for value in values:
        try:
            item = int(value)
        except (TypeError, ValueError):
            continue
        if item not in result:
            result.append(item)
    return result
