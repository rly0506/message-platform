# Redundancy Audit - 2026-07-03

## Decision

No business-code refactor was applied in Phase 3.

This is intentional. The working tree already contains a large cross-layer repair set. The redundancy scan found real hotspots, but the safe reduction opportunities are not strong enough to justify adding another behavior-preserving refactor patch before final regression.

## Evidence

Largest local files:

- `frontend/src/style.css`: 2740 lines.
- `frontend/src/App.vue`: 1289 lines.
- `frontend/src/components/DiscoveryPanel.vue`: 1030 lines.
- `backend/app/api.py`: 840 lines.
- `frontend/src/components/MediaPanel.vue`: 780 lines.
- `frontend/src/composables/useJobRunner.ts`: 666 lines.
- `backend/app/topic_ops.py`: 553 lines.
- `backend/app/services/search_service.py`: 508 lines.

CSS selector scan:

- `frontend/src/style.css` has many repeated selector blocks, especially `.markdown-body`, `.source-matrix-table`, `.event-network-edge`, `.step-list`, `.sentiment-platform-chip`, `.topic-editor`, `.project-row`, `.source-table`, and `.academic-paper`.
- This is a valid next cleanup target, but it needs visual regression checks because the duplicated selectors often represent component-specific overrides, not mechanically identical dead code.

GitNexus impact checks:

- `useJobRunner` upstream impact: LOW, 1 direct caller.
- `useTopicData` upstream impact: LOW, 1 direct caller.
- `run_cross_synthesis_job` upstream impact: LOW.
- `run_search` upstream impact: CRITICAL, 5 impacted symbols and 6 affected processes.

## Candidates Rejected For This Pass

### `backend/app/services/search_service.py`

Rejected because `run_search` is CRITICAL. This file owns job lifecycle, search, deep analysis, academic, sentiment, cross-synthesis, and discovery orchestration. A cosmetic cleanup here would increase the risk surface without fixing a reproduced bug.

### `frontend/src/composables/useJobRunner.ts`

Rejected for now despite LOW GitNexus impact. The function is large, but it is the UI job state machine for search, deep analysis, academic, sentiment, and cross-synthesis. Splitting it safely should be a dedicated frontend refactor with Playwright checkpoints after each extraction.

### `frontend/src/App.vue`

Rejected because project/source management has just landed and is covered by e2e. Extracting management forms now would touch prop/event wiring and could create avoidable regressions.

### `frontend/src/style.css`

Rejected because selector repetition is real but not proven identical. A safe style cleanup needs visual screenshots or component-level CSS grouping. That is a separate small task, not a drive-by edit in this audit.

### `backend/app/api.py`

Rejected because many new handlers are uncommitted and not fully represented as individual GitNexus symbols. Moving helpers now would make the already-large API diff harder to review.

## Recommended Next Refactor Route

1. CSS-only patch: group project/source manager form styles and run `npm run build` plus `project-management.spec.ts` and `source-registry.spec.ts`.
2. Frontend composable patch: extract source registry state/actions from `App.vue` into `frontend/src/composables/useSourceRegistry.ts`; run `source-registry.spec.ts`.
3. Frontend composable patch: extract project manager form state/actions from `App.vue`; run `project-management.spec.ts`.
4. Backend helper patch: extract pure project/topic payload validation helpers from `api.py` only after GitNexus index includes the current uncommitted handlers.
5. Search-service cleanup only after the current 14-point repair branch is committed and the `CRITICAL` baseline drops.

## Phase 3 Result

Phase 3 passes as a conservative no-code refactor decision.

No dependencies were added. No public API, DTO, database field, route, button text, or workflow behavior was changed.
