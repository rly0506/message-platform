"""发现层入口 —— 串起 拉取 -> 打分 -> 报告 -> 提交快照。

用法 (项目虚拟环境):
    venv\\Scripts\\python.exe -m app.discovery.run

每次运行:
1. 从注意力前沿拉取 (HN + arXiv)
2. 对照历史快照打分 (加速 / 全新)
3. 渲染当日报告
4. 把本次快照写入 discovery.db (成为明天的"昨天")

首次运行只建基线; 次日起报告才有加速信号。
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from app.discovery import report, sources
from app.discovery.store import DiscoveryStore

# 日报落盘目录: backend/discovery_reports/
_BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.getenv("DISCOVERY_REPORTS_DIR") or os.path.join(_BACKEND, "discovery_reports")


def run_discovery(store: DiscoveryStore | None = None, items=None, run_id: str | None = None,
                  annotate: bool = False) -> dict:
    """跑一轮发现, 返回 {markdown, seeds}。

    参数可注入 (store / items / run_id), 便于测试与复用;
    默认走真实拉取 + 默认 db + 当前时间戳。
    annotate=True: 对种子做可选 LLM 二级分拣 (无 LLM 时自动降级, 不报错)。

    seeds: 结构化 A 档种子列表 (供前端"点种子->深入分析"闭环);
           首次/基线运行无加速信号 -> seeds 为 []。
    """
    own_store = store is None
    store = store or DiscoveryStore()
    try:
        run_id = run_id or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        has_history = store.run_count() > 0
        items = items if items is not None else sources.fetch_all()
        scored = store.score(items, run_id=run_id, now_iso=run_id)

        annotations = None
        synthesis = ""
        if annotate and has_history:
            # 只标注种子档 (省钱), 且仅在有历史时 (首日只建基线无需标注)
            from app.discovery import annotate as annotate_mod
            from app.discovery.report import categorize
            seed_items = [s for s in scored if categorize(s, has_history) == "seed"]
            annotations = annotate_mod.annotate_seeds(seed_items)
            # 综述: 把种子编织成一篇有叙事的导读 (无 LLM -> 返回 "", 优雅降级)
            synthesis = annotate_mod.synthesize_frontier(seed_items, annotations)

        md = report.build_report(scored, run_id=run_id, has_history=has_history,
                                 annotations=annotations, synthesis=synthesis)
        seeds = report.collect_seeds(scored, has_history=has_history, annotations=annotations)
        store.commit_run(items, run_id=run_id, now_iso=run_id)
        return {"markdown": md, "seeds": seeds}
    finally:
        if own_store:
            store.close()


def _save_report(md: str, run_id: str) -> str:
    """把日报写到 discovery_reports/ (UTF-8), 返回文件路径。"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    safe = run_id.replace(":", "").replace("-", "")
    path = os.path.join(REPORTS_DIR, f"frontier-{safe}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def _seeds_path_for(md_path: str) -> str:
    """报告 .md 的同名 sidecar .json 路径 (存结构化种子)。"""
    return md_path[: -len(".md")] + ".json" if md_path.endswith(".md") else md_path + ".json"


def _save_seeds(seeds: list, md_path: str) -> str:
    """把结构化种子写到与 .md 同名的 .json sidecar, 返回其路径。

    与 markdown 报告并存: markdown 给人读, json 给前端做"点种子"闭环。
    """
    path = _seeds_path_for(md_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False)
    return path


def run_and_save(annotate: bool = False, on_step=None) -> dict:
    """跑一轮发现并落盘, 返回结构化结果 (供 API job 复用)。

    on_step(key, status): 可选进度回调 (JobRunner.on_step 形状), 用于前端步骤展示。
    返回 {markdown, seeds, run_id, path, annotated} —— job result 与 /latest 共用此形状。
    """
    def step(key: str, status: str) -> None:
        if on_step is not None:
            on_step(key, status)

    run_id = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    step("fetch", "running")
    result = run_discovery(run_id=run_id, annotate=annotate)
    md, seeds = result["markdown"], result["seeds"]
    step("fetch", "done")
    step("persist", "running")
    path = _save_report(md, run_id)
    _save_seeds(seeds, path)
    step("persist", "done")
    return {"markdown": md, "seeds": seeds, "run_id": run_id, "path": path, "annotated": annotate}


def latest_report() -> dict | None:
    """读 discovery_reports/ 里最新一份报告。

    ISO 命名 = 字典序即时间序, 取末尾即最新。
    命令行 / 定时任务跑出的报告也落在同一目录, 故前端能统一看到。
    一并读同名 .json sidecar 拿结构化种子 (老报告无 sidecar -> seeds=[])。
    无报告时返回 None。
    """
    if not os.path.isdir(REPORTS_DIR):
        return None
    files = sorted(f for f in os.listdir(REPORTS_DIR) if f.startswith("frontier-") and f.endswith(".md"))
    if not files:
        return None
    name = files[-1]
    path = os.path.join(REPORTS_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        md = f.read()
    seeds: list = []
    seeds_path = _seeds_path_for(path)
    if os.path.exists(seeds_path):
        try:
            with open(seeds_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                seeds = loaded
        except (json.JSONDecodeError, OSError):
            seeds = []  # sidecar 损坏 -> 退回空种子, 报告照常显示
    # 文件名形如 frontier-20260628T123000Z.md -> 抽回 run_id 标识
    run_id = name[len("frontier-"):-len(".md")]
    return {"markdown": md, "seeds": seeds, "run_id": run_id, "path": path}


def main() -> None:
    result = run_and_save()
    md = result["markdown"]
    # Windows GBK 控制台可能打不出 emoji; 落盘是权威输出, stdout 仅作提示。
    try:
        print(md)
    except UnicodeEncodeError:
        print(md.encode("ascii", "replace").decode("ascii"))
    print(f"\n[报告已保存] {result['path']}  (种子 {len(result['seeds'])} 条)")


if __name__ == "__main__":
    main()
