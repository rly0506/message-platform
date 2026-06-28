"""Sonnet 综合 (强模型层): 把已富化的相关报道编织成专题档案。

拆成三次独立调用 (时间线 / 各方态度 / 批判分析)，原因:
- 单次产出全部内容输出过长，经不稳定代理时易超时或断连;
- 拆分后每次输出更短、更可靠，且单步失败不影响其余部分。
"""
from __future__ import annotations

from app import config, llm

MAX_ARTICLES = 100  # 送进综合的报道上限
RETRIES = 2

_SYSTEM = (
    "你是资深国际事件分析师。基于给定的多来源、多语种报道，"
    "编织出客观、可核查的专题档案。区分'事实'与'各方说法'，"
    "明确指出矛盾点、信息缺口与可能的立场偏差。只输出要求的格式。"
)

_JSON_RULE = (
    "只输出 JSON，不要 markdown 围栏外的任何文字。"
    "字符串内部如需引用/强调一律用中文引号「」，严禁英文双引号 \" (会破坏 JSON)。"
)


def _listing(rows: list[dict]) -> str:
    return "\n".join(
        f"[id={r['id']} | {r['date']} | {r['source']} | {r['lang']} | 立场:{r['stance']}] {r['title_zh']}"
        for r in rows
    )


def _call_json(prompt: str, max_tokens: int):
    last = ""
    for _ in range(RETRIES + 1):
        try:
            text = llm.chat(config.SYNTH_MODEL, prompt, max_tokens=max_tokens, system=_SYSTEM)
            return llm.extract_json(text)
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:80]}"
    raise RuntimeError(last)


def synth_timeline(name: str, desc: str, rows: list[dict]) -> list:
    prompt = f"""主题: {name}
说明: {desc or "(无)"}

基于以下报道，提炼事件演进时间线。{_JSON_RULE}
输出 JSON 数组，每个元素:
{{"date":"YYYY-MM-DD","title_zh":"节点标题","summary_zh":"该节点发生了什么(综合多源)","article_ids":[相关id]}}
要求: 合并同一节点的多篇报道，按日期升序，控制在 8~15 个关键节点。

报道:
{_listing(rows)}"""
    data = _call_json(prompt, 4000)
    return data if isinstance(data, list) else data.get("timeline", [])


def synth_framing(name: str, desc: str, rows: list[dict]) -> list:
    prompt = f"""主题: {name}
说明: {desc or "(无)"}

基于以下报道，对照各方/各家媒体如何报道 (谁强调什么、谁回避什么)。{_JSON_RULE}
输出 JSON 数组，每个元素:
{{"party":"媒体/阵营(可按来源国或立场归类)","stance":"总体立场","summary_zh":"该方如何报道、侧重什么","article_ids":[id]}}
要求: 做真正的对照，控制在 4~7 方。

报道:
{_listing(rows)}"""
    data = _call_json(prompt, 3000)
    return data if isinstance(data, list) else data.get("framing", [])


def synth_analysis(name: str, desc: str, timeline: list, framing: list) -> str:
    tl = "\n".join(f"- {e.get('date','?')} {e.get('title_zh','')}" for e in timeline)
    fr = "\n".join(f"- {f.get('party','')}[{f.get('stance','')}]: {f.get('summary_zh','')}" for f in framing)
    prompt = f"""主题: {name}
说明: {desc or "(无)"}

已整理的时间线:
{tl or "(空)"}

各方态度:
{fr or "(空)"}

请基于以上撰写批判性分析 (markdown, 600 字以内), 包含:
1) 事实共识  2) 各方分歧与矛盾点  3) 信息缺口/未被回答的问题  4) 需警惕的立场偏差。
要具体、可核查、不空泛。直接输出 markdown 文本 (不是 JSON)。"""
    return llm.chat(config.SYNTH_MODEL, prompt, max_tokens=2000, system=_SYSTEM)


def fallback_analysis(name: str, timeline: list, framing: list) -> str:
    top_events = "；".join(
        f"{event.get('date', '?')} {event.get('title_zh', '')}"
        for event in timeline[:5]
        if event.get("title_zh")
    ) or "暂无可用时间线节点"
    parties = "；".join(
        f"{item.get('party', '')}：{item.get('stance', '')}"
        for item in framing[:5]
        if item.get("party") or item.get("stance")
    ) or "暂无可用态度分组"
    return (
        f"## LLM 批判分析未返回有效正文\n\n"
        f"专题「{name}」已完成 LLM 时间线与各方态度综合，但批判分析正文为空。"
        f"以下为基于同一轮 LLM 综合结果生成的兜底摘要，供复核使用。\n\n"
        f"- 事实共识：当前可识别的主要节点包括：{top_events}。\n"
        f"- 各方分歧：当前可识别的报道阵营包括：{parties}。\n"
        f"- 信息缺口：需继续核对原始报道全文、官方文件、现场证据与时间戳，避免仅凭标题和摘要确认事实。\n"
        f"- 立场偏差：不同媒体可能按国家立场、市场利益或评论取向选择重点，阅读时应对照多来源。"
    )


def synthesize(topic_name: str, topic_desc: str, rows: list[dict]) -> dict:
    """编排三步综合。单步失败则该部分为空，不影响其余。"""
    rows = rows[:MAX_ARTICLES]
    out = {"timeline": [], "framing": [], "analysis_md": ""}

    try:
        out["timeline"] = synth_timeline(topic_name, topic_desc, rows)
        print(f"  · 时间线 {len(out['timeline'])} 节点")
    except Exception as e:
        print(f"  · 时间线失败: {e}")
    try:
        out["framing"] = synth_framing(topic_name, topic_desc, rows)
        print(f"  · 各方态度 {len(out['framing'])} 方")
    except Exception as e:
        print(f"  · 各方态度失败: {e}")
    try:
        out["analysis_md"] = synth_analysis(topic_name, topic_desc, out["timeline"], out["framing"])
        if not out["analysis_md"].strip():
            out["analysis_md"] = fallback_analysis(topic_name, out["timeline"], out["framing"])
        print(f"  · 批判分析 {len(out['analysis_md'])} 字")
    except Exception as e:
        print(f"  · 批判分析失败: {e}")
        out["analysis_md"] = fallback_analysis(topic_name, out["timeline"], out["framing"])
    return out
