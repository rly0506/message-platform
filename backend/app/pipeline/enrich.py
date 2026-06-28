"""Haiku 批量富化 (便宜层): 相关性确认 + 译中 + 单篇立场。

为省成本与往返: 多篇打包进一次调用，要求模型返回 JSON 数组。
已富化的文章 (Article.enriched / TopicArticle.stance 已填) 不再重复处理。
"""
from __future__ import annotations

import json

from app import config, llm

BATCH = 6           # 每次 LLM 调用处理的文章数 (小批降低截断/解析失败)
MAX_TOKENS = 4096   # 输出上限, 留足中文翻译空间
RETRIES = 3         # 解析失败时重试次数 (代理偶发返回截断/非JSON)

_SYSTEM = (
    "你是国际新闻分析助手。判断每篇报道是否真正与给定主题相关，"
    "把标题/摘要翻成简洁中文，并概括该篇相对主题体现的立场。"
    "只输出 JSON，不要任何解释或 markdown 围栏。"
)


def _prompt(topic_name: str, topic_desc: str, items: list[dict]) -> str:
    listing = "\n".join(
        json.dumps({"id": it["id"], "lang": it["lang"], "title": it["title"],
                    "snippet": it["snippet"][:300]}, ensure_ascii=False)
        for it in items
    )
    return f"""主题: {topic_name}
主题说明: {topic_desc or "(无)"}

下面是若干报道。对每一篇，返回一个对象，字段:
- id: 原样回传
- relevant: 布尔, 是否真正与主题相关 (蹭关键词但实质无关 -> false)
- relevance: 0~1 的相关度
- title_zh: 标题的简洁中文翻译 (本就是中文则精炼即可)
- snippet_zh: 摘要的一句话中文概括 (无摘要可据标题推断, 不确定则留空)
- stance: 该篇相对主题的立场标签, 从 [中立, 乐观, 担忧, 批评, 支持, 官方表态, 行业视角] 选最贴切的一个
- stance_summary: 一句话说明该篇的角度/侧重 (中文, <=30字)

报道列表 (每行一个 JSON):
{listing}

输出: 一个 JSON 数组, 每篇一个对象, 顺序不限但 id 必须对应。"""


def enrich_batch(topic_name: str, topic_desc: str, items: list[dict]) -> dict[int, dict]:
    """处理一批, 返回 {id: 富化结果}。解析失败会重试; 最终失败返回空 dict。"""
    prompt = _prompt(topic_name, topic_desc, items)
    last_err = ""
    for _ in range(RETRIES):
        try:
            text = llm.chat(config.HAIKU_MODEL, prompt, max_tokens=MAX_TOKENS, system=_SYSTEM)
            data = llm.extract_json(text)
        except Exception as e:  # 解析失败或网络/代理错误
            last_err = f"{type(e).__name__}: {str(e)[:80]}"
            continue
        out: dict[int, dict] = {}
        for obj in data if isinstance(data, list) else []:
            try:
                out[int(obj["id"])] = obj
            except (KeyError, ValueError, TypeError):
                continue
        if out:
            return out
        last_err = "解析得到空结果"
    print(f"    (batch 富化失败, 已重试 {RETRIES} 次: {last_err})")
    return {}
