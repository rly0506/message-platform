# Discovery Archive / Cognition Timeline Design

## Purpose

The discovery layer already writes multiple `frontier-*.md` and sidecar `frontier-*.json` reports into `backend/discovery_reports/`, but the frontend currently loads only `/api/discovery/latest`.

This design captures two user requests:

- show older `认知前沿日报`, not only the latest day;
- connect today's discovery seeds or events with previous days as a tree, so the user can see continuity instead of isolated daily snapshots.
- strengthen the no-LLM local experience so classification, collection, archive browsing, query, and evidence retrieval remain useful without generated synthesis.

## Product Goal

Help the user answer:

- What did earlier discovery reports contain?
- Which frontier seeds are new, repeated, accelerating, fading, or connected to previous events?
- How did a topic branch across days?
- Which branch is worth following next to broaden cognition?
- What can I still collect, classify, search, and review when LLM access is unavailable?

## Non-Goals

- Do not replace the event analysis desk.
- Do not claim causal roots between days unless evidence supports it.
- Do not require LLM for the core path.
- Do not add a vector database, graph database, queue system, or graph visualization library in V1.
- Do not turn the daily report into a social feed or infinite scroll.
- Do not hide the original daily markdown reports; archive access must preserve them.
- Do not make local mode feel like an error state. It should be a usable mode with clear evidence limits.

## Current State

Observed on 2026-07-02:

- backend report files exist under `backend/discovery_reports/`;
- examples include `frontier-20260702T135734Z.md/json`, `frontier-20260702T022816Z.md/json`, and older 2026-06-30 / 2026-06-29 reports;
- `backend/app/discovery/run.py` has `latest_report()` but no list/get-by-id API;
- `frontend/src/api/dossierApi.ts` exposes only `fetchLatestDiscovery()`;
- `frontend/src/composables/useDiscovery.ts` and `DiscoveryPanel.vue` display only the currently loaded report.

The first gap is therefore an interface/UX gap, not a storage gap.

## Local-First Operating Mode

The intelligence desk should work as a local evidence workbench before it becomes an LLM writing surface.

Local mode should support:

- **Collection**: run available media, academic, and community collectors; isolate platform failures; keep partial results.
- **Classification**: group seeds by `domain`, `domain_label`, source/domain, date, signal strength, and local keyword overlap.
- **Archive**: browse past frontier reports and their sidecar seeds without launching a new discovery job.
- **Query**: search or filter historical reports, seeds, tracked topics, sources, and cognition marks with local fields first.
- **Connection**: build cross-day branches from local similarity evidence before asking an LLM to explain them.
- **Evidence retrieval**: every local label or branch should link back to the seed, report date, source URL, or topic that produced it.

LLM mode may later improve wording, branch names, and cross-day summaries, but it must not be required to see the archive, run local classification, or follow evidence links.

### Local Mode Acceptance

- With no LLM key configured, the intelligence desk can still load the latest report, browse historical reports, show seeds, and display local classifications.
- A cross-day branch can be produced from local evidence alone when at least two reports share a domain, domain label, source domain, or normalized keyword.
- Collector failures appear as platform/source status, not as a blank product state.
- Local explanations use constrained wording such as `同领域连续出现`, `共享领域标签`, or `本地相似信号`.
- Local explanations do not claim `导致`, `根因`, `证明`, `操控`, or `事实核查完成`.

## V1: Discovery Report Archive

### Backend Shape

Add small read-only APIs:

- `GET /api/discovery/reports`
  - returns report metadata sorted newest first;
  - fields: `run_id`, `path` or stable `report_id`, `created_at`, `seed_count`, `has_markdown`, `has_sidecar`;
  - does not return full markdown for every report.
- `GET /api/discovery/reports/{run_id}`
  - returns the same shape as `/api/discovery/latest`: `markdown`, `seeds`, `run_id`, `path`;
  - rejects unsafe path traversal and only reads files matching the `frontier-*.md` naming pattern.

Keep `/api/discovery/latest` unchanged for compatibility.

### Frontend Shape

In `今日情报台`:

- add a compact date selector or archive strip near the report timestamp;
- default to latest report;
- allow switching to older reports without running a new discovery job;
- show an explicit label when viewing an older report, e.g. `历史日报`;
- keep cognition-boundary queue behavior tied to the selected report's seeds.

### Acceptance

- If `backend/discovery_reports/` contains three reports, the UI can show three selectable dates.
- Selecting an older date loads that report's markdown and seeds.
- Running `立即分析` still creates a new latest report and selects it after job completion.
- No real `backend/dossier.db` writes are needed for archive reads.

## V2: Cognition Timeline Tree

### Core Idea

Build a cross-day tree from discovery seeds and related tracked topics:

```text
认知时间树
  AI infrastructure
    2026-06-29 seed: CPO capacity bottleneck
    2026-06-30 seed: data-center power constraint
    2026-07-02 seed: model serving cost shift
  Energy / nuclear
    2026-06-30 seed: small modular reactor policy
    2026-07-02 seed: grid bottleneck
```

Each node should show:

- date / run id;
- seed title;
- domain or inferred topic;
- why it is connected to the parent;
- whether the connection is local heuristic or LLM-assisted;
- links back to the original daily report and, when available, related tracked topic.

### Local-First Linking

V1/V2 should start with local heuristics:

- exact or fuzzy URL/domain reuse;
- source + external id reuse from `discovery.db`;
- shared normalized keywords from seed title and `what/why`;
- shared `domain` field from `DiscoverySeed`;
- overlap with cognition profile domain keys;
- repeated or accelerating `signal` from `DiscoveryStore`.

Local links should be labeled as `本地相似信号`, not as causal relationships.

The tree should privilege continuity over cleverness:

- use stable local fields first;
- prefer fewer branches with clear evidence over many speculative branches;
- require at least two report dates before showing a branch;
- keep original report dates visible so the user can verify the sequence;
- allow `深入` to reuse the existing seed analysis path, but do not auto-run LLM.

### Optional LLM Enhancement

LLM may later improve:

- branch names;
- short explanations for why two seeds belong together;
- unresolved questions across several days;
- "what changed since the previous report" summaries.

LLM output must be optional and marked as an enhancement. If LLM fails, the local tree remains visible.

### UI Shape

Keep it text-first:

- default collapsed panel named `认知时间树`;
- group by domain/topic branch;
- show 3-5 most relevant cross-day branches first;
- each branch links to the source report dates;
- avoid canvas/graph layout in V1.

### Acceptance

- With at least two reports sharing a domain or keyword, the tree shows one cross-day branch.
- Each edge displays its evidence basis, e.g. `共享关键词: CPO, data center`.
- Edges do not use causal language such as `导致`, `根因`, or `证明`.
- Turning off LLM still shows the locally linked tree.

## Suggested Iteration Order

1. **Discovery archive V1**: list reports and select historical reports.
2. **Local mode polish**: make no-LLM archive browsing, seed classification, collector status, and local filtering feel intentional.
3. **Local cognition timeline tree V1**: build local cross-day branches from report sidecars and `discovery.db`.
4. **Local query layer**: search/filter reports and seeds by date, domain, source, keyword, and cognition mark.
5. **LLM-assisted branch explanation**: optional enhancement only after local links feel useful.
6. **Use cognition marks**: prioritize branches where the user marked `陌生` or `存疑`.

## Risks

- **False continuity**: similar words across days may not mean the same event. Mitigation: label links as similarity/evidence, not causality.
- **Archive overload**: showing too many reports can recreate the raw-feed problem. Mitigation: newest-first list, date filter, and collapsed branches.
- **LLM over-interpretation**: generated cross-day narratives may sound more certain than evidence allows. Mitigation: local evidence first and enhancement labels.
- **Path safety**: report-by-id API must not read arbitrary local files.
- **Local mode under-design**: if no-LLM mode is framed only as a fallback, the product will still feel broken without an LLM key. Mitigation: make local archive, local query, and local evidence links first-class UI surfaces.
