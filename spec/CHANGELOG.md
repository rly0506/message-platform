# Spec Changelog

> Recent window only. The complete history through 2026-07-12 is preserved at `spec/archive/changelog/CHANGELOG-through-2026-07-12.md`.

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
