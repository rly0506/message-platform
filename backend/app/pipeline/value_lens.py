"""Local info-value reading hints for articles and discovery seeds."""
from __future__ import annotations

from typing import Any


InfoValueLabel = dict[str, str]

_LABELS: dict[str, InfoValueLabel] = {
    "suspected_hype": {
        "code": "suspected_hype",
        "label": "疑似造势",
        "note": "情绪强度高且干货密度低，提示先核查事实支撑，不把语气当证据。",
        "severity": "hint",
    },
    "availability_high": {
        "code": "availability_high",
        "label": "可得性偏高",
        "note": "这条材料很醒目，但当前可核查细节偏少，避免因容易想起而高估重要性。",
        "severity": "hint",
    },
    "availability_rising_seed": {
        "code": "availability_high",
        "label": "可得性偏高",
        "note": "信号正在快速上升，提示先把它当早期线索，而不是已经被充分验证的结论。",
        "severity": "hint",
    },
    "suspected_herding": {
        "code": "suspected_herding",
        "label": "疑似羊群",
        "note": "多家来源集中复述同一说法，提示可能是信息瀑布，不等于证据增强。",
        "severity": "hint",
    },
    "small_sample": {
        "code": "small_sample",
        "label": "样本不足",
        "note": "当前样本很少，只适合作为待复核线索，不足以支持趋势判断。",
        "severity": "hint",
    },
}


def _label(code: str) -> InfoValueLabel:
    return dict(_LABELS[code])


def article_info_value_labels(
    *,
    substance_score: int,
    emotion_score: int,
    source: str = "",
    title: str = "",
    snippet: str = "",
) -> list[InfoValueLabel]:
    """Return local reading hints for one article; hints are not truth judgments."""
    labels: list[InfoValueLabel] = []
    has_substance = substance_score >= 0
    has_emotion = emotion_score >= 0
    low_substance = has_substance and substance_score <= 35
    high_emotion = has_emotion and emotion_score >= 70

    if low_substance and high_emotion:
        labels.append(_label("suspected_hype"))
        labels.append(_label("availability_high"))
    elif low_substance:
        labels.append(_label("availability_high"))

    return _dedupe(labels)


def seed_info_value_labels(scored: Any) -> list[InfoValueLabel]:
    """Return local reading hints for a discovery seed."""
    labels: list[InfoValueLabel] = []
    delta = int(getattr(scored, "delta", 0) or 0)
    is_new = bool(getattr(scored, "is_new", False))
    runs_seen = int(getattr(scored, "runs_seen", 0) or 0)

    if delta >= 25:
        labels.append(_label("availability_rising_seed"))
    if is_new or runs_seen < 2:
        labels.append(_label("small_sample"))

    return _dedupe(labels)


def narrative_info_value_labels(signal: dict[str, Any]) -> list[InfoValueLabel]:
    """Flag narrative convergence as a possible information cascade."""
    source_count = int(signal.get("source_count") or 0)
    article_count = int(signal.get("article_count") or 0)
    if source_count >= 2 and article_count >= 3:
        return [_label("suspected_herding")]
    return []


def _dedupe(labels: list[InfoValueLabel]) -> list[InfoValueLabel]:
    seen: set[str] = set()
    out: list[InfoValueLabel] = []
    for label in labels:
        code = label["code"]
        if code in seen:
            continue
        seen.add(code)
        out.append(label)
    return out
