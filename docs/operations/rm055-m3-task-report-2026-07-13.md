# RM-055 M3' Work Management And Task Report

Status: **COMPLETE**

Branch: `feature/academic-reading-signals`

Push/merge policy: do not push; do not merge `master`.

## Delivery Checklist

- [x] Read the authoritative RM-055 roadmap, ledger, Phase 0 report, current queue,
  cognition calibration path, and Coverage contract.
- [x] Run GitNexus impact analysis before production symbol edits; warn that
  `DigQueueItem` and shared `_migrate` map to CRITICAL conservative blast radii.
- [x] Reject reuse of cognition rows after finding that queue and cognition
  semantics could overwrite one another.
- [x] Write backend tests first and observe the expected 404 red state.
- [x] Add a dedicated `DigQueueItem` table and save/list/delete API.
- [x] Prove atomic concurrent create, idempotent retries, revision-guarded
  updates, and tombstone deletes.
- [x] Prove every `CognitionProfile` field and all `CognitionMark` rows remain
  unchanged after queue writes/deletes.
- [x] Write frontend cross-device restoration and network-degrade tests first and
  observe their expected failures.
- [x] Keep localStorage as an offline cache and add a one-operation-per-key
  persisted mutation outbox with causal successor revisions.
- [x] Restore the server queue on a fresh device; replay offline add/delete when
  connectivity returns.
- [x] Show an honest degraded notice while retaining the local queue.
- [x] Keep queue synchronization independent from topic loading and deep links.
- [x] Run the focused backend hardening tests: `8 passed, 1 warning`.
- [x] Run the frontend production build: 98 modules, exit 0.
- [x] Run focused frontend behavior cases: both desktop cases passed; obtain a
  clean process exit again during the final gate.
- [x] Evaluate source expansion against Phase 0 and Coverage evidence.
- [x] Record an executable two-week source-selection gate; no unsupported feed
  expansion was made.
- [x] Run fresh backend full suite: `319 passed, 1 warning`.
- [x] Run fresh frontend full desktop/mobile E2E suite with exit 0: `174 passed`.
- [x] Run `git diff --check` and inspect the exact diff.
- [x] Stage only M3' implementation paths and run staged GitNexus
  `detect-changes`.
- [x] Commit initial implementation without never-commit files: `98efa59`.
- [x] Close four rounds of independent review and commit concurrency hardening:
  `4723b0b`.
- [x] Update roadmap index, ledger, current state, changelog, BOARD, and Claude
  mailbox with actual commit and verification evidence.
- [x] Prepare tracked documentation as a separate closeout batch.
- [x] Complete requirement-by-requirement audit and approve M3' for closeout.
- [ ] Complete the human-requested lossless roadmap archive/index cleanup, then
  open the next RM-055 goal and continue M4'.

## Current Technical Decision

`dig_later` uses a dedicated table and API rather than a new cognition label.
Both remain local-first SQLite data, but queue actions cannot enter cognition
summary/calibration paths or overwrite topic/event cognition marks.

## Evidence Log

- Backend RED: 3 tests failed with 404 because `/api/dig-queue` did not exist.
- Backend GREEN: `3 passed, 1 warning in 3.33s`.
- Frontend RED: remote restore had no queue; offline failure had no sync notice.
- Frontend focused behavior after the initial implementation: 2/2 desktop cases
  passed; its full desktop/mobile suite was `146 passed` with exit 0.
- Frontend build after the TypeScript union fix: exit 0, 98 modules transformed.
- Initial implementation backend suite: `315 passed, 1 warning` with exit 0.
- Hardening RED/GREEN coverage includes concurrent first PUT, stale
  delete/resurrection, tombstone re-add, add-delete and delete-add while the
  predecessor request is in flight, stale cross-tab snapshots, descendant-first
  conflict cleanup, legacy delete migration, malformed/401 behavior, and
  storage-unavailable memory fallback.
- Backend final suite after hardening: `319 passed, 1 warning`; frontend final
  suite: build 98 modules and `174 passed` desktop/mobile E2E.
- Hardening staged GitNexus: 9 files, 67 symbols, 27 flows, risk `critical`.
  The conservative expansion is through shared `_migrate`; exact staged paths
  matched the queue protocol, frontend synchronization, and tests.
- Implementation commit: `98efa59 feat: persist dig queue across devices`.
- Hardening commit: `4723b0b fix: harden dig queue synchronization`.
- Independent review: four REQUEST CHANGES / repair loops followed by final
  `APPROVE`; both remaining non-blocking minor findings were also closed.
- Source decision: HOLD until the gate in
  `docs/operations/rm055-source-expansion-gate-2026-07-13.md` is satisfied.

## Human Decisions Deferred To The End

None currently required. Any genuine product-direction decision discovered later
will be listed here instead of interrupting unattended execution.
