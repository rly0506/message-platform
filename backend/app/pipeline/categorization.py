"""Report stance and category inference for local no-LLM analysis."""
from __future__ import annotations

from app.pipeline.term_match import term_hit

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

def infer_stance(title: str, snippet: str = "") -> str:
    text = f"{title} {snippet}"
    scores: dict[str, int] = {}
    for label, terms in STANCE_RULES:
        score = sum(1 for term in terms if term_hit(term, text))
        if score:
            scores[label] = score
    if not scores:
        return "中性观察"
    return max(scores.items(), key=lambda item: item[1])[0]
def infer_report_category(title: str, snippet: str = "") -> str:
    return _event_category(f"{title} {snippet}".strip())
def report_category_reason(category: str, title: str, snippet: str = "") -> str:
    return _event_category_reason(f"{title} {snippet}".strip(), category)
def _event_category(text: str) -> str:
    scores = {}
    for label, terms in CATEGORY_RULES:
        score = sum(1 for term in terms if term_hit(term, text))
        if score:
            scores[label] = score
    if not scores:
        return "行动进展"
    return max(scores.items(), key=lambda item: item[1])[0]
def _event_category_reason(text: str, category: str) -> str:
    terms = next((terms for label, terms in CATEGORY_RULES if label == category), ())
    matched = [term for term in terms if term_hit(term, text)]
    if matched:
        return "命中阶段词：" + "、".join(matched[:6])
    return "未命中明确阶段词，归为一般进展报道"
