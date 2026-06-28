"""Local, no-LLM event synthesis for topic dossiers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from app.pipeline import categorization as _categorization
from app.pipeline import clustering as _clustering
from app.pipeline import entities as _entities
from app.pipeline import scoring as _scoring

MAX_EVENTS = 30
TITLE_SIMILARITY = _clustering.TITLE_SIMILARITY

STOPWORDS = _clustering.STOPWORDS
MEDIA_SOURCE_TIERS = _scoring.MEDIA_SOURCE_TIERS
MEDIA_TIER_LABELS = _scoring.MEDIA_TIER_LABELS
CJK_STOP_TERMS = _clustering.CJK_STOP_TERMS
ENTITY_STOPWORDS = _entities.ENTITY_STOPWORDS
AUTHORITY_SOURCES = _scoring.AUTHORITY_SOURCES

SIGNIFICANCE_CRITERIA = _scoring.SIGNIFICANCE_CRITERIA
IMPACT_TERMS = _scoring.IMPACT_TERMS
STANCE_RULES = _categorization.STANCE_RULES
CATEGORY_RULES = _categorization.CATEGORY_RULES
ENTITY_ALIASES = _entities.ENTITY_ALIASES
ENTITY_KIND_LABELS = _entities.ENTITY_KIND_LABELS
ENTITY_KIND_ORDER = _entities.ENTITY_KIND_ORDER
SPACY_MODEL_NAMES = _entities.SPACY_MODEL_NAMES
SPACY_ENTITY_KINDS = _entities.SPACY_ENTITY_KINDS
SPACY_TEXT_LIMIT = _entities.SPACY_TEXT_LIMIT
CJK_PLACE_CORRECTIONS = _entities.CJK_PLACE_CORRECTIONS
CJK_PERSON_NOISE = _entities.CJK_PERSON_NOISE
CJK_ORGANIZATION_NOISE_TERMS = _entities.CJK_ORGANIZATION_NOISE_TERMS
CJK_ORGANIZATION_EVENT_MARKERS = _entities.CJK_ORGANIZATION_EVENT_MARKERS

jieba = _clustering.jieba
pseg = _entities.pseg


@dataclass
class ArticleRow:
    id: int
    title: str
    source: str
    published_at: datetime | None
    snippet: str
    relevance: float
    stance: str = ""


def analyze_topic(name: str, rows: list[ArticleRow], max_events: int = MAX_EVENTS) -> dict[str, Any]:
    dated = [row for row in rows if row.published_at and row.title]
    if not dated:
        return {
            "events": [],
            "framing": [],
            "analysis_md": "",
            "stance_evolution": [],
            "keywords": [],
            "entities": [],
            "entity_groups": [],
            "criteria": SIGNIFICANCE_CRITERIA,
        }

    clusters = _cluster_articles(sorted(dated, key=lambda row: row.published_at or datetime.min))
    events = [_event_from_cluster(cluster) for cluster in clusters if cluster]
    events.sort(key=lambda item: item["score"], reverse=True)
    major_events = sorted(events[:max_events], key=lambda item: item["date"] or "")

    evolution = _stance_evolution(dated)
    framing = _framing_from_evolution(evolution, dated)
    analysis = _analysis_text(name, major_events, framing)

    entities = _entity_cloud(dated, major_events)
    return {
        "events": major_events,
        "framing": framing,
        "analysis_md": analysis,
        "stance_evolution": evolution,
        "keywords": _keyword_cloud(dated, major_events),
        "entities": entities,
        "entity_groups": grouped_entities(entities),
        "criteria": SIGNIFICANCE_CRITERIA,
    }



def infer_stance(title: str, snippet: str = "") -> str:
    return _categorization.infer_stance(title, snippet)


def infer_report_category(title: str, snippet: str = "") -> str:
    return _categorization.infer_report_category(title, snippet)


def report_category_reason(category: str, title: str, snippet: str = "") -> str:
    return _categorization.report_category_reason(category, title, snippet)


def _cluster_articles(rows: list[ArticleRow]) -> list[list[ArticleRow]]:
    return _clustering._cluster_articles(rows)


def _event_from_cluster(cluster: list[ArticleRow]) -> dict[str, Any]:
    return _scoring._event_from_cluster(cluster, entities_for_text=_entities_for_text)


def _entity_cloud(rows: list[ArticleRow], events: list[dict[str, Any]], limit: int = 40) -> list[dict[str, Any]]:
    return _entities._entity_cloud(rows, events, limit=limit, entities_for_text=_entities_for_text)


def _entities_for_text(
    text: str,
    limit: int = 20,
    source_names: Iterable[str] | None = None,
    use_spacy: bool = True,
) -> list[dict[str, Any]]:
    return _entities._entities_for_text(
        text,
        limit=limit,
        source_names=source_names,
        use_spacy=use_spacy,
        spacy_entities=_spacy_entities,
        pseg_module=pseg,
    )


def _spacy_entities(text: str) -> list[tuple[str, str]]:
    return _entities._spacy_entities(text)


def _spacy_models() -> tuple[Any, ...]:
    return _entities._spacy_models()


_score_breakdown = _scoring._score_breakdown
_event_summary = _scoring._event_summary
_stance_evolution = _scoring._stance_evolution
_framing_from_evolution = _scoring._framing_from_evolution
_trend_for_stance = _scoring._trend_for_stance
_analysis_text = _scoring._analysis_text
_keyword_cloud = _entities._keyword_cloud
_keywords_for_rows = _entities._keywords_for_rows
grouped_entities = _entities.grouped_entities
_entity_blocklist = _entities._entity_blocklist
_source_block_terms = _entities._source_block_terms
_strip_blocked_entities = _entities._strip_blocked_entities
_clean_entity_text = _entities._clean_entity_text
_blocked_entity = _entities._blocked_entity
_normalize_entity_token = _entities._normalize_entity_token
_english_place_kind = _entities._english_place_kind
_correct_spacy_kind = _entities._correct_spacy_kind
_correct_person_kind = _entities._correct_person_kind
_known_place_term = _entities._known_place_term
_place_markers = _entities._place_markers
_person_noise = _entities._person_noise
_organization_noise = _entities._organization_noise
_english_place_markers = _entities._english_place_markers
_matches_ascii_marker = _entities._matches_ascii_marker
_candidate_entity = _entities._candidate_entity
_noisy_entity = _entities._noisy_entity
_bad_keyword = _entities._bad_keyword
_event_category = _categorization._event_category
_event_category_reason = _categorization._event_category_reason
_top_sources = _scoring._top_sources
_source_matrix = _scoring._source_matrix
_first_sources = _scoring._first_sources
_importance_label = _scoring._importance_label
_coverage_label = _scoring._coverage_label
_selection_basis = _scoring._selection_basis
_source_tier_summary = _scoring._source_tier_summary
_source_tier = _scoring._source_tier
_signature = _clustering._signature
_jaccard = _clustering._jaccard
_impact_hits = _scoring._impact_hits
_matched_impact_terms = _scoring._matched_impact_terms
_authority_sources = _scoring._authority_sources
_media_tier_scores = _scoring._media_tier_scores
_authority_reason = _scoring._authority_reason
_date_span_days = _scoring._date_span_days
_clean_title = _clustering._clean_title
