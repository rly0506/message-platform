# Spec Harness

This folder is the project harness: the shared map, rules, and acceptance gates used by coding agents and reviewers.

## How To Use

Read in this order:

1. `.agent-bridge/BOARD.md` for the single current truth: current goal, latest commit, who does what next.
2. `AGENTS.md` for the workspace map and GitNexus rules.
3. `spec/roadmap-event-graph-2026-07-09.md` for the CURRENT sprint: evidence-first event graph (V1 within-topic, V2 cross-topic).
4. `spec/project.md` for the product goal and architecture.
5. `spec/current-state.md` for prior project truth and completed work (being refreshed each major iteration).
6. `spec/bug-audit-2026-07-05.md` before touching auto-refresh, persistence, narrative signals, discovery cognition marks, or search-job concurrency.
7. `spec/development.md` for development constraints.
8. `spec/acceptance.md` before claiming work is complete.
9. `spec/roadmap.md` for the broader product direction (design-first backlog).
10. `spec/local-capability-boundary.md` to understand what works without LLM access.
11. `spec/event-tree-literature-graph-design.md` before planning event-tree or academic graph work (the understanding-layer boundary).
12. `spec/academic-filtering-design.md` when working on the academic layer filtering iteration.
13. `spec/discovery-archive-cognition-timeline-design.md` before planning discovery history or cross-day cognition-tree work.
14. `spec/CHANGELOG.md` to understand recent spec changes.
15. Historical sprint snapshots (14-point ledgers, dated audits, superseded roadmaps) are archived under `spec/archive/`.

## What Counts As Done

A change is not done until the final report includes reproducible evidence:

- changed files
- commands run
- exit codes or pass counts
- GitNexus risk summary when code symbols changed
- confirmation that `backend/.env` and `backend/dossier.db` were not tracked or written

## Document Scope

Keep this folder small. Add a new subdocument only when one of these files becomes hard to scan or a repeated workflow needs its own checklist.

## Maintenance

When changing `AGENTS.md` or any file in `spec/`, append a dated entry to `spec/CHANGELOG.md` with:

- date
- changed files
- reason
- verification evidence
