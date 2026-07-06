"""Topic-local narrative convergence signals, no factual judgment."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.pipeline.local_analyze import ArticleRow
from app.pipeline import value_lens

_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "by",
    "is", "are", "will", "say", "says", "said", "new", "latest", "after",
}


def detect_narrative_signals(rows: list[ArticleRow], limit: int = 5) -> list[dict[str, Any]]:
    buckets: dict[str, list[ArticleRow]] = defaultdict(list)
    for row in rows:
        seen = set(_phrases(row.title))
        for phrase in seen:
            buckets[phrase].append(row)

    signals = []
    for phrase, items in buckets.items():
        sources = {item.source for item in items if item.source}
        if len(items) < 3 or len(sources) < 2:
            continue
        dated = [item.published_at for item in items if item.published_at]
        ordered = sorted(
            items,
            key=lambda item: (
                item.published_at is None,
                item.published_at or datetime.max,
                item.title,
                item.id,
            ),
        )
        signal = {
            "claim": phrase,
            "source_count": len(sources),
            "article_count": len(items),
            "first_seen": min(dated).isoformat() if dated else None,
            "last_seen": max(dated).isoformat() if dated else None,
            "sources": sorted(sources)[:8],
            "article_ids": [item.id for item in ordered[:12]],
            "representative_titles": [item.title for item in ordered[:3]],
        }
        signal["info_value_labels"] = value_lens.narrative_info_value_labels(signal)
        signals.append(signal)
    return sorted(signals, key=lambda item: (-item["source_count"], -item["article_count"], item["claim"]))[:limit]


def _phrases(title: str) -> list[str]:
    words = [
        word for word in re.findall(r"[a-z0-9]+", title.lower())
        if len(word) > 1 and word not in _STOP
    ]
    if len(words) < 3:
        return []
    return [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
