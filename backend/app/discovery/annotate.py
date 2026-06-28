"""发现层可选增强: LLM 二级分拣。

验证时发现: 原始前沿源噪声占快一半。这一层给每条种子标一句
"这是什么 / 为何可能重要 / 是否还在小圈子", 帮你快速判断, 把噪声折叠掉。

严格遵守项目红线: 这是**可选增强**, 不是核心链路。
- 没配 LLM key / 调用失败 -> 优雅降级, 返回未标注的原始种子, 报告照常出。
- LLM 只做"解读", 不做事实源, 不替代你的判断 (符合 future-directions 原则)。

省钱: 把本次全部种子打包成一次 LLM 调用 (而非每条一次)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app import config
from app.discovery.store import ScoredItem


@dataclass
class Annotation:
    """一条种子的 LLM 解读。"""
    external_id: str
    what: str = ""          # 这是什么 (一句话)
    why: str = ""           # 为何可能重要 (机制, 不站队)
    still_niche: bool = True  # 是否还在小圈子 (未出圈)


def annotate_seeds(seeds: list[ScoredItem], model: str = "") -> dict[str, Annotation]:
    """对种子批量 LLM 标注。返回 {external_id: Annotation}。

    无 LLM 或失败 -> 返回空 dict (调用方据此降级, 不报错)。
    """
    if not seeds:
        return {}
    if not config.LLM_API_KEY:
        return {}  # 未配置 -> 静默降级

    try:
        from app import llm
    except Exception:
        return {}

    target_model = model or config.HAIKU_MODEL
    prompt = _build_prompt(seeds)
    try:
        raw = llm.chat(
            target_model,
            prompt,
            max_tokens=1500,
            system=(
                "你是科技/财经/地缘领域的情报分析助手。对每条前沿信号, "
                "用最简短的中文判断它是什么、为何可能重要(讲机制与潜在影响,不站队、不做道德归责), "
                "以及它是否还停留在小圈子(未出圈)。严格输出 JSON 数组, 不要多余文字。"
            ),
        )
        data = llm.extract_json(raw)
    except Exception:
        return {}  # 网关超时 / 解析失败 -> 降级

    out: dict[str, Annotation] = {}
    if not isinstance(data, list):
        return {}
    for row in data:
        if not isinstance(row, dict):
            continue
        eid = str(row.get("id", "")).strip()
        if not eid:
            continue
        out[eid] = Annotation(
            external_id=eid,
            what=str(row.get("what", "")).strip()[:120],
            why=str(row.get("why", "")).strip()[:200],
            still_niche=bool(row.get("still_niche", True)),
        )
    return out


def _build_prompt(seeds: list[ScoredItem]) -> str:
    lines = [
        "下面是今天从注意力前沿(HN/arXiv/智库)捞到的候选信号。",
        "对每一条, 输出一个 JSON 对象, 字段:",
        '  id: 原样回填我给的 id',
        '  what: 这是什么 (≤30字)',
        '  why: 为何可能重要 (讲机制/潜在影响, ≤60字, 不站队)',
        '  still_niche: true/false (是否还在小圈子、未出圈)',
        "把所有对象放进一个 JSON 数组。只输出 JSON。",
        "",
        "候选:",
    ]
    for s in seeds:
        it = s.item
        summary = it.meta.get("summary", "") if isinstance(it.meta, dict) else ""
        extra = f" — {summary[:160]}" if summary else ""
        lines.append(f'- id={it.external_id} [{it.domain}] {it.title}{extra}')
    return "\n".join(lines)
