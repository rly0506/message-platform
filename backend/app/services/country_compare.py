"""Read-only country comparison aggregation for topic articles."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app import rule_config
from app.db import Article, Topic, TopicArticle
from app.pipeline import local_analyze


Country = dict[str, str]


def normalize_source(source: str) -> str:
    value = (source or "").strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" /|_-")


def country_of_source(source: str) -> Country | None:
    normalized = normalize_source(source)
    if not normalized:
        return None
    for marker, country in _country_map("media_country").items():
        if _matches_place_marker(marker, normalized):
            return dict(country)
    return None


def country_of_source_country(source_country: str) -> Country | None:
    normalized = normalize_source(source_country)
    if not normalized:
        return None
    for marker, country in _country_map("gdelt_country").items():
        if marker == normalized:
            return dict(country)
    return None


def country_of_place(place: str) -> Country | None:
    normalized = normalize_source(place)
    if not normalized:
        return None
    for marker, country in _country_map("place_country").items():
        if _matches_place_marker(marker, normalized):
            return dict(country)
    return None


def build_country_compare(
    session: Session,
    topic: Topic,
    article_ids: list[int] | None = None,
) -> dict[str, Any]:
    rows = _topic_rows(session, topic.id, article_ids)
    party_counts = _infer_party_countries(rows)
    g20 = g20_members()
    g20_codes = {item["code"] for item in g20}
    anchors = {item["code"]: item for item in g20}
    for code, count in party_counts.items():
        country = _country_by_code(code)
        if country:
            item = dict(country)
            item["mention_count"] = count
            anchors[code] = item

    display_countries = {code: dict(country) for code, country in anchors.items()}
    grouped: dict[str, list[tuple[TopicArticle, Article]]] = defaultdict(list)
    unmapped_count = 0
    for topic_article, article in rows:
        country = _country_for_article(article)
        if not country:
            unmapped_count += 1
            continue
        grouped[country["code"]].append((topic_article, article))
        display_countries.setdefault(country["code"], dict(country))

    country_rows = []
    for code, country in display_countries.items():
        items = grouped.get(code, [])
        outlets = sorted({article.source for _, article in items if article.source})
        stances = Counter(
            topic_article.stance
            or local_analyze.infer_stance(
                article.title_zh or article.title,
                article.snippet_zh or article.snippet,
            )
            for topic_article, article in items
        )
        country_rows.append({
            "code": code,
            "name": country["name"],
            "is_g20": code in g20_codes,
            "is_party": code in party_counts,
            "party_mention_count": party_counts.get(code, 0),
            "article_count": len(items),
            "stance_distribution": dict(stances),
            "outlets": outlets,
            "first_report": _first_report(items),
            "sample_titles": _sample_titles(items),
        })

    country_rows.sort(key=lambda item: (
        not item["is_party"],
        -item["article_count"],
        item["name"],
    ))

    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "article_scope_count": len(rows),
        "anchor_countries": sorted(anchors.values(), key=lambda item: item["name"]),
        "countries": country_rows,
        "first_reporters": _first_reporters(rows),
        "unmapped_count": unmapped_count,
    }


def g20_members() -> list[Country]:
    return [dict(item) for item in rule_config.load_rule_config().get("g20_members", [])]


def _topic_rows(
    session: Session,
    topic_id: int | None,
    article_ids: list[int] | None,
) -> list[tuple[TopicArticle, Article]]:
    stmt = (
        select(TopicArticle, Article)
        .where(TopicArticle.article_id == Article.id)
        .where(TopicArticle.topic_id == topic_id)
        .where(TopicArticle.relevant == True)  # noqa: E712
    )
    if article_ids:
        stmt = stmt.where(Article.id.in_(article_ids))
    return list(session.exec(stmt).all())


def _infer_party_countries(rows: list[tuple[TopicArticle, Article]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for _topic_article, article in rows:
        text = " ".join([
            article.title_zh or article.title or "",
            article.snippet_zh or article.snippet or "",
        ])
        for entity in local_analyze._entities_for_text(text, limit=40):
            if entity.get("kind") in {"place", "name"}:
                country = country_of_place(entity.get("term", ""))
                if country:
                    counts[country["code"]] += int(entity.get("count", 1) or 1)
        for marker, country in _country_map("place_country").items():
            if _matches_place_marker(marker, normalize_source(text)):
                counts[country["code"]] += 1
    return counts


def _matches_place_marker(marker: str, text: str) -> bool:
    if not marker or not text:
        return False
    if marker == text:
        return True
    if marker.isascii():
        return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None
    return marker in text


def _first_report(items: list[tuple[TopicArticle, Article]]) -> dict[str, Any] | None:
    dated = [article for _topic_article, article in items if article.published_at]
    if not dated:
        return None
    article = min(dated, key=lambda item: item.published_at or datetime.max)
    return {
        "date": _iso(article.published_at),
        "outlet": article.source,
        "title": article.title_zh or article.title,
        "article_id": article.id,
    }


def _first_reporters(rows: list[tuple[TopicArticle, Article]]) -> list[dict[str, Any]]:
    out = []
    for _topic_article, article in rows:
        country = _country_for_article(article)
        if not country or not article.published_at:
            continue
        out.append({
            "date": _iso(article.published_at),
            "country_code": country["code"],
            "country_name": country["name"],
            "outlet": article.source,
            "title": article.title_zh or article.title,
            "article_id": article.id,
        })
    out.sort(key=lambda item: item["date"] or "")
    return out[:30]


def _sample_titles(items: list[tuple[TopicArticle, Article]], limit: int = 5) -> list[str]:
    ordered = sorted(items, key=lambda pair: pair[1].published_at or datetime.max)
    return [(article.title_zh or article.title) for _topic_article, article in ordered[:limit]]


def _country_by_code(code: str) -> Country | None:
    for country in [
        *g20_members(),
        *_country_map("place_country").values(),
        *_country_map("media_country").values(),
        *_country_map("gdelt_country").values(),
    ]:
        if country["code"] == code:
            return dict(country)
    return None


def _country_for_article(article: Article) -> Country | None:
    if article.source_country:
        return country_of_source_country(article.source_country)
    return country_of_source(article.source)


def _country_map(name: str) -> dict[str, Country]:
    raw = rule_config.load_rule_config().get(name, {})
    return {
        normalize_source(key): {"code": str(value["code"]), "name": str(value["name"])}
        for key, value in raw.items()
        if isinstance(value, dict) and value.get("code") and value.get("name")
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
