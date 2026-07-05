from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlmodel import Session, select

from app.db import SourceRegistry
from app.services import payloads


def list_sources(session: Session) -> list[dict[str, Any]]:
    rows = session.exec(
        select(SourceRegistry).order_by(SourceRegistry.enabled.desc(), SourceRegistry.name)
    ).all()
    return [source_payload(source) for source in rows]


def create_source(session: Session, data: dict[str, Any]) -> dict[str, Any]:
    name = required_text(data.get("name"), "Source name is required")
    url = clean_url(data.get("url"))
    existing = session.exec(select(SourceRegistry).where(SourceRegistry.url == url)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Source URL already exists")
    source = SourceRegistry(
        name=name,
        url=url,
        country=clean_text(data.get("country")),
        language=clean_text(data.get("language") or data.get("lang")),
        source_type=clean_text(data.get("source_type")) or "rss",
        quality_tier=clean_text(data.get("quality_tier") or data.get("tier")) or "user",
        requires_login=bool(data.get("requires_login", False)),
        fulltext_support=bool(data.get("fulltext_support", False)),
        enabled=bool(data.get("enabled", True)),
        notes=clean_text(data.get("notes")),
        coverage=clean_text(data.get("coverage")),
        access=clean_text(data.get("access")),
        coverage_reason=clean_text(data.get("coverage_reason")),
        last_tested=clean_text(data.get("last_tested")),
        state_media=bool(data.get("state_media", False)),
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source_payload(source)


def import_sources(session: Session, data: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "country": clean_text(data.get("country")),
        "language": clean_text(data.get("language") or data.get("lang")),
        "source_type": clean_text(data.get("source_type")) or "rss",
        "quality_tier": clean_text(data.get("quality_tier") or data.get("tier")) or "user",
        "requires_login": bool(data.get("requires_login", False)),
        "fulltext_support": bool(data.get("fulltext_support", False)),
        "enabled": bool(data.get("enabled", True)),
        "coverage": clean_text(data.get("coverage")),
        "access": clean_text(data.get("access")),
        "coverage_reason": clean_text(data.get("coverage_reason")),
        "last_tested": clean_text(data.get("last_tested")),
        "state_media": bool(data.get("state_media", False)),
    }
    created = []
    duplicates = []
    invalid = []
    seen_urls: set[str] = set()

    for raw_line in str(data.get("text") or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parsed = parse_import_line(line)
        if not parsed:
            invalid.append({"line": line, "error": "No http(s) URL found"})
            continue
        name, url = parsed
        if url in seen_urls:
            duplicates.append({"line": line, "url": url, "name": name, "reason": "duplicate in import"})
            continue
        seen_urls.add(url)
        existing = session.exec(select(SourceRegistry).where(SourceRegistry.url == url)).first()
        if existing:
            duplicates.append(source_payload(existing) | {"line": line, "reason": "already exists"})
            continue
        source = SourceRegistry(
            name=name,
            url=url,
            country=defaults["country"],
            language=defaults["language"],
            source_type=defaults["source_type"],
            quality_tier=defaults["quality_tier"],
            requires_login=defaults["requires_login"],
            fulltext_support=defaults["fulltext_support"],
            enabled=defaults["enabled"],
            coverage=defaults["coverage"],
            access=defaults["access"],
            coverage_reason=defaults["coverage_reason"],
            last_tested=defaults["last_tested"],
            state_media=defaults["state_media"],
            notes=clean_text(data.get("notes")) or "bulk-imported source",
        )
        session.add(source)
        session.commit()
        session.refresh(source)
        created.append(source_payload(source))

    return {
        "created_count": len(created),
        "duplicate_count": len(duplicates),
        "invalid_count": len(invalid),
        "created": created,
        "duplicates": duplicates,
        "invalid": invalid,
    }


def update_source(session: Session, source_id: int, data: dict[str, Any]) -> dict[str, Any]:
    source = session.get(SourceRegistry, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field in (
        "name",
        "country",
        "language",
        "source_type",
        "quality_tier",
        "last_status",
        "last_error",
        "notes",
        "coverage",
        "access",
        "coverage_reason",
        "last_tested",
    ):
        if field in data:
            setattr(source, field, str(data.get(field) or "").strip())
    for field in ("enabled", "requires_login", "fulltext_support", "state_media"):
        if field in data:
            setattr(source, field, bool(data.get(field)))
    source.updated_at = datetime.utcnow()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source_payload(source)


def parse_import_line(line: str) -> tuple[str, str] | None:
    parts = line.replace(",", " ").split()
    url = next((part.strip("()[]<>") for part in parts if is_http_url(part.strip("()[]<>"))), "")
    if not url:
        return None
    name_text = line.replace(url, " ")
    name_text = " ".join(name_text.replace(",", " ").split()).strip(" -:")
    name = name_text or urlparse(url).netloc
    return name[:160], url


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def required_text(value: Any, message: str) -> str:
    text = clean_text(value)
    if not text:
        raise HTTPException(status_code=422, detail=message)
    return text


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def clean_url(value: Any) -> str:
    url = required_text(value, "Source URL is required")
    if not is_http_url(url):
        raise HTTPException(status_code=422, detail="Source URL must be http(s)")
    return url


def source_payload(source: SourceRegistry) -> dict[str, Any]:
    return {
        "id": source.id,
        "name": source.name,
        "url": source.url,
        "country": source.country,
        "language": source.language,
        "source_type": source.source_type,
        "quality_tier": source.quality_tier,
        "requires_login": source.requires_login,
        "fulltext_support": source.fulltext_support,
        "enabled": source.enabled,
        "last_status": source.last_status,
        "last_error": source.last_error,
        "last_fetched_at": payloads.iso(source.last_fetched_at),
        "article_count": source.article_count,
        "notes": source.notes,
        "coverage": source.coverage,
        "access": source.access,
        "coverage_reason": source.coverage_reason,
        "last_tested": source.last_tested,
        "state_media": source.state_media,
        "created_at": payloads.iso(source.created_at),
        "updated_at": payloads.iso(source.updated_at),
    }
