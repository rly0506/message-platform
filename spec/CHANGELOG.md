# Spec Changelog

> Recent window only. The complete history through 2026-07-12 is preserved at `spec/archive/changelog/CHANGELOG-through-2026-07-12.md`.

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
