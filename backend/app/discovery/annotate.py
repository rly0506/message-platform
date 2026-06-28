"""发现层可选增强: LLM 二级分拣。

验证时发现: 原始前沿源噪声占快一半。这一层给每条种子标一句
"这是什么 / 为何可能重要 / 是否还在小圈子", 帮你快速判断, 把噪声折叠掉。

严格遵守项目红线: 这是**可选增强**, 不是核心链路。
- 没配 LLM key / 调用失败 -> 优雅降级, 返回未标注的原始种子, 报告照常出。
- LLM 只做"解读", 不做事实源, 不替代你的判断 (符合 future-directions 原则)。

省钱: 把本次全部种子打包成一次 LLM 调用 (而非每条一次)。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app import config
from app.discovery.store import ScoredItem


def _heuristic_topic(title: str) -> str:
    """无 LLM 时的降级提炼: 取主干、去技术性后缀, 限长。

    不追求聪明, 只求"比原始长标题更像一个搜索词"。前端会让用户再改。
    """
    t = (title or "").strip()
    # 去掉常见栏目前缀 (MIT TR 的 "The Download:" 等)
    t = re.sub(r"^(the download|the algorithm)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
    # 冒号/破折号前的主干通常就是话题
    for sep in ("：", ":", " — ", " – ", " - "):
        if sep in t:
            t = t.split(sep, 1)[0].strip()
            break
    # 去掉 [pdf]/(2026)/【…】 这类括注
    t = re.sub(r"[\[\(【].*?[\]\)】]", "", t).strip()
    return t[:40] if t else (title or "").strip()[:40]


def distill_topic(title: str, domain: str = "") -> dict:
    """把一条前沿种子的长标题提炼成简短新闻话题词, 供事件分析台搜索。

    返回 {query, llm}:
      llm=True  -> 走了 LLM 提炼;
      llm=False -> 降级到启发式截断 (无 LLM key / 调用失败 / 空结果)。
    守住发现层红线: LLM 只是按需增强, 不可用时优雅降级, 绝不报错。
    """
    title = (title or "").strip()
    fallback = _heuristic_topic(title)
    if not title:
        return {"query": "", "llm": False}
    if not config.LLM_API_KEY:
        return {"query": fallback, "llm": False}

    try:
        from app import llm
    except Exception:
        return {"query": fallback, "llm": False}

    prompt = (
        f"前沿标题: {title}\n"
        f"领域: {domain or '未知'}\n\n"
        "把它转换成一个简短的新闻检索话题词 (2-6 个词), 用于在新闻聚合里搜相关报道。\n"
        "要求: 去掉论文/帖子腔 (如 DSpark、[pdf]、版本号), 提炼出底层主题; "
        "语言跟随该主题最可能的新闻语种 (中文或英文); 只输出话题词本身, 不要引号、标点或解释。"
    )
    try:
        raw = llm.chat(
            config.HAIKU_MODEL,
            prompt,
            max_tokens=40,
            system="你把科技/财经/地缘的前沿标题提炼成简短、可检索的新闻话题词。只输出话题词。",
        )
    except Exception:
        return {"query": fallback, "llm": False}

    q = _clean_term(raw)
    if not q:
        return {"query": fallback, "llm": False}
    return {"query": q, "llm": True}


def _clean_term(raw: str) -> str:
    """清洗 LLM 返回: 取首行、去引号/前后标点, 限长。"""
    if not raw:
        return ""
    line = raw.strip().splitlines()[0].strip()
    line = line.strip("\"'“”‘’` 。.，,").strip()
    return line[:50]


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
