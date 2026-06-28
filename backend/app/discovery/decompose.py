"""把一个宏观/单薄的事件主题拆成可深挖的相关线索 (可选 LLM 增强)。

解决工作台的一个核心空缺: 你给一个宽词 (如"中国政府债务"), 系统过去只会
原样去搜, 不帮你拆成"中央债/地方债/化债"这些可深挖的角度。

一次 LLM 调用同时产出两组方向, 两组用途不同:
  subtopics —— 同一事件的更细切面 (中央债/地方债/化债)。
               可并进当前专题撒网采集 (采得更厚), 也供前端"下钻"点击。
  analogues —— 历史上的相似先例 (2008/1997/2020 金融危机)。
               绝不并进当前专题 (否则旧闻污染本档案), 仅供前端点击开新搜索。

严守发现层红线: 这是**可选增强**, 不是核心链路。
- 没配 LLM key / 调用失败 / 解析失败 -> 返回空结果, 搜索退回原 query_variants 行为, 绝不报错。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app import config


@dataclass
class Decomposition:
    """一个主题的拆解结果。"""
    subtopics: list[str] = field(default_factory=list)  # 下钻: 更细切面
    analogues: list[str] = field(default_factory=list)  # 历史: 相似先例

    @property
    def is_empty(self) -> bool:
        return not self.subtopics and not self.analogues


def decompose_topic(query: str, model: str = "") -> Decomposition:
    """把主题拆成 {subtopics, analogues}。

    无 LLM / 失败 / 空主题 -> 返回空 Decomposition (调用方据此退回原行为, 不报错)。
    """
    query = (query or "").strip()
    if not query:
        return Decomposition()
    if not config.LLM_API_KEY:
        return Decomposition()

    try:
        from app import llm
    except Exception:
        return Decomposition()

    target_model = model or config.HAIKU_MODEL
    prompt = _build_prompt(query)
    try:
        raw = llm.chat(
            target_model,
            prompt,
            max_tokens=400,
            system=(
                "你是事件研究助手。给你一个研究主题, 你要把它拆成可深挖的更细切面, "
                "并列出历史上的相似先例。只输出 JSON, 不要多余文字。"
            ),
        )
        data = llm.extract_json(raw)
    except Exception:
        return Decomposition()  # 网关超时 / 解析失败 -> 降级

    if not isinstance(data, dict):
        return Decomposition()
    return Decomposition(
        subtopics=_clean_list(data.get("subtopics")),
        analogues=_clean_list(data.get("analogues")),
    )


def _build_prompt(query: str) -> str:
    return (
        f"研究主题: {query}\n\n"
        "请输出一个 JSON 对象, 两个字段:\n"
        '  subtopics: 这个主题向下深挖的更细切面 (数组, 5 个), 每个是一个简短可检索的话题词。\n'
        '             例: 主题"中国政府债务" -> ["中央政府债务", "地方政府债务", "化债 隐性债务", "城投债 风险", "专项债 发行"]。\n'
        '  analogues: 历史上的相似事件/先例 (数组, 3-5 个), 每个是一个可检索的具体事件名。\n'
        '             例: 主题"硅谷银行倒闭" -> ["2008 雷曼兄弟破产", "1997 亚洲金融危机", "2023 瑞信危机"]。\n'
        "要求: 话题词简短具体 (2-8 字/词), 语言跟随主题最可能的新闻语种; "
        "subtopics 必须是同一主题的细分, analogues 必须是不同时间的类似事件; 只输出 JSON。"
    )


def _clean_list(value: object, limit: int = 8) -> list[str]:
    """清洗 LLM 返回的数组: 去空、去重、限长、限量。"""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        term = str(item).strip().strip("\"'“”‘’`")[:50]
        if not term or term in seen:
            continue
        seen.add(term)
        out.append(term)
        if len(out) >= limit:
            break
    return out
