# Spec Changelog

> Recent window only. The complete history through 2026-07-12 is preserved at `spec/archive/changelog/CHANGELOG-through-2026-07-12.md`.

## 2026-07-16 RM-065 R1 Probe Implementation Plan

- Added a P0-gated, TDD implementation plan for the inspection-reading evidence
  probe. It specifies deterministic 3-topic/30-slot selection, a separate
  disposable SQLite filesystem snapshot that never opens the source family,
  pinned-IP public-page access, closed terminal states, per-field provenance,
  and text-free durable evidence after Grok review.
- Specification and security reviews approved the final contract with no open
  findings. It fixes the production runtime/report roots, strips every query
  value from durable URLs, uses a strict local robots matcher, and makes every
  text/database cleanup state recoverable through owner locks, a no-replace
  claim, tombstone cleanup, and bound pending/final metadata.
- Recorded GitNexus `CRITICAL` impact for the shared `Article` and
  `TopicArticle` models and avoids editing either model, schema, API, DTO, or
  product flow. The plan reuses only the low-risk HTML extraction helper.
- The plan authorizes no product code, real-database read, external network
  probe, LLM call, source enablement, Coverage change, merge, or release.

## 2026-07-16 RM-065 H0 Documentation Closeout

- Added compact root and `docs/` routing indices for both humans and agents.
- Classified historical unfinished work in `spec/current-state.md` without
  reopening completed or superseded roadmaps; RM-055 remains the sole
  `CURRENT`, RM-065 remains a `CANDIDATE`, and source expansion remains `HOLD`.
- Archived superseded architecture/direction prose while retaining stable
  redirect files for code comments and historical links.
- Archived the stale 2026-07-05 Fable 5 audit and replaced its active route
  with an explicit disposition: five named P0 findings closed in `a4647f5`;
  broad P1/P2 themes require fresh evidence rather than automatic reopening.
- Retired `docs/superpowers/` as an active workflow authority while preserving
  its completed plans/specs as evidence; no user-level plugin cache was
  removed or modified.
- Rotated the ignored Agent Bridge board and three long mailboxes into dated
  archives, then rebuilt small live checkpoints. No backend, frontend, source,
  LLM, API, database, or real-observation behavior changed.

## 2026-07-15 RM-065 Inspection-First Candidate Roadmap

- Added RM-065 as a `CANDIDATE` without replacing RM-055: historical truth and
  topic-load correctness precede inspection reading, measured performance,
  local event clustering/deduplication, and evidence-gated source expansion.
- Recorded the human decisions for temporary probe retention, a separate local
  90-day inspection store, a three-article prefetch cap, event clustering as the
  first local-analysis target, and replaceable analysis frameworks.
- Corrected `spec/roadmap.md` from “observation pipeline pending” to the current
  truth: implemented and reviewed, with no successful real observation day yet.
- This documentation change authorizes no candidate implementation, source
  enablement, real-database run, `master` merge, or release.

## 2026-07-15 Agent Work Protocol

- Added a durable, versioned task harness to `spec/development.md`: visible
  todo first, bounded independent subagent before material change, parent
  self-review, ordered verification, and honest checklist closure.
- Defined the non-recursive review-child exception so the required independent
  review does not become infinite delegation.
- Linked the ignored Agent Bridge agreement and task-checklist template to this
  canonical policy; the Bridge copy may add coordination detail but cannot
  weaken the tracked rule.

## 2026-07-15 RM-055 Coverage Observation Pipeline

- Implemented the post-commit, immutable filesystem observation recorder,
  verification/status CLI, strict HTTP-first one-shot refresh, and daily
  discover -> refresh -> email order in `e4a0a35`.
- Preserved unknown and unclassified evidence, isolated recorder failures from
  collection results, retained the exact existing nine-field auto-refresh API,
  and added no source, fulltext persistence, LLM path, or automatic decision.
- Independent specification and quality reviews approved the implementation.
  A final isolation review approved `6c3e316`, which keeps pytest observation
  evidence below the existing temporary test database root before `app.*`
  imports.
- Fresh focused verification passed (`14 passed`); full backend verification
  after the isolation fix passed (`368 passed, 1 warning`). The real authorized
  `refresh-once` attempt failed closed on a loopback `URLError` timeout, so
  successful-day count remains `0`; `first_successful_date` and window end
  remain unset.
- Source expansion remains `HOLD`; no feed was enabled and no `master` merge or
  push was performed. See
  `docs/operations/rm055-coverage-observation-task-report-2026-07-15.md`.

## 2026-07-14 Codex Takeover Work Summary

- Added `docs/operations/codex-takeover-work-summary-2026-07-14.md` as the
  consolidated navigation record for backend P1, RM-055 coverage, M3, M4,
  Phase 3, documentation governance, and the first correctness-audit batch.
- Linked the detailed task reports and recorded the final accepted backend,
  frontend, browser, and independent-review evidence without changing roadmap
  status or reopening completed phases.
- Explicitly excluded personal model-provider, API-key, Grok, Claude Code, and
  OpenCode configuration from the project record.

## 2026-07-14 Correctness Audit: Backend Test Database Isolation

- Replaced shared process-global pytest SQLite paths with unique file-backed
  session directories and function-scoped DiscoveryStore `tmp_path` databases.
- Prevented local `backend/.env` from redirecting test writes by installing a
  version-independent, process-local dotenv no-op before any `app.*` import.
- Disposed the shared engine before session-directory cleanup and made cleanup
  failures visible; added cross-platform order and Windows handle regressions.
- Added real child-pytest coverage for concurrent path uniqueness, TMPDIR and
  DB_PATH containment, first-write dotenv safety, normal cleanup, and failure
  propagation.
- Three review rounds found environment-containment, lifecycle-proof, dotenv
  pre-write, and dependency-version gaps. A fresh final reviewer returned
  `APPROVE` with no Critical or Important findings.
- Implementation: `f83f2f3`. Final verification: focused `8 passed`, backend
  `335 passed, 1 warning`, GitNexus 5 files / 32 symbols / 0 flows / `low`, and
  unchanged real environment/database files.

## 2026-07-14 RM-055 Phase 3 Hypothesis-Layer Boundary

- Added an accessible EventGraph-local hypothesis-layer switch that defaults
  off on each fresh render and has no storage, API, DTO, backend, or LLM path.
- Kept the enabled state deliberately empty: one neutral dashed sample, an
  explicit `假设` badge, and copy stating that evidence edges do not become
  causal judgments.
- Added desktop/mobile checks for default-off behavior, honest empty state,
  evidence text and SVG node/edge preservation, WCAG AA text contrast, and
  horizontal overflow.
- Independent review requested one contrast repair and two test-strength
  improvements. The repaired text measures `5.835:1`; final review ended
  `APPROVE` with no Critical, Important, or Minor findings.
- Implementation commit: `5a53e41`. Verification: focused Playwright `2 passed`,
  build 98 modules, full desktop/mobile E2E `180 passed`, and staged GitNexus
  3 files / 7 symbols / 0 flows / `low`.
- RM-055 now has no autonomous product phase before the 2026-07-27 source and
  fulltext evidence gate; the authorized interim action is a correctness-focused
  code audit.

## 2026-07-14 RM-055 M4' Fact-First Briefing

- Added one read-only persisted-data briefing contract shared by
  `GET /api/briefing/latest`, the discovery front page, and scheduled email.
- Selected at most one recent relevant article per active topic, attached event
  or topic coverage, retained original evidence and contrast deep links, and
  rotated one deterministic domain-question scaffold without profile writes.
- Kept source, language, and fulltext unknowns explicit; facts use original
  title/snippet fields rather than LLM-enriched translations, and malformed app
  base URLs fall back to relative workbench paths.
- Kept briefing requests independent from discovery reports and deep-link
  parsing; email falls back to the archived discovery report if briefing build
  fails.
- Independent review drove two repair rounds and ended `APPROVE`. Commits:
  `2fd9155`, `8cb9f9b`, and `ff85f65`.
- Final verification: backend `327 passed, 1 warning`; frontend build 98 modules;
  desktop/mobile E2E `180 passed`; initial staged GitNexus scope was `high`
  across 13 files / 35 symbols / 8 expected discovery/email flows.

## 2026-07-14 Historical Roadmap Consolidation

- Consolidated all completed, superseded, and reference roadmaps under
  `spec/archive/roadmaps/` without deleting their historical content.
- Added a numbered archive index for RM-010 through RM-017, RM-030, RM-040,
  and RM-050; registered the previously unnumbered GPT continuation as RM-017.
- Updated tracked references to the new canonical paths and corrected the
  startup router so the current sprint points to RM-055 rather than RM-050.
- Kept RM-055 at the spec root as the sole current product roadmap and RM-060
  at the root as a candidate; no roadmap status or historical conclusion was
  rewritten as part of the move.

## 2026-07-14 RM-055 M3' Queue Concurrency Hardening

- Added monotonic per-item revisions and durable tombstones so stale devices
  cannot delete a restored item or resurrect a deleted one.
- Replaced query-then-insert with atomic SQLite conflict handling; concurrent
  identical first PUTs and lost-response retries are idempotent.
- Reworked the frontend outbox into one durable record per operation, with
  causal successor revisions, descendant-first rejection cleanup, stale
  snapshot rejection, and a forced rerun when cross-tab state changes in flight.
- Preserved tombstone revisions and outbox operations in memory when browser
  storage is unavailable; retained authentication/version failures for retry and
  isolated only explicit request-validation failures.
- Migrated legacy pending deletes conservatively: revision-1 legacy records can
  complete, while newer server revisions win instead of being overwritten.
- Independent review completed four repair loops and ended with `APPROVE`.
- Verification for `4723b0b`: backend `319 passed, 1 warning`; frontend build
  passed with 98 modules; full desktop/mobile E2E `174 passed`; staged GitNexus
  reported 9 files / 67 symbols / 27 flows / `critical`, conservatively expanded
  through shared `_migrate`.

## 2026-07-13 RM-055 M3' Cross-Device Curiosity Queue

- Added a dedicated `DigQueueItem` SQLite model and idempotent save/list/delete API.
- Kept curiosity data structurally separate from `CognitionMark` and `CognitionProfile`; regression tests compare the full profile and mark dataset before/after queue mutations.
- Upgraded the frontend queue from localStorage-only to local cache plus a persisted mutation outbox and server reconciliation.
- Restored queue items on a fresh device, preserved offline add/delete intent, displayed honest degraded sync state, and kept sync off the deep-link/topic-loading critical path.
- Added backend and desktop/mobile E2E coverage for persistence, idempotence, remote restoration, deletion, and network failure.
- Recorded a HOLD on source expansion: the coverage instrument has not yet produced the two weeks of longitudinal gap evidence required to choose a defensible first feed batch.
- Verification for implementation commit `98efa59`: backend `315 passed, 1 warning`; frontend build passed with 98 modules; full E2E `146 passed`; staged GitNexus risk `medium` across 9 files / 46 symbols / 5 flows.

## 2026-07-12 Feedback And Ideas Library

- Added `spec/feedback-and-ideas/` as the stable home for user feedback, reflections, developer observations, and external project references.
- Added a feedback ledger linking the historical 14-point source files and the surviving 10-point mailbox record without rewriting either source.
- Added a reference index and dedicated notes for `Mr-Salticidae/knowledge-base`, its Astro/Pagefind display pattern, and OpenSPG/KAG.
- Moved the existing combined publishing/reasoning review into the new reference directory without deleting its content.
- Kept all external projects at `REFERENCE` or `DEFERRED CANDIDATE`; none were added to RM-050 or the implementation backlog.

## 2026-07-12 Documentation Context Consolidation

- Archived full snapshots of BOARD, both live mailboxes, and the changelog before shortening them.
- Reduced BOARD and live mailboxes to the current checkpoint and latest actionable exchange.
- Moved completed/superseded roadmaps to `spec/archive/roadmaps/`.
- Moved the old framework plan to `spec/archive/plans/` and historical backend build logs to `spec/archive/build-logs/`.
- Moved the ChinaNewsMap reference note to `docs/references/chinanewsmap-platform.md`.
- Replaced the read-everything startup list with a four-document startup set plus task-based routing.
- Preserved `backend/discovery_reports/` as product data; it was not modified.
- Preserved the former 410-line `spec/current-state.md` verbatim under `spec/archive/current-state/`, then rewrote the live file as concise current truth.
- Added a non-roadmap reference note for Astro/Pagefind publishing patterns and OpenSPG/KAG reasoning patterns, with explicit borrow/defer/reject decisions.
- Did not modify `AGENTS.md` or `CLAUDE.md`, and did not stage or commit any files.

### Current Coordination Truth

- Claude withdrew the claim that the current backend P1 batch caused test contamination.
- The same backend code and command produced `308 passed, 1 warning` twice.
- The backend P1 batch is code-reviewed and test-accepted; its remaining gate is staged GitNexus `detect-changes` on the exact target files.
- Shared test-database cleanup and event-graph source-of-truth remain separate, non-blocking architecture debts.

## 2026-07-12 Roadmap Ledger And Information Boundary

- Added `spec/roadmap-ledger.md` as the unique roadmap status index.
- Kept RM-050 as the only current product roadmap: M1 complete, M2 partial, M3/M4 pending.
- Added `spec/ai-collaboration-and-source-boundary-2026-07-12.md` as RM-060 `CANDIDATE`.
- Recorded the user's concerns about AI information asymmetry and future blogs, podcasts, video, personal sites, LinkedIn, and authorized private-source ingestion.

## 2026-07-10 Understanding Layer U1 Backend

- Added read-only cross-topic event analogues with explainable similarity, named differences, evidence IDs, truncation disclosure, and non-causal language.
- Later audit identified two remaining boundaries: evidence precision must close with the frontend consumer, and the event graph still reflects local rather than LLM analysis.

## 2026-07-09 Event Graph And Multi-Source Contrast

- Completed event graph V1 and the first multi-source contrast consumer.
- Superseded RM-030/RM-040 with RM-050 for the remaining dual-mode entry, analogue consumer, and deferred hypothesis layer.

## 2026-07-08 Data-Line Options

- Added default-off direct URL/fulltext paths around GNews decoding, SearXNG, and Scrapling.
- These options do not alter the default collection path and must leave degradation evidence when enabled.

## Older History

Read `spec/archive/changelog/CHANGELOG-through-2026-07-12.md`. Historical entries remain verbatim and are not normal startup context.
