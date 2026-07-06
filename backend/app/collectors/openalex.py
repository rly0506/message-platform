"""OpenAlex academic-paper collector."""
from __future__ import annotations

import time
from typing import Any

import httpx

from app import config


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
USER_AGENT = "DossierBot/0.1"


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    tokens: list[tuple[int, str]] = []
    for word, positions in inverted.items():
        for position in positions or []:
            tokens.append((int(position), str(word)))
    return " ".join(word for _, word in sorted(tokens))


def normalize_work(work: dict[str, Any]) -> dict[str, Any]:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    openalex_id = work.get("id", "")
    doi = work.get("doi") or ""
    return {
        "openalex_id": openalex_id,
        "title": work.get("title") or "",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "year": work.get("publication_year"),
        "cited_by_count": int(work.get("cited_by_count") or 0),
        "authors": [
            author_name
            for author_name in (
                (authorship.get("author") or {}).get("display_name")
                for authorship in work.get("authorships") or []
            )
            if author_name
        ],
        "venue": source.get("display_name") or "",
        "concepts": [
            {
                "name": concept.get("display_name", ""),
                "score": concept.get("score", 0),
                "level": concept.get("level"),
            }
            for concept in work.get("concepts") or []
            if concept.get("display_name")
        ],
        "doi": doi,
        "openalex_url": openalex_id,
        "url": primary_location.get("landing_page_url") or work.get("doi") or work.get("id", ""),
        "referenced_works": list(work.get("referenced_works") or []),
    }


def converged_citation_edges(papers: list[dict[str, Any]]) -> list[dict[str, str]]:
    paper_ids = {paper.get("openalex_id") for paper in papers if paper.get("openalex_id")}
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for paper in papers:
        citing_id = paper.get("openalex_id")
        if not citing_id:
            continue
        for cited_id in paper.get("referenced_works") or []:
            if cited_id not in paper_ids:
                continue
            pair = (citing_id, cited_id)
            if pair in seen:
                continue
            seen.add(pair)
            edges.append({"citing_openalex_id": citing_id, "cited_openalex_id": cited_id})
    return edges


def search_works(query: str, top_n: int = 30) -> list[dict[str, Any]]:
    """Search OpenAlex with relevance-first ordering.

    We intentionally do not sort by cited_by_count: OpenAlex relevance is used first
    to avoid high-citation off-topic papers, then citations are used only in local
    academic analysis scoring.
    """
    params = {
        "search": query,
        "per-page": max(1, min(200, top_n)),
    }
    if config.OPENALEX_API_KEY:
        params["api_key"] = config.OPENALEX_API_KEY
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
                response = client.get(OPENALEX_WORKS_URL, params=params)
            if response.status_code == 429 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            return [normalize_work(work) for work in response.json().get("results", [])]
        except Exception as exc:  # pragma: no cover - network boundary
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            break
    raise RuntimeError(f"OpenAlex request failed: {last_error}")
