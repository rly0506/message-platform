"""算法初筛 (免费层): URL/标题去重 + 关键词相关性打分。

目的: 在送进 LLM 富化(花钱)之前，先把明显重复和不相关的剔掉。
"""
from __future__ import annotations

import re
import urllib.parse

from rapidfuzz import fuzz

from app.pipeline.term_match import term_hit

TITLE_DUP_THRESHOLD = 88   # 标题模糊相似度 >= 此值视为重复


def normalize_url(url: str) -> str:
    """去掉 utm_* 等跟踪参数与碎片，统一作去重键。"""
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    keep = [
        (k, v) for k, v in urllib.parse.parse_qsl(p.query)
        if not k.lower().startswith(("utm_", "fbclid", "gclid"))
    ]
    query = urllib.parse.urlencode(keep)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path.rstrip("/"), query, ""))


def _terms(queries: list[str]) -> list[str]:
    out: list[str] = []
    for q in queries:
        # 拆出词/短语: 既保留整句，也拆单词，提升中英文命中率
        out.append(q.lower())
        out.extend(w for w in re.split(r"[\s,，、]+", q.lower()) if len(w) >= 2)
    return list(dict.fromkeys(out))  # 去重保序


def relevance(text: str, queries: list[str]) -> float:
    """命中检索词的比例，作为 [0,1] 相关性。"""
    if not text:
        return 0.0
    terms = _terms(queries)
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if term_hit(term, text))
    return min(1.0, hits / max(1, len(set(queries))))


def dedup_and_score(
    incoming: list[dict],
    queries: list[str],
    known_urls: set[str],
    known_titles: list[str],
    min_relevance: float = 0.0,
) -> list[dict]:
    """对一批采集结果去重 + 打分。

    - known_urls / known_titles: 库中已有的 (规范化 url / 标题)，用于跨批次去重。
    - min_relevance: 低于此分丢弃 (RSS 检索式建议 >0，GDELT 已服务端过滤可设 0)。
    返回带 norm_url / relevance 字段、已去重的列表。
    """
    kept: list[dict] = []
    batch_titles: list[str] = []
    seen_norm = set(known_urls)

    for a in incoming:
        nurl = normalize_url(a["url"])
        if nurl in seen_norm:
            continue
        title = (a.get("title") or "").strip()
        # 标题模糊去重 (与库中 + 本批已留的对比)
        if title and _is_dup_title(title, known_titles + batch_titles):
            continue

        score = relevance(f"{title} {a.get('snippet', '')}", queries)
        if score < min_relevance:
            continue

        seen_norm.add(nurl)
        if title:
            batch_titles.append(title)
        a = dict(a)
        a["norm_url"] = nurl
        a["relevance"] = round(score, 3)
        kept.append(a)
    return kept


def _is_dup_title(title: str, existing: list[str]) -> bool:
    title_key = _title_key(title)
    for e in existing:
        existing_key = _title_key(e)
        if title_key and title_key == existing_key:
            return True
        if fuzz.token_set_ratio(title, e) >= TITLE_DUP_THRESHOLD:
            return True
        if title_key and existing_key and fuzz.ratio(title_key, existing_key) >= TITLE_DUP_THRESHOLD:
            return True
    return False


def _title_key(title: str) -> str:
    """Normalize title for duplicate checks across CJK spacing/punctuation variants."""
    return "".join(re.findall(r"[a-z0-9\u4e00-\u9fff]+", title.lower()))
