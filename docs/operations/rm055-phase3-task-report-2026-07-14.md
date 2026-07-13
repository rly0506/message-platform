# RM-055 Phase 3 Hypothesis-Layer Placeholder Task Report

Status: **COMPLETE**

Branch: `feature/academic-reading-signals`

Implementation commit: `5a53e41 feat: reserve hypothesis layer in event graph`

Push/merge policy: do not push; do not merge `master`.

## Goal And Boundary

Reserve a visible place for future hypotheses in EventGraph while preventing
users, tests, and future agents from confusing observed evidence with inferred
causality.

The accepted V1 boundary is intentionally narrow:

- fresh load is off;
- state is component-local and is not persisted;
- enabled state contains one neutral dashed sample, an explicit `假设` badge,
  and an honest no-data statement;
- no hypothesis relation, endpoint, event identifier, claim, API, DTO, backend
  model, LLM request, or storage key is created;
- existing evidence rows and SVG evidence edges remain unchanged.

## Work Checklist

- [x] Read RM-030/RM-055 requirements and the current EventGraph consumer.
- [x] Run GitNexus impact analysis before editing. `EventGraph.layout` and
  `MediaPanel.eventNetwork` were both LOW with 0 upstream processes.
- [x] Write desktop/mobile assertions first and observe RED because the switch
  did not exist.
- [x] Implement the minimal local switch, default-off status, neutral sample,
  and explicit evidence-versus-causality copy.
- [x] Run focused desktop/mobile Playwright to GREEN (`2 passed`).
- [x] Run the production build (98 modules) and full E2E (`180 passed`).
- [x] Stage only EventGraph, its E2E scenario, and the execution plan; run
  cached diff hygiene and staged GitNexus.
- [x] Obtain independent review and repair every blocking finding with a new
  failing assertion before changing production behavior.
- [x] Commit implementation separately as `5a53e41`.
- [x] Update current-state, roadmap, ledger, changelog, task report, BOARD, and
  the Claude mailbox without deleting historical messages.
- [x] Keep `.agent-bridge/`, `AGENTS.md`, `CLAUDE.md`, local skill directories,
  browser artifacts, and developer scratch files outside the tracked batch.

## TDD And Review Record

The original scenario failed in both Playwright projects because no accessible
`显示假设层` switch existed. After the minimal implementation, the focused
desktop/mobile scenario passed.

The first review attempt ended before a code conclusion with
`account_share_mode_unbound`; it was replaced and was not counted as approval.
The replacement reviewer requested changes because the essential no-data text
did not meet WCAG AA contrast. It also identified weak evidence-preservation and
overflow assertions.

The new contrast assertion failed in both projects at the intended condition:
`3.8428017787704145 < 4.5`. Production text moved from `--text-faint` to the
existing `--text-muted-2` token while the decorative line and badge remained
faint. The test also began comparing evidence-row text, SVG node count, SVG edge
count, and placeholder `scrollWidth <= clientWidth` before/after the toggle.

Repair verification passed in both projects. Re-review measured the essential
text at `5.835:1` and approved the product change. One new non-blocking test
helper issue was then fixed: three-component `rgb(...)` values now use the CSS
default alpha of `1`, not `0`. The reviewer inspected the final staged diff and
returned `APPROVE` with no Critical, Important, or Minor findings.

## Final Evidence

- Focused browser gate:
  `npx playwright test tests/e2e/source-matrix.spec.ts --grep "renders local evidence edges"`
  -> `2 passed` across desktop and mobile.
- Frontend production gate: `npm run build` -> 98 modules transformed.
- Full browser gate: `npm run test:e2e` -> `180 passed`.
- Diff hygiene: `git diff --cached --check` -> exit 0.
- Final staged GitNexus: 3 files, 7 symbols, 0 affected flows, `low` risk.
- Backend suite was not rerun for this frontend-only, no-contract batch. The
  unchanged accepted backend gate remains `327 passed, 1 warning` from M4'.
- No real `.env`, database, secret, push, or `master` merge was involved.

## Residual Boundaries And Next Action

This phase does not authorize hypothesis generation. A future U3 needs a new
roadmap decision covering provenance, contradiction evidence, persistence,
failure behavior, and how inferred relations remain distinguishable from local
evidence.

Source expansion and fulltext persistence remain behind the existing
2026-07-27 human evidence gate. With all executable RM-055 product phases now
closed, the next autonomous action is a correctness-focused code audit; audit
findings must land as small, independently reviewed batches rather than an
invented feature phase.

## Human Decisions Deferred To The End

No new Phase 3 decision is required. The only open product decisions are the
already-recorded 2026-07-27 source-expansion and fulltext-scope gate.
