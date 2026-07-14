# Codex Takeover Work Summary

Status: **RECORDED**

Date: 2026-07-14

Branch: `feature/academic-reading-signals`

Checkpoint HEAD before this report: `3ed51dc`

Push/merge policy: do not push; do not merge `master` without explicit human
approval.

## Scope

This report consolidates the project work completed by Codex while Claude was
offline or acting as an independent reviewer. It is a navigation summary, not a
new roadmap and not permission to reopen completed phases.

Personal model-provider, API-key, Grok, Claude Code, and OpenCode setup is
intentionally excluded. No credential value belongs in this report.

## Delivered Work

### Backend workflow hardening

- Closed the previously reviewed backend P1 batch in `f5bed82`.
- Preserved explicit cognition values, guarded reruns by job type, serialized
  refresh work with rollback, preferred newer analogue candidates, and kept
  local analysis from overwriting existing LLM analysis.
- The exact staged batch passed `308 passed, 1 warning` and GitNexus review
  before commit.

### RM-055 auditable coverage

- Added the no-LLM coverage snapshot contract and integrated it on the current
  branch (`dfdb9c1`, originating from `52c0948`).
- Exposed evidence-linked collector, language, country, source-tier, URL decode,
  and independent-source distributions.
- Kept unavailable fulltext metrics explicitly `unknown` and preserved the rule
  that "not collected" is not proof that a source did not report an event.

### RM-055 M3 cross-device curiosity queue

- Added dedicated queue persistence in `98efa59`, separate from cognition marks
  and profile calibration.
- Hardened revisions, tombstones, concurrent first writes, offline outbox
  replay, cross-tab synchronization, and stale snapshot handling in `4723b0b`.
- Kept queue synchronization outside topic and deep-link critical paths.

### RM-055 M4 fact-first briefing

- Added a shared read-only briefing contract for API, frontend, and email in
  `2fd9155`.
- Preserved original title/snippet evidence, honest coverage labels, auditable
  workbench links, and one read-only domain question.
- Closed review findings around mixed samples, future timestamps, fallback
  behavior, non-blocking deep links, and malformed app URLs in `8cb9f9b` and
  `ff85f65`.

### RM-055 Phase 3 hypothesis boundary

- Added a fresh-render, default-off, component-local hypothesis-layer switch in
  `5a53e41`.
- The enabled state contains only a neutral dashed sample, an explicit
  hypothesis badge, and honest no-data copy.
- No causal claim, generated relation, persistence, API, DTO, backend, or LLM
  path was introduced.
- Independent review required a WCAG repair; final essential text contrast is
  `5.835:1`, and the final review result was `APPROVE`.

### First correctness-audit batch

- Recorded, designed, planned, implemented, and closed pytest database
  isolation in `4a0a2b3`, `8021897`, `6f6452a`, `f83f2f3`, and `3ed51dc`.
- Replaced shared SQLite test paths with unique file-backed session directories
  and function-scoped DiscoveryStore databases.
- Prevented local dotenv files from redirecting first test writes, disposed the
  engine before cleanup, and made cleanup failures visible.
- Three independent repair rounds ended with `APPROVE`.

## Documentation And Governance

- Consolidated live context without deleting history and established the
  minimal startup reading chain.
- Created `spec/feedback-and-ideas/` for user feedback, reflections, developer
  observations, and external references, including Astro/Pagefind and
  OpenSPG/KAG.
- Moved completed, superseded, and reference roadmaps into
  `spec/archive/roadmaps/`, added stable RM identifiers, and retained RM-055 as
  the sole current product roadmap.
- Kept `.agent-bridge/BOARD.md` and `TO_CLAUDE.md` current while preserving old
  exchanges in place or in the local archive.

## Final Accepted Evidence

- Backend: `335 passed, 1 warning`.
- Frontend production build: 98 modules transformed.
- Full desktop and mobile Playwright gate: `180 passed`.
- RM-055 Phase 3 final review: `APPROVE`.
- Test-database isolation final review: `APPROVE`.
- Real `.env`, `dossier.db`, and `discovery.db` were not changed by the accepted
  audit gate.

## Current Checkpoint

- All autonomous RM-055 product phases are complete.
- Source expansion and fulltext scope remain behind the evidence gate in
  `docs/operations/rm055-source-expansion-gate-2026-07-13.md`; the earliest
  review date is 2026-07-27.
- Until that gate, the authorized engineering action is correctness-focused
  auditing in small, independently reviewed batches.
- The branch remains unpushed and unmerged. Local GitNexus instruction files,
  agent bridge files, browser artifacts, skills, and developer scratch files
  remain outside tracked product batches.

## Detailed Reports

- `docs/operations/rm055-m3-task-report-2026-07-13.md`
- `docs/operations/spec-roadmap-consolidation-task-report-2026-07-14.md`
- `docs/operations/rm055-m4-task-report-2026-07-14.md`
- `docs/operations/rm055-phase3-task-report-2026-07-14.md`
- `docs/operations/correctness-audit-test-db-isolation-2026-07-14.md`
