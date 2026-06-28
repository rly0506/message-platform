from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EvidenceArticlePayload(BaseModel):
    id: int
    url: str
    title: str
    source: str
    published_at: str | None
    snippet: str
    collector: str
    relevance: float
    stance: str
    category: str
    category_reason: str


class SourceMatrixPayload(BaseModel):
    source: str
    tier: str
    tier_label: str
    article_count: int
    first_published_at: str | None
    latest_published_at: str | None
    dominant_stance: str
    stance_counts: dict[str, int]
    dominant_category: str
    category_counts: dict[str, int]
    representative_title: str
    article_ids: list[int]


class LocalEventPayload(BaseModel):
    date: str | None
    title_zh: str
    summary_zh: str
    article_ids: list[int]
    score: float
    importance_label: str
    coverage_label: str
    selection_basis: list[str]
    source_count: int
    article_count: int
    sources: list[dict[str, Any]]
    source_matrix: list[SourceMatrixPayload]
    source_tiers: list[dict[str, Any]]
    category: str
    category_reason: str
    stance: str
    score_breakdown: dict[str, Any]
    evidence: dict[str, Any]
    keywords: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    location_signals: list[dict[str, Any]]
    evidence_articles: list[EvidenceArticlePayload] = []
