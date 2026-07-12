# Spec Harness

This folder is the project harness: current product truth, roadmap state, task-specific design constraints, and reproducible acceptance gates.

## Minimal Startup Context

Normal agent startup reads only:

1. `AGENTS.md` - mandatory engineering contract and project map.
2. `.agent-bridge/BOARD.md` - current checkpoint, owners, blockers, and next gate.
3. `spec/roadmap-ledger.md` - roadmap IDs and status.
4. `spec/current-state.md` - implemented, partial, missing, and known limitations.

Do not load mail archives, the full changelog archive, completed roadmaps, build logs, or generated discovery reports during normal startup.

## Task Routing

| Task | Read |
|---|---|
| Current product sprint | `spec/roadmap-dual-mode-2026-07-09.md` |
| Product goal and architecture | `spec/project.md` |
| Development constraints | `spec/development.md` |
| Completion claim or release review | `spec/acceptance.md` |
| Auto-refresh, persistence, narrative signals, cognition marks, search concurrency | `spec/bug-audit-2026-07-05.md` |
| No-LLM capability boundary | `spec/local-capability-boundary.md` |
| Event/literature graph planning | `spec/event-tree-literature-graph-design.md` |
| Academic filtering | `spec/academic-filtering-design.md` |
| Discovery archive or cognition timeline | `spec/discovery-archive-cognition-timeline-design.md` |
| Browser control and OpenCLI boundary | `spec/browser-control-decision-2026-07-10.md` |
| AI controllability and multi-format source candidate | `spec/ai-collaboration-and-source-boundary-2026-07-12.md` |
| User feedback, reflections, developer observations, and external references | `spec/feedback-and-ideas/README.md` |
| Static knowledge publishing and inspectable reasoning references | `spec/feedback-and-ideas/references/knowledge-publishing-and-reasoning-reference-2026-07-12.md` |
| Broader future priorities | `spec/roadmap.md` |
| Recent documentation changes | `spec/CHANGELOG.md` |

## Historical Material

- Completed and superseded roadmaps: `spec/archive/roadmaps/` and `spec/archive/`.
- Full changelog through 2026-07-12: `spec/archive/changelog/CHANGELOG-through-2026-07-12.md`.
- Historical implementation plans: `spec/archive/plans/`.
- Historical backend build logs: `spec/archive/build-logs/`.
- External project references: `docs/references/`.
- Agent coordination history: `.agent-bridge/archive/` (local only).
- `backend/discovery_reports/` contains product data, not project documentation.

## What Counts As Done

A completion report must include changed files, commands and results, GitNexus risk evidence when symbols changed, and confirmation that real secrets/databases were not tracked or written. Exact gates live in `spec/acceptance.md`.

## Maintenance

- Give every executable roadmap a stable ID in `spec/roadmap-ledger.md`.
- Keep only one `CURRENT` product roadmap.
- Keep BOARD and live mailboxes current; archive history instead of appending forever.
- Keep `spec/CHANGELOG.md` as a short recent window and roll full history into `spec/archive/changelog/`.
- Do not silently delete historical decisions.
