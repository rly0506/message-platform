"""Discovery runner: fetch items, score them, render reports, and archive them."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

from app.discovery import report, sources
from app.discovery.store import DiscoveryStore

_BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.getenv("DISCOVERY_REPORTS_DIR") or os.path.join(_BACKEND, "discovery_reports")
_RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z$")
_FORBIDDEN_TREE_WORDS = ("\u5bfc\u81f4", "\u6839\u56e0", "\u8bc1\u660e", "\u56e0\u679c")


def run_discovery(store: DiscoveryStore | None = None, items=None, run_id: str | None = None,
                  annotate: bool = False) -> dict:
    """Run one discovery pass and return rendered markdown plus structured seeds."""
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
            from app.discovery import annotate as annotate_mod
            from app.discovery.report import categorize

            seed_items = [s for s in scored if categorize(s, has_history) == "seed"]
            annotations = annotate_mod.annotate_seeds(seed_items)
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
    """Archive a markdown report and return its path."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    safe = run_id.replace(":", "").replace("-", "")
    path = os.path.join(REPORTS_DIR, f"frontier-{safe}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def _seeds_path_for(md_path: str) -> str:
    return md_path[: -len(".md")] + ".json" if md_path.endswith(".md") else md_path + ".json"


def _safe_run_id_from_name(name: str) -> str:
    return name[len("frontier-"):-len(".md")]


def _report_filename(run_id: str) -> str | None:
    if not _RUN_ID_RE.match(run_id):
        return None
    return f"frontier-{run_id}.md"


def _report_files() -> list[str]:
    if not os.path.isdir(REPORTS_DIR):
        return []
    return sorted(
        name for name in os.listdir(REPORTS_DIR)
        if name.startswith("frontier-")
        and name.endswith(".md")
        and _RUN_ID_RE.match(_safe_run_id_from_name(name))
    )


def _load_seeds(md_path: str) -> list:
    seeds_path = _seeds_path_for(md_path)
    if not os.path.exists(seeds_path):
        return []
    try:
        with open(seeds_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        return loaded if isinstance(loaded, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def list_reports() -> list[dict]:
    """Return archived discovery report metadata, newest first."""
    reports: list[dict] = []
    for name in reversed(_report_files()):
        path = os.path.join(REPORTS_DIR, name)
        run_id = _safe_run_id_from_name(name)
        reports.append({
            "run_id": run_id,
            "created_at": run_id,
            "seed_count": len(_load_seeds(path)),
            "has_sidecar": os.path.exists(_seeds_path_for(path)),
        })
    return reports


def report_by_run_id(run_id: str) -> dict | None:
    """Read one archived report by safe run_id."""
    name = _report_filename(run_id)
    if name is None:
        return None
    reports_dir = os.path.abspath(REPORTS_DIR)
    path = os.path.abspath(os.path.join(reports_dir, name))
    if os.path.commonpath([reports_dir, path]) != reports_dir:
        return None
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        md = f.read()
    return {"markdown": md, "seeds": _load_seeds(path), "run_id": run_id, "path": path}


def _tree_item(seed: dict, run_id: str, domain: str) -> dict:
    return {
        "run_id": run_id,
        "title": str(seed.get("title") or ""),
        "url": str(seed.get("url") or ""),
        "domain": domain,
        "domain_label": str(seed.get("domain_label") or domain),
        "signal": seed.get("signal") or 0,
        "delta": seed.get("delta") or 0,
        "why": str(seed.get("why") or ""),
    }


def _choose_tree_items(items: list[dict], limit: int = 5) -> list[dict]:
    def score(item: dict) -> tuple[float, float]:
        return (float(item.get("signal") or 0), float(item.get("delta") or 0))

    by_run: dict[str, list[dict]] = {}
    for item in items:
        by_run.setdefault(str(item.get("run_id") or ""), []).append(item)
    for run_items in by_run.values():
        run_items.sort(key=score, reverse=True)

    selected: list[dict] = []
    for run_id in sorted(by_run, reverse=True):
        if len(selected) >= limit:
            break
        selected.append(by_run[run_id][0])

    remaining = [
        item
        for run_items in by_run.values()
        for item in run_items
        if item not in selected
    ]
    remaining.sort(key=score, reverse=True)
    selected.extend(remaining[: max(0, limit - len(selected))])
    return selected[:limit]


def timeline_tree() -> dict:
    """Build local cross-report branches from archived discovery seeds."""
    grouped: dict[str, dict] = {}
    for meta in reversed(list_reports()):
        payload = report_by_run_id(meta["run_id"])
        if not payload:
            continue
        for seed in payload.get("seeds", []):
            if not isinstance(seed, dict):
                continue
            domain = str(seed.get("domain") or seed.get("domain_label") or "").strip()
            if not domain:
                continue
            branch = grouped.setdefault(domain, {
                "branch_key": domain,
                "label": str(seed.get("domain_label") or domain),
                "evidence_basis": "\u540c\u9886\u57df\u8fde\u7eed\u51fa\u73b0",
                "connection_kind": "local_similarity",
                "_items": [],
                "_runs": set(),
            })
            branch["_runs"].add(meta["run_id"])
            branch["_items"].append(_tree_item(seed, meta["run_id"], domain))

    branches: list[dict] = []
    for branch in grouped.values():
        if len(branch["_runs"]) < 2:
            continue
        clean = {
            "branch_key": branch["branch_key"],
            "label": branch["label"],
            "evidence_basis": branch["evidence_basis"],
            "connection_kind": branch["connection_kind"],
            "items": _choose_tree_items(branch["_items"]),
        }
        serialized = json.dumps(clean, ensure_ascii=False)
        if any(word in serialized for word in _FORBIDDEN_TREE_WORDS):
            continue
        branches.append(clean)
    branches.sort(key=lambda item: (-len({row["run_id"] for row in item["items"]}), -len(item["items"]), item["label"]))
    return {"branches": branches[:5]}


def _save_seeds(seeds: list, md_path: str) -> str:
    """Archive the structured seed sidecar next to a markdown report."""
    path = _seeds_path_for(md_path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False)
    return path


def run_and_save(annotate: bool = False, on_step=None) -> dict:
    """Run discovery, archive markdown and sidecar JSON, and return API payload."""
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
    """Read the newest archived discovery report, if any."""
    files = _report_files()
    if not files:
        return None
    return report_by_run_id(_safe_run_id_from_name(files[-1]))


def main() -> None:
    result = run_and_save()
    md = result["markdown"]
    try:
        print(md)
    except UnicodeEncodeError:
        print(md.encode("ascii", "replace").decode("ascii"))
    print(f"\n[report saved] {result['path']}  (seeds {len(result['seeds'])})")


if __name__ == "__main__":
    main()
