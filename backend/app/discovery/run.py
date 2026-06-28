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

import os
from datetime import datetime

from app.discovery import report, sources
from app.discovery.store import DiscoveryStore

# 日报落盘目录: backend/discovery_reports/
_BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.getenv("DISCOVERY_REPORTS_DIR") or os.path.join(_BACKEND, "discovery_reports")


def run_discovery(store: DiscoveryStore | None = None, items=None, run_id: str | None = None,
                  annotate: bool = False) -> str:
    """跑一轮发现, 返回 markdown 报告。

    参数可注入 (store / items / run_id), 便于测试与复用;
    默认走真实拉取 + 默认 db + 当前时间戳。
    annotate=True: 对种子做可选 LLM 二级分拣 (无 LLM 时自动降级, 不报错)。
    """
    own_store = store is None
    store = store or DiscoveryStore()
    try:
        run_id = run_id or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        has_history = store.run_count() > 0
        items = items if items is not None else sources.fetch_all()
        scored = store.score(items, run_id=run_id, now_iso=run_id)

        annotations = None
        if annotate and has_history:
            # 只标注种子档 (省钱), 且仅在有历史时 (首日只建基线无需标注)
            from app.discovery import annotate as annotate_mod
            from app.discovery.report import categorize
            seeds = [s for s in scored if categorize(s, has_history) == "seed"]
            annotations = annotate_mod.annotate_seeds(seeds)

        md = report.build_report(scored, run_id=run_id, has_history=has_history,
                                 annotations=annotations)
        store.commit_run(items, run_id=run_id, now_iso=run_id)
        return md
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


def main() -> None:
    run_id = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    md = run_discovery(run_id=run_id)
    path = _save_report(md, run_id)
    # Windows GBK 控制台可能打不出 emoji; 落盘是权威输出, stdout 仅作提示。
    try:
        print(md)
    except UnicodeEncodeError:
        print(md.encode("ascii", "replace").decode("ascii"))
    print(f"\n[报告已保存] {path}")


if __name__ == "__main__":
    main()
