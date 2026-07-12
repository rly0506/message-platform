"""Evidence-first event graph persistence and payload helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.db import Article, Event, EventRelation, Topic, TopicArticle
from app.pipeline import local_analyze

EDGE_LIMIT = 24
RELATION_DIRECTIONS = {
    "chronological": "directed",
    "shared_article": "symmetric",
    "shared_entity": "symmetric",
    "shared_source": "symmetric",
}


def topic_event_graph_payload(session: Session, topic: Topic) -> dict[str, Any]:
    events = _topic_events(session, topic.id)
    if not events:
        local_events = local_events_for_topic(session, topic)
        if local_events:
            events = sync_topic_events(session, topic.id, local_events)
            rebuild_event_relations(session, topic.id, events=events)

    if not events:
        return {
            "nodes": [],
            "edges": [],
            "degraded": True,
            "note": "没有可用事件节点，先采集并运行本地分析后再生成事件关系图。",
        }

    degraded_note = _degraded_note(events)
    if degraded_note:
        _delete_relations_for_event_ids(session, _event_ids(events))
        return {
            "nodes": [_node_payload(row) for row in events],
            "edges": [],
            "degraded": True,
            "note": degraded_note,
        }

    relations = _topic_relations(session, events)
    if not relations:
        relations = rebuild_event_relations(session, topic.id, events=events)

    return {
        "nodes": [_node_payload(row) for row in events],
        "edges": [_edge_payload(row) for row in relations],
        "degraded": False,
        "note": "",
    }


def local_events_for_topic(session: Session, topic: Topic) -> list[dict[str, Any]]:
    rows = session.exec(
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic.id)
        .where(TopicArticle.relevant == True)  # noqa: E712
    ).all()
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
    return local_analyze.analyze_topic(topic.name, article_rows).get("events", [])


def sync_topic_events(
    session: Session,
    topic_id: int,
    events: list[dict[str, Any]],
    *,
    commit: bool = True,
) -> list[Event]:
    incoming = _events_by_key(events)
    existing = _topic_events(session, topic_id)
    existing_by_key = {_event_key(row.date): row for row in existing}

    stale_ids = [row.id for key, row in existing_by_key.items() if key not in incoming and row.id is not None]
    _delete_relations_for_event_ids(session, stale_ids, commit=False)
    for key, row in existing_by_key.items():
        if key not in incoming:
            session.delete(row)

    for key, data in incoming.items():
        row = existing_by_key.get(key)
        if not row:
            row = Event(topic_id=topic_id, date=data["date"])
        row.title = data["title"]
        row.title_zh = data["title_zh"]
        row.summary_zh = data["summary_zh"]
        row.article_ids = data["article_ids"]
        row.sources = data["sources"]
        row.entities = data["entities"]
        row.source_count = data["source_count"]
        row.article_count = data["article_count"]
        row.updated_at = datetime.utcnow()
        session.add(row)
    if commit:
        session.commit()
    else:
        session.flush()

    rows = _topic_events(session, topic_id)
    for row in rows:
        session.refresh(row)
    return rows


def rebuild_event_relations(
    session: Session,
    topic_id: int,
    events: list[Event] | None = None,
    *,
    commit: bool = True,
) -> list[EventRelation]:
    events = events or _topic_events(session, topic_id)
    event_ids = _event_ids(events)
    _delete_relations_for_event_ids(session, event_ids, commit=False)
    if _degraded_note(events):
        if commit:
            session.commit()
        else:
            session.flush()
        return []

    for spec in _relation_specs(events):
        session.add(EventRelation(
            from_event_id=spec["from_id"],
            to_event_id=spec["to_id"],
            relation_type=spec["relation_type"],
            evidence=spec["evidence"],
            items=spec["items"],
        ))
    if commit:
        session.commit()
    else:
        session.flush()
    return _topic_relations(session, events)


def delete_topic_graph(session: Session, topic_id: int) -> None:
    events = _topic_events(session, topic_id)
    _delete_relations_for_event_ids(session, _event_ids(events), commit=False)
    for event in events:
        session.delete(event)
    session.commit()


def _events_by_key(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for event in events:
        normalized = _normalize_event(event)
        key = _event_key(normalized["date"])
        existing = out.get(key)
        if not existing:
            out[key] = normalized
            continue
        existing["article_ids"] = _unique([*existing["article_ids"], *normalized["article_ids"]])
        existing["sources"] = _unique([*existing["sources"], *normalized["sources"]])
        existing["entities"] = _unique([*existing["entities"], *normalized["entities"]])
        existing["source_count"] = max(existing["source_count"], normalized["source_count"], len(existing["sources"]))
        existing["article_count"] = max(existing["article_count"], normalized["article_count"], len(existing["article_ids"]))
    return out


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    article_ids = [int(value) for value in event.get("article_ids", []) if _intable(value)]
    sources = _source_names(event)
    entities = _event_terms(event)
    return {
        "date": _parse_event_date(event.get("date")),
        "title": str(event.get("title") or event.get("title_zh") or ""),
        "title_zh": str(event.get("title_zh") or event.get("title") or ""),
        "summary_zh": str(event.get("summary_zh") or ""),
        "article_ids": article_ids,
        "sources": sources,
        "entities": entities,
        "source_count": int(event.get("source_count") or len(sources)),
        "article_count": int(event.get("article_count") or len(article_ids)),
    }


def _relation_specs(events: list[Event]) -> list[dict[str, Any]]:
    ordered = _sort_events(events)
    specs: list[dict[str, Any]] = []
    for index in range(len(ordered) - 1):
        current = ordered[index]
        next_event = ordered[index + 1]
        specs.append({
            "from_id": current.id,
            "to_id": next_event.id,
            "relation_type": "chronological",
            "evidence": f"{_date_label(current.date)} -> {_date_label(next_event.date)}",
            "items": [current.title_zh, next_event.title_zh],
        })

    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            first = ordered[left]
            second = ordered[right]
            shared_articles = _intersect(first.article_ids or [], second.article_ids or [])
            if shared_articles:
                specs.append({
                    "from_id": first.id,
                    "to_id": second.id,
                    "relation_type": "shared_article",
                    "evidence": f"{len(shared_articles)} 篇共同报道",
                    "items": [f"#{article_id}" for article_id in shared_articles[:5]],
                })

            shared_entities = _intersect(first.entities or [], second.entities or [])
            if shared_entities:
                specs.append({
                    "from_id": first.id,
                    "to_id": second.id,
                    "relation_type": "shared_entity",
                    "evidence": "、".join(shared_entities[:4]),
                    "items": shared_entities[:6],
                })

            shared_sources = _intersect(first.sources or [], second.sources or [])
            if shared_sources:
                specs.append({
                    "from_id": first.id,
                    "to_id": second.id,
                    "relation_type": "shared_source",
                    "evidence": "、".join(shared_sources[:4]),
                    "items": shared_sources[:6],
                })
    return [spec for spec in specs[:EDGE_LIMIT] if spec["from_id"] is not None and spec["to_id"] is not None]


def _topic_events(session: Session, topic_id: int) -> list[Event]:
    rows = session.exec(select(Event).where(Event.topic_id == topic_id)).all()
    return _sort_events(rows)


def _topic_relations(session: Session, events: list[Event]) -> list[EventRelation]:
    ids = _event_ids(events)
    if not ids:
        return []
    id_set = set(ids)
    relations = session.exec(select(EventRelation).where(EventRelation.from_event_id.in_(ids))).all()
    relations.extend(session.exec(select(EventRelation).where(EventRelation.to_event_id.in_(ids))).all())
    unique = {
        row.id: row
        for row in relations
        if row.id is not None and row.from_event_id in id_set and row.to_event_id in id_set
    }
    return sorted(unique.values(), key=lambda row: row.id or 0)


def _delete_relations_for_event_ids(
    session: Session,
    event_ids: list[int],
    *,
    commit: bool = True,
) -> None:
    if not event_ids:
        return
    rows = session.exec(select(EventRelation).where(EventRelation.from_event_id.in_(event_ids))).all()
    rows.extend(session.exec(select(EventRelation).where(EventRelation.to_event_id.in_(event_ids))).all())
    seen: set[int] = set()
    for row in rows:
        if row.id in seen:
            continue
        if row.id is not None:
            seen.add(row.id)
        session.delete(row)
    if commit:
        session.commit()
    else:
        session.flush()


def _node_payload(row: Event) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date.date().isoformat() if row.date else None,
        "title_zh": row.title_zh,
        "summary_zh": row.summary_zh,
        "source_count": row.source_count,
        "article_count": row.article_count,
    }


def _edge_payload(row: EventRelation) -> dict[str, Any]:
    return {
        "from_id": row.from_event_id,
        "to_id": row.to_event_id,
        "relation_type": row.relation_type,
        "direction": RELATION_DIRECTIONS.get(row.relation_type, "symmetric"),
        "evidence": row.evidence,
        "items": row.items or [],
    }


def _degraded_note(events: list[Event]) -> str:
    if len(events) < 2:
        return "至少需要 2 个事件节点才能生成事件关系图。"
    if all(event.date is None for event in events):
        return "事件节点缺少可用日期，无法生成时间锚定的事件关系图。"
    return ""


def _sort_events(events: list[Event]) -> list[Event]:
    return sorted(events, key=lambda row: (row.date or datetime.max, row.id or 0))


def _event_ids(events: list[Event]) -> list[int]:
    return [event.id for event in events if event.id is not None]


def _event_key(value: datetime | None) -> str:
    return value.date().isoformat() if value else "unknown"


def _date_label(value: datetime | None) -> str:
    return value.date().isoformat() if value else "?"


def _parse_event_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = str(value)
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _source_names(event: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for source in event.get("sources", []) or []:
        if isinstance(source, dict):
            names.append(str(source.get("name") or source.get("source") or ""))
        else:
            names.append(str(source or ""))
    for source in event.get("source_matrix", []) or []:
        if isinstance(source, dict):
            names.append(str(source.get("source") or source.get("name") or ""))
    return _unique([name for name in names if name])


def _event_terms(event: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for field in ("entities", "location_signals", "keywords"):
        for item in event.get(field, []) or []:
            if isinstance(item, dict):
                terms.append(str(item.get("term") or ""))
            else:
                terms.append(str(item or ""))
    return _unique([term for term in terms if term])


def _intersect(left: list[Any], right: list[Any]) -> list[Any]:
    right_set = set(right)
    return _unique([item for item in left if item in right_set])


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _intable(value: Any) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True
