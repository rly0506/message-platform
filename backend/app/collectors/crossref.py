"""Crossref academic metadata collector."""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
USER_AGENT = "DossierBot/0.1 (personal research workbench)"


def normalize_work(work: dict[str, Any]) -> dict[str, Any]:
    doi = normalize_doi(work.get("DOI", ""))
    title = first_text(work.get("title"))
    container = first_text(work.get("container-title"))
    year = issued_year(work)
    authors = [
        " ".join(str(part).strip() for part in (author.get("given", ""), author.get("family", "")) if part).strip()
        for author in work.get("author") or []
    ]
    authors = [author for author in authors if author]
    return {
        "openalex_id": f"crossref:{doi.removeprefix('https://doi.org/')}" if doi else f"crossref:{title[:80]}",
        "title": title,
        "abstract": strip_crossref_markup(work.get("abstract", "")),
        "year": year,
        "cited_by_count": 0,
        "authors": authors,
        "venue": container or first_text(work.get("publisher")),
        "concepts": [],
        "doi": doi,
        "openalex_url": "",
        "url": doi or first_text(work.get("URL")),
        "referenced_works": [],
        "sources": ["crossref"],
        "source_count": 1,
        "source_links": [{"source": "crossref", "url": crossref_work_url(doi)}] if doi else [],
    }


def search_works(query: str, top_n: int = 30) -> list[dict[str, Any]]:
    params = {
        "query.bibliographic": query,
        "rows": max(1, min(100, top_n)),
    }
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT}) as client:
                response = client.get(CROSSREF_WORKS_URL, params=params)
            if response.status_code == 429 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            items = response.json().get("message", {}).get("items", [])
            return [normalize_work(item) for item in items if item.get("title") or item.get("DOI")]
        except Exception as exc:  # pragma: no cover - network boundary
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            break
    raise RuntimeError(f"Crossref request failed: {last_error}")


def normalize_doi(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.removeprefix("doi:").strip()
    raw = raw.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if not raw:
        return ""
    return f"https://doi.org/{raw.lower()}"


def crossref_work_url(doi: str) -> str:
    raw = normalize_doi(doi).removeprefix("https://doi.org/")
    return f"{CROSSREF_WORKS_URL}/{quote(raw, safe='')}" if raw else ""


def first_text(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0] if value else "").strip()
    return str(value or "").strip()


def issued_year(work: dict[str, Any]) -> int | None:
    date_parts = (work.get("issued") or {}).get("date-parts") or []
    if not date_parts or not date_parts[0]:
        return None
    try:
        return int(date_parts[0][0])
    except (TypeError, ValueError):
        return None


def strip_crossref_markup(value: Any) -> str:
    text = str(value or "")
    return (
        text.replace("<jats:p>", "")
        .replace("</jats:p>", "")
        .replace("<p>", "")
        .replace("</p>", "")
        .strip()
    )
