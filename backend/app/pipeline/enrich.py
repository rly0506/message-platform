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

# 喂给 LLM 的单篇正文上限 (字符)。够判修辞结构, 又不把 token 撑爆。
BODY_CHARS = 1800


def _prompt(topic_name: str, topic_desc: str, items: list[dict]) -> str:
    def _one(it: dict) -> dict:
        obj = {"id": it["id"], "lang": it["lang"], "title": it["title"],
               "snippet": it["snippet"][:300]}
        body = (it.get("body") or "").strip()
        if body:
            obj["body"] = body[:BODY_CHARS]   # 抓到正文才带; 否则只有标题+摘要
        return obj

    listing = "\n".join(json.dumps(_one(it), ensure_ascii=False) for it in items)
    return f"""主题: {topic_name}
主题说明: {topic_desc or "(无)"}

下面是若干报道。有 body 字段的, 以 body (正文) 为准判断; 没有 body 的只有标题+摘要, 信息有限。
对每一篇，返回一个对象，字段:
- id: 原样回传
- relevant: 布尔, 是否真正与主题相关 (蹭关键词但实质无关 -> false)
- relevance: 0~1 的相关度
- title_zh: 标题的简洁中文翻译 (本就是中文则精炼即可)
- snippet_zh: 摘要的一句话中文概括 (无摘要可据标题推断, 不确定则留空)
- stance: 该篇相对主题的立场标签, 从 [中立, 乐观, 担忧, 批评, 支持, 官方表态, 行业视角] 选最贴切的一个
- stance_summary: 一句话说明该篇的角度/侧重 (中文, <=30字)
- substance_score: 0~100 的"干货密度"。判据钉死在一条: **一句话能否被证伪/查证**。
    高分(70+): 多为可证伪的具体事实——数字、时间、地点、具名引述、可查的事件。
    低分(30-): 多为不可证伪的空话——"将深刻重塑格局""未来已来""业内普遍认为""某种程度上"等模糊断言、情绪渲染、口号。
    有 body 则据正文判断; 只有标题/摘要时保守估计, 不确定给中间值 50。
- substance_note: 一句话说明打这个分的依据 (中文, <=30字, 让分数可追溯, 例: "含具体金额与时间" 或 "多为趋势空话无数据")
- emotion_score: 0~100 的"情绪操控强度"。判据: **这篇是否靠煽动情绪/修辞压力推动读者, 而非靠事实**。
    高分(70+): 大量情绪化措辞、恐吓/亢奋渲染、立场预设、"先带情绪后空泛", 事实占比低。
    低分(30-): 克制陈述、就事论事、让事实说话。
    **此项必须基于正文修辞结构判断**: 仅凭标题/摘要无法可靠判断整篇修辞 ->
    **没有 body 字段时一律返回 -1 (表示信息不足, 不评分)**, 不要硬猜。
- emotion_note: 一句话说明情绪评分依据 (中文, <=30字, 例: "通篇渲染恐慌少事实"); 返回 -1 时可留空

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
