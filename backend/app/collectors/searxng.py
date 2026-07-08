"""SearXNG collector for publisher-direct news URLs.

SearXNG itself is an optional local service. This module only knows how to call
an already-running instance and normalize its JSON results.
"""
from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from app import config


class SearxngError(RuntimeError):
    """SearXNG service/network failure."""


def collect(query: str) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    base_url = config.SEARXNG_URL.rstrip("/")
    try:
        with httpx.Client(
            base_url=base_url,
            timeout=config.RSS_FETCH_TIMEOUT,
            trust_env=True,
            follow_redirects=True,
            headers={"User-Agent": config.RSS_USER_AGENT},
        ) as client:
            response = client.get(
                "/search",
                params={"q": query, "format": "json", "categories": "news"},
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        raise SearxngError(f"{type(exc).__name__}: {exc}") from exc
    return [_normalize_result(item) for item in payload.get("results", []) if item.get("url")]


def _normalize_result(item: dict[str, Any]) -> dict[str, Any]:
    url = str(item.get("url", ""))
    return {
        "url": url,
        "title": str(item.get("title", "")),
        "source": _domain(url),
        "source_lang": "",
        "source_country": "",
        "source_tier": "",
        "published_at": None,
        "snippet": str(item.get("content", ""))[:1000],
        "collector": "searxng",
        "engine": str(item.get("engine", "")),
    }


def _domain(url: str) -> str:
    try:
        return urllib.parse.urlsplit(url).netloc
    except ValueError:
        return ""
