"""Scoring, event assembly, and framing helpers for local no-LLM analysis."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Callable

from app import rule_config
from app.pipeline.categorization import infer_report_category, infer_stance
from app.pipeline.categorization import _event_category_reason
from app.pipeline.clustering import _clean_title
from app.pipeline.entities import _entities_for_text, _keywords_for_rows

MEDIA_SOURCE_TIERS = rule_config.string_tuple_dict("media_source_tiers")
MEDIA_TIER_LABELS = rule_config.string_dict("media_tier_labels")
AUTHORITY_SOURCES = rule_config.string_set("authority_sources")
SIGNIFICANCE_CRITERIA = [
    {
        "key": "authority",
        "label": "权威来源",
        "description": "是否由国际通讯社、主流媒体、官方媒体或专业权威来源报道。",
        "weight": 0.22,
    },
    {
        "key": "pickup",
        "label": "扩散/引用代理",
        "description": "当前没有全网引用计数时，用同一事件的报道篇数与来源数近似衡量被多次引用或转载。",
        "weight": 0.25,
    },
    {
        "key": "impact",
        "label": "未来影响信号",
        "description": "是否出现发布、战争、制裁、监管、突破、开源、收购、停火等改变后续走向的词。",
        "weight": 0.25,
    },
    {
        "key": "spread",
        "label": "持续时间",
        "description": "事件是否跨多个日期持续发酵，而不是单日孤立报道。",
        "weight": 0.10,
    },
    {
        "key": "relevance",
        "label": "主题相关度",
        "description": "事件与当前搜索词/专题关键词的匹配程度。",
        "weight": 0.18,
    },
]
IMPACT_TERMS = {
    "发布": 1.2, "推出": 1.1, "首次": 1.0, "突破": 1.4, "大模型": 1.0,
    "模型": 0.8, "架构": 1.2, "开源": 1.0, "监管": 1.1, "禁令": 1.3,
    "法案": 1.2, "标准": 1.1, "事故": 1.2, "危机": 1.1, "战争": 1.5,
    "袭击": 1.2, "停火": 1.2, "谈判": 0.9, "制裁": 1.3, "收购": 1.0,
    "融资": 0.8, "上市": 1.0, "破产": 1.1, "裁员": 0.8,
    "transformer": 1.6, "gpt": 1.2, "gpt-4": 1.8, "deepseek": 1.6,
    "gemini": 1.1, "llama": 1.1, "claude": 1.0, "sora": 1.2,
    "chip": 0.8, "semiconductor": 1.0, "regulation": 1.2, "ban": 1.1,
    "act": 0.8, "launch": 1.0, "release": 1.0, "breakthrough": 1.4,
    "open-source": 1.1, "acquisition": 1.0, "war": 1.4, "strike": 1.1,
    "ceasefire": 1.2, "sanction": 1.2,
}

def _event_from_cluster(
    cluster: list[ArticleRow],
    entities_for_text: Callable[..., list[dict[str, Any]]] = _entities_for_text,
) -> dict[str, Any]:
    sources = {row.source for row in cluster if row.source}
    dates = sorted(row.published_at for row in cluster if row.published_at)
    representative = max(cluster, key=lambda row: (_impact_hits(row.title), row.relevance, -len(row.title)))
    stances = Counter(row.stance or infer_stance(row.title, row.snippet) for row in cluster)
    breakdown = _score_breakdown(cluster)
    score = sum(item["value"] * item["weight"] for item in breakdown.values())
    authority_sources = _authority_sources(cluster)
    title_text = " ".join(row.title for row in cluster)
    text = " ".join(f"{row.title} {row.snippet}" for row in cluster)
    category = infer_report_category(text)
    tier_scores = _media_tier_scores(cluster)
    entities = entities_for_text(text, limit=10, source_names=sources, use_spacy=False)
    place_signals = [entity for entity in entities if entity.get("kind") == "place"][:6]
    importance_label = _importance_label(score)
    coverage_label = _coverage_label(len(sources), len(cluster), bool(authority_sources))

    return {
        "date": dates[0].date().isoformat() if dates else None,
        "title_zh": _clean_title(representative.title),
        "summary_zh": _event_summary(cluster, sources, dates, stances, category),
        "article_ids": [row.id for row in cluster],
        "score": round(score, 3),
        "importance_label": importance_label,
        "coverage_label": coverage_label,
        "selection_basis": _selection_basis(
            len(sources),
            len(cluster),
            authority_sources,
            _matched_impact_terms(title_text),
            _date_span_days(dates),
            representative.relevance,
        ),
        "source_count": len(sources),
        "article_count": len(cluster),
        "sources": _top_sources(cluster),
        "source_matrix": _source_matrix(cluster),
        "source_tiers": _source_tier_summary(tier_scores),
        "category": category,
        "category_reason": _event_category_reason(text, category),
        "stance": stances.most_common(1)[0][0] if stances else "中性观察",
        "score_breakdown": {
            key: {
                "label": item["label"],
                "value": round(item["value"], 3),
                "weight": item["weight"],
                "reason": item["reason"],
            }
            for key, item in breakdown.items()
        },
        "evidence": {
            "authority_sources": authority_sources,
            "source_count": len(sources),
            "article_count": len(cluster),
            "impact_terms": _matched_impact_terms(title_text),
            "date_span_days": _date_span_days(dates),
            "first_sources": _first_sources(cluster),
            "source_tiers": _source_tier_summary(tier_scores),
        },
        "keywords": _keywords_for_rows(cluster, limit=8),
        "entities": entities,
        "location_signals": place_signals,
    }


def _score_breakdown(cluster: list[ArticleRow]) -> dict[str, dict[str, Any]]:
    sources = {row.source for row in cluster if row.source}
    dates = [row.published_at for row in cluster if row.published_at]
    title_text = " ".join(row.title for row in cluster)
    authority = _authority_sources(cluster)
    tier_scores = _media_tier_scores(cluster)
    span_days = _date_span_days(dates)

    authority_tiers = {key: value for key, value in tier_scores.items() if key != "aggregator"}
    authority_score = min(1.0, (len(authority) / 2) + (sum(authority_tiers.values()) * 0.08))
    pickup_score = min(
        1.0,
        (math.log1p(len(sources)) / math.log(8) * 0.55)
        + (math.log1p(len(cluster)) / math.log(12) * 0.45),
    )
    impact_score = min(1.0, _impact_hits(title_text) / 4)
    spread_score = min(1.0, span_days / 14)
    relevance_score = sum(row.relevance for row in cluster) / max(1, len(cluster))

    return {
        "authority": {
            "label": "权威来源",
            "value": authority_score,
            "weight": 0.22,
            "reason": _authority_reason(authority, tier_scores),
        },
        "pickup": {
            "label": "扩散/引用代理",
            "value": pickup_score,
            "weight": 0.25,
            "reason": f"{len(sources)} 个来源、{len(cluster)} 篇报道集中到同一节点",
        },
        "impact": {
            "label": "未来影响信号",
            "value": impact_score,
            "weight": 0.25,
            "reason": "、".join(_matched_impact_terms(title_text)[:6]) or "未命中强影响词",
        },
        "spread": {
            "label": "持续时间",
            "value": spread_score,
            "weight": 0.10,
            "reason": f"持续约 {span_days} 天",
        },
        "relevance": {
            "label": "主题相关度",
            "value": relevance_score,
            "weight": 0.18,
            "reason": "由检索词命中比例估计",
        },
    }
def _event_summary(
    cluster: list[ArticleRow],
    sources: set[str],
    dates: list[datetime],
    stances: Counter[str],
    category: str,
) -> str:
    start = dates[0].date().isoformat() if dates else "未知时间"
    end = dates[-1].date().isoformat() if len(dates) > 1 else start
    when = start if start == end else f"{start} 至 {end}"
    stance_text = "、".join(f"{name}{count}篇" for name, count in stances.most_common(3))
    return (
        f"{when}，{len(sources)} 个来源的 {len(cluster)} 篇报道集中指向这一节点，报道功能判断为「{category}」。"
        f"入选依据包括权威来源、报道扩散、未来影响信号、持续时间和主题相关度；"
        f"态度分布为：{stance_text or '中性观察'}。"
    )
def _stance_evolution(rows: list[ArticleRow]) -> list[dict[str, Any]]:
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    article_ids: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if not row.published_at:
            continue
        bucket = row.published_at.strftime("%Y-%m")
        stance = row.stance or infer_stance(row.title, row.snippet)
        buckets[bucket][stance] += 1
        article_ids[bucket].append(row.id)

    out = []
    for bucket in sorted(buckets):
        counts = dict(buckets[bucket])
        dominant = max(counts.items(), key=lambda item: item[1])[0]
        out.append({
            "period": bucket,
            "dominant_stance": dominant,
            "counts": counts,
            "article_ids": article_ids[bucket],
        })
    return out
def _framing_from_evolution(
    evolution: list[dict[str, Any]],
    rows: list[ArticleRow],
) -> list[dict[str, Any]]:
    all_counts = Counter(row.stance or infer_stance(row.title, row.snippet) for row in rows)
    first_seen: dict[str, str] = {}
    last_seen: dict[str, str] = {}
    article_ids: dict[str, list[int]] = defaultdict(list)

    for item in evolution:
        for stance, count in item["counts"].items():
            if count <= 0:
                continue
            first_seen.setdefault(stance, item["period"])
            last_seen[stance] = item["period"]
            article_ids[stance].extend(item["article_ids"])

    framing = []
    for stance, count in all_counts.most_common():
        trend = _trend_for_stance(stance, evolution)
        framing.append({
            "party": stance,
            "stance": trend,
            "summary_zh": (
                f"共 {count} 篇报道呈现这一取向，出现区间为 "
                f"{first_seen.get(stance, '未知')} 至 {last_seen.get(stance, '未知')}。"
                f"相较早期，近期变化判断为：{trend}。"
            ),
            "article_ids": sorted(set(article_ids[stance]))[:80],
        })
    return framing[:8]
def _trend_for_stance(stance: str, evolution: list[dict[str, Any]]) -> str:
    if len(evolution) < 2:
        return "样本不足"
    midpoint = max(1, len(evolution) // 2)
    early = sum(item["counts"].get(stance, 0) for item in evolution[:midpoint])
    late = sum(item["counts"].get(stance, 0) for item in evolution[midpoint:])
    if late >= early + 3:
        return "近期增强"
    if early >= late + 3:
        return "近期减弱"
    return "基本稳定"
def _analysis_text(name: str, events: list[dict[str, Any]], framing: list[dict[str, Any]]) -> str:
    if not events:
        return "本地规则暂未发现足够集中的重大事件节点。建议扩大检索词或采集更长时间跨度。"
    strongest = max(events, key=lambda item: item["score"])
    stance_line = "；".join(f"{item['party']}：{item['stance']}" for item in framing[:4]) or "暂无明显分布"
    return (
        f"## 本地规则分析\n\n"
        f"专题「{name}」当前识别出 {len(events)} 个重大事件节点。"
        f"分数最高的节点是「{strongest['title_zh']}」，得分 {strongest['score']}，"
        f"由 {strongest['source_count']} 个来源和 {strongest['article_count']} 篇报道支撑。\n\n"
        f"关键节点标准：权威来源、报道扩散/引用代理、未来影响信号、持续时间、主题相关度。\n\n"
        f"态度变化概览：{stance_line}。\n\n"
        f"注意：这是无模型额度时的本地启发式结果，适合做第一轮筛选；"
        f"它不能替代人工核查，也不能真正计算全网引用量。"
    )
def _top_sources(cluster: list[ArticleRow], limit: int = 5) -> list[dict[str, Any]]:
    counts = Counter(row.source for row in cluster if row.source)
    return [
        {
            "name": name,
            "count": count,
            "tier": _source_tier(name),
            "tier_label": MEDIA_TIER_LABELS.get(_source_tier(name), "其他来源"),
        }
        for name, count in counts.most_common(limit)
    ]
def _source_matrix(cluster: list[ArticleRow], limit: int = 12) -> list[dict[str, Any]]:
    grouped: dict[str, list[ArticleRow]] = defaultdict(list)
    for row in cluster:
        grouped[row.source or "未知来源"].append(row)

    out = []
    for source, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: row.published_at or datetime.max)
        stances = Counter(row.stance or infer_stance(row.title, row.snippet) for row in rows)
        categories = Counter(infer_report_category(row.title, row.snippet) for row in rows)
        first = ordered[0]
        tier = _source_tier(source)
        out.append({
            "source": source,
            "tier": tier,
            "tier_label": MEDIA_TIER_LABELS.get(tier, "其他来源"),
            "article_count": len(rows),
            "first_published_at": first.published_at.isoformat() if first.published_at else None,
            "latest_published_at": ordered[-1].published_at.isoformat() if ordered[-1].published_at else None,
            "dominant_stance": stances.most_common(1)[0][0] if stances else "中性观察",
            "stance_counts": dict(stances),
            "dominant_category": categories.most_common(1)[0][0] if categories else "行动进展",
            "category_counts": dict(categories),
            "representative_title": _clean_title(first.title),
            "article_ids": [row.id for row in ordered[:20]],
        })

    return sorted(
        out,
        key=lambda item: (
            list(MEDIA_TIER_LABELS).index(item["tier"]) if item["tier"] in MEDIA_TIER_LABELS else 99,
            -item["article_count"],
            item["first_published_at"] or "",
            item["source"],
        ),
    )[:limit]
def _first_sources(cluster: list[ArticleRow], limit: int = 3) -> list[dict[str, Any]]:
    rows = sorted(cluster, key=lambda row: row.published_at or datetime.max)
    seen: set[str] = set()
    out = []
    for row in rows:
        if not row.source or row.source in seen:
            continue
        seen.add(row.source)
        out.append({
            "name": row.source,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "title": _clean_title(row.title),
            "tier": _source_tier(row.source),
            "tier_label": MEDIA_TIER_LABELS.get(_source_tier(row.source), "其他来源"),
        })
        if len(out) >= limit:
            break
    return out
def _importance_label(score: float) -> str:
    if score >= 0.68:
        return "高"
    if score >= 0.42:
        return "中"
    if score > 0:
        return "低"
    return "未评分"
def _coverage_label(source_count: int, article_count: int, has_authority: bool) -> str:
    if source_count >= 4 and article_count >= 6:
        return "多源覆盖"
    if source_count >= 2 and has_authority:
        return "权威来源覆盖"
    if source_count >= 2:
        return "有限多源"
    return "单源线索"
def _selection_basis(
    source_count: int,
    article_count: int,
    authority: list[str],
    impact_terms: list[str],
    span_days: int,
    relevance: float,
) -> list[str]:
    basis = [f"{source_count} 个来源、{article_count} 篇报道"]
    if authority:
        basis.append("权威来源：" + "、".join(authority[:3]))
    if impact_terms:
        basis.append("影响信号：" + "、".join(impact_terms[:4]))
    if span_days > 1:
        basis.append(f"持续约 {span_days} 天")
    if relevance >= 0.75:
        basis.append("与检索主题高度相关")
    return basis
def _source_tier_summary(tier_scores: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"key": key, "label": MEDIA_TIER_LABELS.get(key, key), "count": count}
        for key, count in sorted(
            tier_scores.items(),
            key=lambda item: (
                list(MEDIA_TIER_LABELS).index(item[0]) if item[0] in MEDIA_TIER_LABELS else 99,
                item[0],
            ),
        )
        if count > 0
    ]
def _source_tier(source: str) -> str:
    source_lower = (source or "").lower()
    for tier, markers in MEDIA_SOURCE_TIERS.items():
        if any(marker in source_lower for marker in markers):
            return tier
    return "other"
def _impact_hits(text: str) -> float:
    lower = text.lower()
    return sum(weight for term, weight in IMPACT_TERMS.items() if term.lower() in lower)
def _matched_impact_terms(text: str) -> list[str]:
    lower = text.lower()
    return [term for term in IMPACT_TERMS if term.lower() in lower]
def _authority_sources(cluster: list[ArticleRow]) -> list[str]:
    found = []
    for row in cluster:
        source = (row.source or "").lower()
        if any(authority in source for authority in AUTHORITY_SOURCES):
            found.append(row.source)
    return sorted(set(found))
def _media_tier_scores(cluster: list[ArticleRow]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for row in cluster:
        tier = _source_tier(row.source)
        scores[tier] = scores.get(tier, 0) + 1
    return scores
def _authority_reason(authority: list[str], tier_scores: dict[str, int]) -> str:
    parts = []
    if authority:
        parts.append("命中来源：" + "、".join(authority[:4]))
    if tier_scores:
        parts.append(
            "来源层级："
            + "、".join(f"{MEDIA_TIER_LABELS.get(k, k)}{v}" for k, v in tier_scores.items())
        )
    return "；".join(parts) if parts else "未命中内置权威来源表"
def _date_span_days(dates: list[datetime]) -> int:
    if not dates:
        return 1
    return (max(dates) - min(dates)).days + 1
