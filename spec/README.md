# Spec Harness

This folder is the project harness: the shared map, rules, and acceptance gates used by coding agents and reviewers.

## How To Use

Read in this order:

1. `AGENTS.md` for the workspace map and GitNexus rules.
2. `spec/current-state.md` for the latest project truth, completed work, gaps, and next candidates.
3. `spec/14-point-acceptance-2026-07-04.md` for the active 14-point sprint acceptance ledger.
4. `spec/14-point-remaining-decisions-2026-07-04.md` for the remaining human/Claude decisions before the sprint can close.
5. `spec/project.md` for the product goal and architecture.
6. `spec/development.md` for development constraints.
7. `spec/acceptance.md` before claiming work is complete.
8. `spec/roadmap.md` to understand the current iteration direction.
9. `spec/local-capability-boundary.md` to understand what works without LLM access.
10. `spec/academic-filtering-design.md` when working on the academic layer filtering iteration.
11. `spec/event-tree-literature-graph-design.md` before planning event-tree or academic graph work.
12. `spec/discovery-archive-cognition-timeline-design.md` before planning discovery history or cross-day cognition-tree work.
13. `spec/CHANGELOG.md` to understand recent spec changes.

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
