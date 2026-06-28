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

# --- 启发式阈值 (可调) ---
# HN points 高于此 = 已出圈 (主流已大量关注, 你看到就迟了)
MAINSTREAM_SIGNAL = 400
# HN 新出现项至少要有这么多 points 才算"带初速度的苗头" (滤掉刚发的零散贴)
NEW_SEED_MIN_SIGNAL = 30
# 两次运行间 signal 增量高于此 = 在加速 (从低基数在长)
RISE_DELTA_MIN = 25


def categorize(scored: ScoredItem, has_history: bool) -> str:
    """给一条 ScoredItem 定档: seed / mainstream / noise。

    has_history=False (首次运行): 无法判定加速, 一律归 baseline 处理 (见 build_report)。
    """
    it = scored.item

    # arXiv 无投票信号: "新出现的一篇论文"本身就是早期信号 -> 全新即种子
    if it.source == "arxiv":
        return "seed" if scored.is_new else "noise"

    # HN: 用 points (signal) + 加速 (delta) 判定
    if it.signal >= MAINSTREAM_SIGNAL:
        return "mainstream"

    if scored.is_new:
        # 全新出现且已带一定初速度 = 苗头
        return "seed" if it.signal >= NEW_SEED_MIN_SIGNAL else "noise"

    # 见过的项: 看它是否在加速 (从低基数往上拐)
    if scored.delta >= RISE_DELTA_MIN:
        return "seed"
    return "noise"


def build_report(scored: list[ScoredItem], run_id: str, has_history: bool) -> str:
    """渲染 markdown 认知前沿日报。

    has_history=False: 首次运行 = 只建基线, 报告说明"明天起才有加速信号"。
    """
    lines: list[str] = []
    lines.append(f"# 认知前沿日报 · {run_id}")
    lines.append("")
    lines.append(f"源: Hacker News front_page + arXiv ({', '.join(sorted({s.item.category for s in scored if s.item.category}))})")
    lines.append(f"本次拉取 {len(scored)} 条。")
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
        for s in seeds:
            lines.append(_render_line(s, show_delta=True))
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
