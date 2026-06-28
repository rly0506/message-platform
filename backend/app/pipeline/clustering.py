"""Article clustering helpers for local no-LLM analysis."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from rapidfuzz import fuzz

from app import rule_config

try:
    import jieba  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    jieba = None

TITLE_SIMILARITY = 58
STOPWORDS = rule_config.string_set("stopwords")
CJK_STOP_TERMS = rule_config.string_set("cjk_stop_terms")

def _cluster_articles(rows: list[ArticleRow]) -> list[list[ArticleRow]]:
    clusters: list[list[ArticleRow]] = []
    signatures: list[Counter[str]] = []

    for row in rows:
        sig = _signature(row.title)
        best_idx = -1
        best_score = 0.0
        for idx, cluster in enumerate(clusters):
            days = abs(((row.published_at or datetime.min) - (cluster[0].published_at or datetime.min)).days)
            if days > 45:
                continue
            token_score = _jaccard(sig, signatures[idx])
            title_score = max(fuzz.token_set_ratio(row.title, other.title) for other in cluster) / 100
            score = max(token_score, title_score)
            if score > best_score:
                best_idx = idx
                best_score = score
        if best_idx >= 0 and best_score >= TITLE_SIMILARITY / 100:
            clusters[best_idx].append(row)
            signatures[best_idx].update(sig)
        else:
            clusters.append([row])
            signatures.append(sig)
    return clusters
def _signature(text: str) -> Counter[str]:
    text = _clean_title(text).lower()
    words = [word for word in re.findall(r"[a-z0-9][a-z0-9\-]{1,}", text) if word not in STOPWORDS]
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    grams: list[str] = []
    if jieba is not None:
        for token in jieba.cut(" ".join(cjk_chunks), cut_all=False):
            token = token.strip()
            if len(token) >= 2 and token not in CJK_STOP_TERMS:
                grams.append(token)
    else:
        for chunk in cjk_chunks:
            if len(chunk) <= 6:
                grams.append(chunk)
            else:
                for size in (6, 5, 4):
                    grams.extend(chunk[idx : idx + size] for idx in range(0, len(chunk) - size + 1))
    return Counter(words + [term for term in grams if term not in CJK_STOP_TERMS])
def _jaccard(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    a = set(left)
    b = set(right)
    return len(a & b) / max(1, len(a | b))
def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return re.split(r"\s[-|_]\s", title, maxsplit=1)[0].strip() or title
