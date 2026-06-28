"""Local, no-LLM event synthesis for topic dossiers."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Iterable

from rapidfuzz import fuzz

from app import rule_config

try:
    import jieba  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    jieba = None

try:
    import jieba.posseg as pseg  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pseg = None

MAX_EVENTS = 30
TITLE_SIMILARITY = 58

STOPWORDS = rule_config.string_set("stopwords")
MEDIA_SOURCE_TIERS = rule_config.string_tuple_dict("media_source_tiers")
MEDIA_TIER_LABELS = rule_config.string_dict("media_tier_labels")
CJK_STOP_TERMS = rule_config.string_set("cjk_stop_terms")
ENTITY_STOPWORDS = rule_config.string_set("entity_stopwords")
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

STANCE_RULES = [
    ("政策/监管", ("监管", "法案", "规则", "审查", "调查", "禁令", "合规", "regulation", "law", "ban", "probe")),
    ("支持/乐观", ("增长", "突破", "领先", "利好", "机会", "加速", "投资", "看好", "surge", "boost", "growth", "optimistic")),
    ("风险/审慎", ("风险", "担忧", "争议", "安全", "失业", "泡沫", "下滑", "警告", "risk", "concern", "warning", "safety")),
    ("竞争/商业", ("竞争", "价格", "市场", "收购", "融资", "客户", "营收", "competition", "market", "deal", "funding")),
    ("冲突/安全", ("战争", "袭击", "导弹", "军事", "停火", "制裁", "war", "strike", "military", "ceasefire", "sanction")),
]

CATEGORY_RULES = [
    ("起因背景", ("起因", "背景", "根源", "历史", "为什么", "由来", "矛盾", "tension", "background", "root", "why")),
    ("触发事件", ("发起", "袭击", "空袭", "导弹", "最后通牒", "遇袭", "爆发", "attack", "strike", "launch", "ultimatum", "killed")),
    ("行动进展", ("升级", "报复", "军事", "部署", "推进", "拦截", "打击", "war", "military", "retaliation", "escalation", "missile")),
    ("各方回应", ("回应", "反制", "谴责", "警告", "声明", "表示", "称", "response", "retaliation", "warns", "condemns", "says")),
    ("外交降温", ("谈判", "停火", "斡旋", "外交", "联合国", "协议", "ceasefire", "talks", "diplomacy", "deal", "un")),
    ("影响后果", ("影响", "后果", "油价", "市场", "黄金", "供应链", "伤亡", "casualties", "impact", "oil", "market", "gold")),
    ("分析解读", ("分析", "预测", "可能", "风险", "意味着", "前景", "scenario", "analysis", "could", "risk", "means")),
    ("核实澄清", ("澄清", "否认", "辟谣", "证实", "核实", "clarify", "denies", "fact check", "verified")),
    ("后续处置", ("调查", "制裁", "审判", "处置", "重建", "撤离", "probe", "sanction", "trial", "evacuation")),
]

ENTITY_ALIASES = rule_config.entity_aliases()
ENTITY_KIND_LABELS = rule_config.string_dict("entity_kind_labels")
ENTITY_KIND_ORDER = rule_config.string_tuple("entity_kind_order")

SPACY_MODEL_NAMES = ("zh_core_web_sm", "en_core_web_sm")
SPACY_ENTITY_KINDS = {
    "PERSON": "person",
    "PER": "person",
    "ORG": "organization",
    "GPE": "place",
    "LOC": "place",
    "FAC": "place",
}
SPACY_TEXT_LIMIT = 900
CJK_PLACE_CORRECTIONS = frozenset({"黎巴嫩", "霍尔木兹", "凡尔赛", "哈尔克岛"})
CJK_PERSON_NOISE = frozenset({"红艳艳", "英法德"})
CJK_ORGANIZATION_NOISE_TERMS = frozenset({"通讯社", "备忘录", "谅解备忘录", "协议", "战争"})
CJK_ORGANIZATION_EVENT_MARKERS = ("战争", "冲突", "协议", "备忘录")


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
    text = f"{title} {snippet}".lower()
    scores: dict[str, int] = {}
    for label, terms in STANCE_RULES:
        score = sum(1 for term in terms if term.lower() in text)
        if score:
            scores[label] = score
    if not scores:
        return "中性观察"
    return max(scores.items(), key=lambda item: item[1])[0]


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


def _event_from_cluster(cluster: list[ArticleRow]) -> dict[str, Any]:
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
    entities = _entities_for_text(text, limit=10, source_names=sources, use_spacy=False)
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


def _keyword_cloud(rows: list[ArticleRow], events: list[dict[str, Any]], limit: int = 45) -> list[dict[str, Any]]:
    event_ids = {article_id for event in events for article_id in event.get("article_ids", [])}
    selected = [row for row in rows if row.id in event_ids] or rows
    return _keywords_for_rows(selected, limit=limit)


def _entity_cloud(rows: list[ArticleRow], events: list[dict[str, Any]], limit: int = 40) -> list[dict[str, Any]]:
    text = " ".join(f"{row.title} {row.snippet}" for row in rows)
    return _entities_for_text(text, limit=limit, source_names=(row.source for row in rows if row.source))


def _keywords_for_rows(rows: list[ArticleRow], limit: int = 20) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(_signature(f"{row.title} {row.snippet}"))
    out = []
    for term, count in counts.most_common(limit * 2):
        if len(term) < 2 or term.isdigit() or _bad_keyword(term):
            continue
        out.append({"term": term, "count": count, "weight": min(1.0, math.log1p(count) / math.log(20))})
        if len(out) >= limit:
            break
    return out


def _entities_for_text(
    text: str,
    limit: int = 20,
    source_names: Iterable[str] | None = None,
    use_spacy: bool = True,
) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    blocked_terms = _entity_blocklist(source_names)
    scan_text = _strip_blocked_entities(_clean_entity_text(text), blocked_terms)
    lower = scan_text.lower()
    known_terms: set[str] = set()
    for canonical, (kind, aliases) in ENTITY_ALIASES.items():
        count = 0
        for alias in aliases:
            known_terms.add(alias.lower())
            if _blocked_entity(canonical, blocked_terms) or _blocked_entity(alias, blocked_terms):
                continue
            if re.search(r"[\u4e00-\u9fff]", alias):
                count += scan_text.count(alias)
            else:
                count += len(re.findall(rf"\b{re.escape(alias.lower())}\b", lower))
        if count:
            counts[(canonical, kind)] += count

    if use_spacy:
        for term, kind in _spacy_entities(scan_text):
            if _blocked_entity(term, blocked_terms):
                continue
            if _noisy_entity(term):
                continue
            kind = _correct_spacy_kind(term, kind)
            if not kind:
                continue
            if term.lower() in known_terms:
                continue
            counts[(term, kind)] += 1

    if pseg is not None:
        for word, flag in pseg.cut(scan_text):
            term = str(word).strip()
            if not _candidate_entity(term):
                continue
            if _blocked_entity(term, blocked_terms):
                continue
            if term.lower() in known_terms:
                continue
            if flag.startswith("nr"):
                kind = _correct_person_kind(term)
                if kind:
                    counts[(term, kind)] += 1
            elif flag.startswith("ns"):
                counts[(term, "place")] += 1
            elif flag.startswith("nt"):
                counts[(term, "organization")] += 1
            elif flag.startswith("nz"):
                counts[(term, "concept")] += 1

    # Fallback for common capitalized proper nouns in English headlines.
    for match in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", scan_text):
        if not _candidate_entity(match):
            continue
        if _blocked_entity(match, blocked_terms):
            continue
        if match.lower() in known_terms:
            continue
        counts[(match, _english_place_kind(match) or "name")] += 1

    out = []
    filtered_counts = (
        item for item in counts.items()
        if not (item[0][1] == "organization" and _organization_noise(item[0][0]))
    )
    ranked = sorted(
        filtered_counts,
        key=lambda item: (
            ENTITY_KIND_ORDER.index(item[0][1]) if item[0][1] in ENTITY_KIND_ORDER else 99,
            -item[1],
            item[0][0],
        ),
    )
    for (term, kind), count in ranked[:limit]:
        out.append({
            "term": term,
            "kind": kind,
            "kind_label": ENTITY_KIND_LABELS.get(kind, "其他名词"),
            "count": count,
            "weight": min(1.0, math.log1p(count) / math.log(20)),
        })
    return out


def grouped_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {kind: [] for kind in ENTITY_KIND_ORDER}
    for entity in entities:
        grouped.setdefault(entity.get("kind", "name"), []).append(entity)
    return [
        {
            "kind": kind,
            "label": ENTITY_KIND_LABELS.get(kind, "其他名词"),
            "items": items,
        }
        for kind, items in grouped.items()
        if items
    ]


def _spacy_entities(text: str) -> list[tuple[str, str]]:
    if not text:
        return []
    truncated = text[:SPACY_TEXT_LIMIT]
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for nlp in _spacy_models():
        try:
            doc = nlp(truncated)
        except Exception:
            continue
        for ent in getattr(doc, "ents", ()):
            kind = SPACY_ENTITY_KINDS.get(getattr(ent, "label_", ""))
            term = getattr(ent, "text", "").strip()
            if not kind or not _candidate_entity(term):
                continue
            if _noisy_entity(term):
                continue
            key = (term, kind)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


@lru_cache(maxsize=1)
def _spacy_models() -> tuple[Any, ...]:
    try:
        import spacy  # type: ignore
    except Exception:
        return ()

    models = []
    for name in SPACY_MODEL_NAMES:
        try:
            models.append(spacy.load(name))
        except Exception:
            continue
    return tuple(models)


def _entity_blocklist(source_names: Iterable[str] | None) -> set[str]:
    blocked = set(ENTITY_STOPWORDS)
    if not source_names:
        return {_normalize_entity_token(item) for item in blocked if item}
    for source in source_names:
        cleaned = str(source or "").strip()
        blocked.update(_source_block_terms(cleaned))
    return {_normalize_entity_token(item) for item in blocked if item}


def _source_block_terms(source: str) -> set[str]:
    cleaned = str(source or "").strip()
    if not cleaned:
        return set()
    terms = {cleaned}
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9&'.-]*(?:\s+[A-Za-z][A-Za-z0-9&'.-]*)*", cleaned)
    for phrase in ascii_words:
        phrase = phrase.strip(" -_|/:：")
        if len(phrase) >= 4:
            terms.add(phrase)
    cjk_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", cleaned)
    terms.update(cjk_chunks)
    return terms


def _strip_blocked_entities(text: str, blocked_terms: set[str]) -> str:
    cleaned = text
    for term in sorted(blocked_terms, key=len, reverse=True):
        if not term or len(term) < 3:
            continue
        if re.search(r"[\u4e00-\u9fff]", term):
            cleaned = cleaned.replace(term, " ")
        else:
            cleaned = re.sub(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", " ", cleaned, flags=re.I)
    return cleaned


def _clean_entity_text(text: str) -> str:
    cleaned = re.sub(r"<a\b[^>]*>", " ", text or "", flags=re.I)
    cleaned = re.sub(r"</a>", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"&[a-zA-Z]+;", " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\b[0-9A-Za-z_-]{14,}\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _blocked_entity(term: str, blocked_terms: set[str]) -> bool:
    normalized = _normalize_entity_token(term)
    if not normalized:
        return False
    if normalized in blocked_terms:
        return True
    return any(len(blocked) >= 4 and blocked in normalized for blocked in blocked_terms)



def _normalize_entity_token(term: str) -> str:
    value = (term or "").strip().lower()
    value = re.sub(r"https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" /|_-:：")


def _english_place_kind(term: str) -> str | None:
    normalized = _normalize_entity_token(term)
    if not normalized or re.search(r"[\u4e00-\u9fff]", normalized):
        return None
    for marker in _english_place_markers():
        if _matches_ascii_marker(marker, normalized):
            return "place"
    return None


def _correct_spacy_kind(term: str, kind: str) -> str | None:
    if kind == "person":
        return _correct_person_kind(term)
    if kind == "organization" and _organization_noise(term):
        return None
    return kind


def _correct_person_kind(term: str) -> str | None:
    if _known_place_term(term):
        return "place"
    if _person_noise(term):
        return None
    return "person"


def _known_place_term(term: str) -> bool:
    normalized = _normalize_entity_token(term)
    if not normalized:
        return False
    if term.strip() in CJK_PLACE_CORRECTIONS:
        return True
    if normalized in _place_markers():
        return True
    for marker in _place_markers():
        if re.search(r"[\u4e00-\u9fff]", marker) and len(normalized) >= 3 and (
            normalized in marker or marker in normalized
        ):
            return True
    return _english_place_kind(term) == "place"


@lru_cache(maxsize=1)
def _place_markers() -> frozenset[str]:
    markers: set[str] = set()
    config = rule_config.load_rule_config()
    for section in ("gdelt_country", "place_country", "media_country"):
        raw = config.get(section, {})
        if not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            normalized = _normalize_entity_token(str(key))
            if normalized:
                markers.add(normalized)
            if isinstance(value, dict):
                name = _normalize_entity_token(str(value.get("name", "")))
                if name:
                    markers.add(name)
    for canonical, (kind, aliases) in ENTITY_ALIASES.items():
        if kind != "place":
            continue
        for alias in (canonical, *aliases):
            normalized = _normalize_entity_token(alias)
            if normalized:
                markers.add(normalized)
    return frozenset(markers)


def _person_noise(term: str) -> bool:
    cleaned = term.strip()
    if not cleaned:
        return True
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        bad_fragments = ("已", "达成", "军", "战争", "协议", "备忘录", "通讯社", "称")
        if any(fragment in cleaned for fragment in bad_fragments):
            return True
        if cleaned.endswith(("岛", "湾", "海峡", "山", "河", "市", "省", "国")):
            return True
        if cleaned in CJK_PERSON_NOISE:
            return True
    return False


def _organization_noise(term: str) -> bool:
    cleaned = term.strip()
    if not cleaned:
        return True
    if not re.search(r"[\u4e00-\u9fff]", cleaned):
        return False
    if cleaned in CJK_ORGANIZATION_NOISE_TERMS:
        return True
    return any(marker in cleaned for marker in CJK_ORGANIZATION_EVENT_MARKERS)


@lru_cache(maxsize=1)
def _english_place_markers() -> tuple[str, ...]:
    markers: set[str] = set()
    config = rule_config.load_rule_config()
    for section in ("gdelt_country", "place_country"):
        raw = config.get(section, {})
        if not isinstance(raw, dict):
            continue
        for key in raw:
            normalized = _normalize_entity_token(str(key))
            if normalized and normalized.isascii():
                markers.add(normalized)
    for canonical, (kind, aliases) in ENTITY_ALIASES.items():
        if kind != "place":
            continue
        for alias in (canonical, *aliases):
            normalized = _normalize_entity_token(alias)
            if normalized and normalized.isascii():
                markers.add(normalized)
    return tuple(sorted(markers, key=lambda item: (-len(item), item)))


def _matches_ascii_marker(marker: str, text: str) -> bool:
    if marker == text:
        return True
    return re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text) is not None


def infer_report_category(title: str, snippet: str = "") -> str:
    return _event_category(f"{title} {snippet}".strip())


def report_category_reason(category: str, title: str, snippet: str = "") -> str:
    return _event_category_reason(f"{title} {snippet}".strip(), category)


def _event_category(text: str) -> str:
    lower = text.lower()
    scores = {}
    for label, terms in CATEGORY_RULES:
        score = sum(1 for term in terms if term.lower() in lower)
        if score:
            scores[label] = score
    if not scores:
        return "行动进展"
    return max(scores.items(), key=lambda item: item[1])[0]


def _event_category_reason(text: str, category: str) -> str:
    lower = text.lower()
    terms = next((terms for label, terms in CATEGORY_RULES if label == category), ())
    matched = [term for term in terms if term.lower() in lower]
    if matched:
        return "命中阶段词：" + "、".join(matched[:6])
    return "未命中明确阶段词，归为一般进展报道"


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


def _candidate_entity(term: str) -> bool:
    cleaned = term.strip()
    if not cleaned:
        return False
    lower = cleaned.lower()
    if lower in STOPWORDS or lower in ENTITY_STOPWORDS or cleaned in CJK_STOP_TERMS:
        return False
    if len(cleaned) < 2 or cleaned.isdigit():
        return False
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        if len(cleaned) > 12:
            return False
        if _bad_keyword(cleaned):
            return False
    elif len(cleaned) < 4:
        return False
    if _noisy_entity(cleaned):
        return False
    return True


def _noisy_entity(term: str) -> bool:
    cleaned = term.strip()
    if cleaned.lower() in {"nbsp", "amp", "quot"}:
        return True
    if not cleaned or re.search(r"[\u4e00-\u9fff\s]", cleaned):
        return False
    if len(cleaned) >= 12 and re.search(r"[A-Z]", cleaned) and re.search(r"[a-z]", cleaned):
        return True
    if re.search(r"[0-9]", cleaned) and len(cleaned) >= 8:
        return True
    return False


def _bad_keyword(term: str) -> bool:
    if term in CJK_STOP_TERMS:
        return True
    if re.search(r"[\u4e00-\u9fff]", term):
        if len(term) < 3:
            return True
        bad_fragments = ("影响", "如何", "几何", "深远", "报道", "新闻", "专栏")
        if any(fragment in term for fragment in bad_fragments):
            return True
    return False


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


def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return re.split(r"\s[-|_]\s", title, maxsplit=1)[0].strip() or title
