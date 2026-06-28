"""Entity and keyword extraction for local no-LLM analysis."""
from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any, Callable, Iterable

from app import rule_config
from app.pipeline.clustering import _signature

try:
    import jieba.posseg as pseg  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pseg = None

STOPWORDS = rule_config.string_set("stopwords")
CJK_STOP_TERMS = rule_config.string_set("cjk_stop_terms")
ENTITY_STOPWORDS = rule_config.string_set("entity_stopwords")
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

def _keyword_cloud(rows: list[ArticleRow], events: list[dict[str, Any]], limit: int = 45) -> list[dict[str, Any]]:
    event_ids = {article_id for event in events for article_id in event.get("article_ids", [])}
    selected = [row for row in rows if row.id in event_ids] or rows
    return _keywords_for_rows(selected, limit=limit)


def _entity_cloud(
    rows: list[ArticleRow],
    events: list[dict[str, Any]],
    limit: int = 40,
    entities_for_text: Callable[..., list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    text = " ".join(f"{row.title} {row.snippet}" for row in rows)
    handler = entities_for_text or _entities_for_text
    return handler(text, limit=limit, source_names=(row.source for row in rows if row.source))


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


_PSEG_DEFAULT = object()

def _entities_for_text(
    text: str,
    limit: int = 20,
    source_names: Iterable[str] | None = None,
    use_spacy: bool = True,
    spacy_entities: Callable[[str], list[tuple[str, str]]] | None = None,
    pseg_module: Any = _PSEG_DEFAULT,
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
        for term, kind in (spacy_entities or _spacy_entities)(scan_text):
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

    active_pseg = pseg if pseg_module is _PSEG_DEFAULT else pseg_module
    if active_pseg is not None:
        for word, flag in active_pseg.cut(scan_text):
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
