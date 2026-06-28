"""发现层分类 + 报告 —— 把加速判定翻译成人能读的"认知前沿日报"。

分类三档 (验证样张里固化下来的):
- seed   种子: 在加速 / 全新出现, 但还没出圈 —— 你最想要的"认知之外但在长"
- mainstream 已出圈: 信号已经很大 —— 看到时已经迟了, 折叠为背景
- noise  噪声: 低信号且没在涨 —— 应被过滤

全部启发式, 不调 LLM (核心链路无模型额度也能跑)。
LLM 分拣 (给每条标一句"这是什么/为何重要") 可作后续可选增强。

诚实边界: "加速"需要历史基线才能算。首次运行没有昨天的快照,
所有项都 is_new、delta 无意义 —— 此时只能建基线, 报告会明确标注。
"""
from __future__ import annotations

from app.discovery.store import ScoredItem
from app.discovery.annotate import Annotation

# --- 启发式阈值 (可调) ---
# HN points 高于此 = 已出圈 (主流已大量关注, 你看到就迟了)
MAINSTREAM_SIGNAL = 400
# HN 新出现项至少要有这么多 points 才算"带初速度的苗头" (滤掉刚发的零散贴)
NEW_SEED_MIN_SIGNAL = 30
# 两次运行间 signal 增量高于此 = 在加速 (从低基数在长)
RISE_DELTA_MIN = 25
# 新鲜窗口 (小时): 首次出现在此窗口内 = 仍算"今天的新苗头",
# 与被轮询了几次无关。这是关键修复: 同一天重跑不该把今天的种子冲成噪声。
FRESH_HOURS = 36

# 领域桶的中文标签 (报告分组用)
_DOMAIN_LABELS = {
    "tech": "🔬 科技 / AI",
    "finance": "💰 金融 / 经济",
    "geopolitics": "🌍 地缘 / 政治",
    "science": "🧬 科学",
    "society": "👥 社会 / 思潮",
    "other": "其它",
}


def _is_fresh(scored: ScoredItem) -> bool:
    """是否仍在新鲜窗口内 = 算"今天的新苗头"。

    有 age_hours (真实 ISO 时间) -> 按窗口判定, 与轮询几次无关。
    无 age_hours (测试用非 ISO run_id) -> 降级到 is_new (保持旧测试语义)。
    """
    if scored.age_hours is not None:
        return scored.age_hours <= FRESH_HOURS
    return scored.is_new


def categorize(scored: ScoredItem, has_history: bool) -> str:
    """给一条 ScoredItem 定档: seed / mainstream / noise。

    has_history=False (首次运行): 无法判定加速, 一律归 baseline 处理 (见 build_report)。

    关键: 种子 = "新鲜"(首见在窗口内) 或 "在加速"。不再因"被轮询过一次"
    就把今天的苗头打成噪声 —— 那是早期 bug, 同一天重跑会冲光所有种子。

    源分级 (tier): 大众媒体 (mass, 如 MIT Tech Review) 发出来就是给所有人看的 = 已出圈,
    "新鲜"不再等于"认知之外", 故不能仅凭新鲜进种子档 —— 这修掉了"大众媒体当日新闻
    污染 A 档"的 bug。小众/领先源 (niche, 默认: arXiv/智库/央行/HN) 保持原判定。
    """
    it = scored.item
    fresh = _is_fresh(scored)

    # 大众媒体 (mass): 当日新闻 = 已出圈。新鲜的归 mainstream, 旧的归 noise。
    # 唯一破例: 真加速 (delta 超阈值, 从低基数往上拐) 仍算种子
    # —— 但 RSS 大众源 signal=0、delta 恒为 0, 故实际只会落在 mainstream/noise。
    if it.tier == "mass":
        if scored.delta >= RISE_DELTA_MIN:
            return "seed"
        return "mainstream" if fresh else "noise"

    # arXiv / RSS 无投票信号: "新鲜出现的一条"本身就是早期信号
    if it.source == "arxiv" or it.signal == 0:
        return "seed" if fresh else "noise"

    # HN: 信号已很大 = 已出圈
    if it.signal >= MAINSTREAM_SIGNAL:
        return "mainstream"

    # 在加速 (从低基数往上拐) = 种子, 无论新旧
    if scored.delta >= RISE_DELTA_MIN:
        return "seed"

    # 新鲜且带一定初速度 = 苗头
    if fresh:
        return "seed" if it.signal >= NEW_SEED_MIN_SIGNAL else "noise"

    return "noise"


def build_report(scored: list[ScoredItem], run_id: str, has_history: bool,
                 annotations: dict | None = None, synthesis: str = "") -> str:
    """渲染 markdown 认知前沿日报。

    has_history=False: 首次运行 = 只建基线, 报告说明"明天起才有加速信号"。
    annotations: 可选 {external_id: Annotation}, 有则在种子下渲染 LLM 解读。
    synthesis: 可选 LLM 综述正文 (markdown), 有则放在报告顶部当导读;
               空字符串 -> 不出综述段 (无 LLM / 首日基线时的优雅降级)。
    """
    annotations = annotations or {}
    lines: list[str] = []
    lines.append(f"# 认知前沿日报 · {run_id}")
    lines.append("")
    lines.append(f"源: Hacker News front_page + arXiv ({', '.join(sorted({s.item.category for s in scored if s.item.category}))})")
    lines.append(f"本次拉取 {len(scored)} 条。")
    lines.append("")

    if synthesis.strip():
        lines.append("## 📰 前沿综述")
        lines.append("")
        lines.append(synthesis.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    if not has_history:
        lines.append("> ⚠️ **首次运行 = 仅建立基线。** 发现系统靠'今天 vs 昨天'算加速,")
        lines.append("> 现在还没有昨天的快照, 无法判定哪条在'从低基数在长'。")
        lines.append("> 快照已存入 discovery.db; **明天起**再次运行才会显示加速信号。")
        lines.append("")
        lines.append("## 本次基线快照 (按当前信号排序)")
        lines.append("")
        for s in sorted(scored, key=lambda x: x.item.signal, reverse=True):
            lines.append(_render_line(s, show_delta=False))
        lines.append("")
        return "\n".join(lines)

    # 有历史: 真正分档
    buckets: dict[str, list[ScoredItem]] = {"seed": [], "mainstream": [], "noise": []}
    for s in scored:
        buckets[categorize(s, has_history)].append(s)

    seeds = sorted(buckets["seed"], key=_seed_sort_key, reverse=True)
    lines.append(f"## A. 种子 —— 在加速 / 全新冒头, 还没出圈 ({len(seeds)} 条)")
    lines.append("")
    lines.append("*这是你最该看的一档: 认知之外、但在长的东西。*")
    lines.append("")
    if seeds:
        # 按领域分组, 让非技术圈的种子 (金融/地缘/...) 不被技术圈淹没
        by_domain: dict[str, list[ScoredItem]] = {}
        for s in seeds:
            by_domain.setdefault(s.item.domain or "other", []).append(s)
        for domain in sorted(by_domain):
            label = _DOMAIN_LABELS.get(domain, domain)
            lines.append(f"### {label} ({len(by_domain[domain])})")
            for s in by_domain[domain]:
                lines.append(_render_line(s, show_delta=True))
                ann = annotations.get(s.item.external_id)
                if ann is not None and (ann.what or ann.why):
                    niche = "🌱 还在小圈子" if ann.still_niche else "已出圈"
                    detail = " ".join(p for p in [ann.what, f"— {ann.why}" if ann.why else ""] if p)
                    lines.append(f"  > {detail} _({niche})_")
            lines.append("")
    else:
        lines.append("(本次无新种子)")
        lines.append("")

    mainstream = sorted(buckets["mainstream"], key=lambda x: x.item.signal, reverse=True)
    lines.append(f"## B. 已出圈 —— 看到时已经迟了 ({len(mainstream)} 条, 折叠)")
    lines.append("")
    for s in mainstream:
        lines.append(_render_line(s, show_delta=True))
    lines.append("")

    lines.append(f"## C. 噪声 —— 低信号且未加速 ({len(buckets['noise'])} 条, 已过滤)")
    lines.append("")
    lines.append(f"*已折叠 {len(buckets['noise'])} 条, 不展开。*")
    lines.append("")

    return "\n".join(lines)


def _seed_sort_key(s: ScoredItem) -> tuple:
    """种子排序: 优先加速量大的, 其次全新的, 再次持续被见的。"""
    return (s.delta, 1 if s.is_new else 0, s.runs_seen)


def collect_seeds(scored: list[ScoredItem], has_history: bool,
                  annotations: dict | None = None) -> list[dict]:
    """抽出结构化的种子列表 (A 档), 供前端做"点种子->深入分析"闭环。

    与 build_report 的 A 档同源: 同样的 categorize 判档、同样的排序。
    但这里返回结构化 dict (而非 markdown 字符串), 让单条种子可被前端点击。

    has_history=False (首次/基线): 无加速信号 -> 无种子, 返回 []。
    annotations: 可选 {external_id: Annotation}, 有则把 what/why/still_niche 一并带出。
    """
    if not has_history:
        return []
    annotations = annotations or {}
    seeds = sorted(
        (s for s in scored if categorize(s, has_history) == "seed"),
        key=_seed_sort_key,
        reverse=True,
    )
    out: list[dict] = []
    for s in seeds:
        it = s.item
        domain = it.domain or "other"
        ann = annotations.get(it.external_id)
        out.append({
            "title": it.title,
            "url": it.url,
            "domain": domain,
            "domain_label": _DOMAIN_LABELS.get(domain, domain),
            "signal": it.signal,
            "delta": s.delta,
            "is_new": s.is_new,
            "what": ann.what if ann else "",
            "why": ann.why if ann else "",
            "still_niche": ann.still_niche if ann else True,
        })
    return out


def _render_line(s: ScoredItem, show_delta: bool) -> str:
    it = s.item
    tag = "🆕" if s.is_new else ""
    sig = f"{it.signal}pts" if it.source == "hackernews" else it.category
    parts = [f"- {tag}**{it.title}**", f"({sig}"]
    if show_delta and not s.is_new and s.delta != 0:
        arrow = "↑" if s.delta > 0 else "↓"
        parts.append(f", {arrow}{abs(s.delta)}")
    parts.append(f") {it.url}")
    return " ".join(p for p in parts if p)
