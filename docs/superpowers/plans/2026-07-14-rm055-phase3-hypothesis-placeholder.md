# RM-055 Phase 3 Hypothesis Placeholder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a default-off, data-less hypothesis-layer placeholder to the
existing event graph so future inference cannot be confused with evidence.

**Architecture:** Keep the state and markup entirely inside `EventGraph.vue`.
The existing graph props, evidence rendering, parent component, API, and DTOs
remain unchanged. One existing event-network E2E scenario proves the layer is
off by default, visibly hypothetical when enabled, and unable to alter evidence
rows.

**Tech Stack:** Vue 3 `<script setup>`, scoped CSS, Playwright, existing design
tokens. No dependency, backend, storage, or LLM change.

---

## File Map

- Modify `frontend/src/components/EventGraph.vue`: own the local switch state,
  render the hypothesis placeholder, and define neutral responsive styles.
- Modify `frontend/tests/e2e/source-matrix.spec.ts`: extend the existing
  two-event evidence-network scenario with default-off, enabled-empty,
  evidence-preservation, accessibility, and viewport assertions.
- Update this plan in place as the execution report; record RED/GREEN, review,
  commit, and residual boundaries before closeout.

### Task 1: Prove The Boundary With A Failing Browser Test

**Files:**

- Modify: `frontend/tests/e2e/source-matrix.spec.ts:831`

- [x] **Step 1: Run GitNexus impact before editing**

Run:

```powershell
node .gitnexus/run.cjs impact layout --direction upstream --repo message-platform --branch feature/academic-reading-signals --file frontend/src/components/EventGraph.vue --include-tests
node .gitnexus/run.cjs impact eventNetwork --direction upstream --repo message-platform --branch feature/academic-reading-signals --file frontend/src/components/MediaPanel.vue --include-tests
```

These symbols cover the graph renderer and its only parent data adapter. Stop and
warn before editing if either result is HIGH or CRITICAL.

- [x] **Step 2: Add the expected hypothesis-layer assertions**

In `renders local evidence edges between events in the event network`, after the
three evidence-row assertions, add:

```ts
  const hypothesisSwitch = network.getByRole('switch', { name: '显示假设层' })
  await expect(hypothesisSwitch).toHaveAttribute('aria-checked', 'false')
  await expect(network.locator('.event-graph-hypothesis-placeholder')).toHaveCount(0)

  const evidenceCount = await network.locator('.event-graph-evidence-row').count()
  await hypothesisSwitch.click()

  await expect(hypothesisSwitch).toHaveAttribute('aria-checked', 'true')
  const hypothesis = network.locator('.event-graph-hypothesis-placeholder')
  await expect(hypothesis).toBeVisible()
  await expect(hypothesis.getByText('假设', { exact: true })).toBeVisible()
  await expect(hypothesis).toContainText('尚无假设数据。证据边不会自动转成因果判断。')
  await expect(network.locator('.event-graph-evidence-row')).toHaveCount(evidenceCount)

  const box = await network.locator('.event-graph-hypothesis').boundingBox()
  const viewport = page.viewportSize()
  expect(box).not.toBeNull()
  expect(viewport).not.toBeNull()
  expect((box?.x || 0) + (box?.width || 0)).toBeLessThanOrEqual(viewport?.width || 0)
```

The scenario already runs in both Playwright projects, so these assertions cover
desktop and Pixel 5 without a duplicate test.

- [x] **Step 3: Run the focused test and verify RED**

Run:

```powershell
cd frontend
npx playwright test tests/e2e/source-matrix.spec.ts --grep "renders local evidence edges"
```

Expected: both desktop and mobile fail because no switch named `显示假设层`
exists. A timeout caused by unrelated setup is not the expected RED; diagnose it
before continuing.

### Task 2: Implement The Minimal Local Placeholder

**Files:**

- Modify: `frontend/src/components/EventGraph.vue:68,268-289,292-479`

- [x] **Step 1: Add component-local, non-persisted state**

Beside `hoveredEdgeKey`, add:

```ts
const hypothesisVisible = ref(false)
```

Do not add props, emits, watchers, storage, or API calls.

- [x] **Step 2: Render the switch and honest empty layer**

After the evidence list and before the existing no-edge message, add:

```vue
    <section class="event-graph-hypothesis" aria-label="假设层">
      <div class="hypothesis-layer-head">
        <div>
          <strong>假设层</strong>
          <span>{{ hypothesisVisible ? '已显示' : '默认关闭' }}</span>
        </div>
        <button
          type="button"
          class="hypothesis-switch"
          role="switch"
          :aria-checked="hypothesisVisible"
          aria-label="显示假设层"
          @click="hypothesisVisible = !hypothesisVisible"
        >
          <span aria-hidden="true" />
        </button>
      </div>
      <div v-if="hypothesisVisible" class="event-graph-hypothesis-placeholder">
        <div class="hypothesis-sample" aria-hidden="true">
          <i />
          <span>假设</span>
        </div>
        <p>尚无假设数据。证据边不会自动转成因果判断。</p>
      </div>
    </section>
```

The placeholder must not render relation endpoints, event numbers, or claim
text.

- [x] **Step 3: Add stable neutral styles**

Append scoped styles using existing tokens:

```css
.event-graph-hypothesis {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
  padding-top: var(--space-3);
  border-top: 1px dashed var(--border-strong);
}

.hypothesis-layer-head,
.hypothesis-layer-head > div,
.hypothesis-sample {
  display: flex;
  align-items: center;
}

.hypothesis-layer-head {
  justify-content: space-between;
  gap: var(--space-3);
}

.hypothesis-layer-head > div {
  min-width: 0;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.hypothesis-layer-head strong {
  color: var(--text-heading);
  font-size: var(--font-size-1);
}

.hypothesis-layer-head > div > span,
.event-graph-hypothesis-placeholder p {
  color: var(--text-faint);
  font-size: var(--font-size-0);
}

.hypothesis-switch {
  position: relative;
  flex: 0 0 38px;
  width: 38px;
  height: 20px;
  padding: 0;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  background: var(--surface-tint);
  cursor: pointer;
}

.hypothesis-switch > span {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-faint);
  transition: transform 0.1s ease;
}

.hypothesis-switch[aria-checked='true'] > span {
  transform: translateX(18px);
}

.hypothesis-switch:focus-visible {
  outline: 2px solid var(--brand-accent);
  outline-offset: 2px;
}

.event-graph-hypothesis-placeholder {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
  color: var(--text-faint);
}

.event-graph-hypothesis-placeholder p {
  margin: 0;
  overflow-wrap: anywhere;
}

.hypothesis-sample {
  flex: 0 0 auto;
  gap: var(--space-2);
}

.hypothesis-sample i {
  width: 24px;
  border-top: 2px dashed var(--text-faint);
}

.hypothesis-sample span {
  border: 1px solid var(--border-strong);
  border-radius: 4px;
  padding: 1px 5px;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 800;
}
```

Add the mobile wrapping rule with the other scoped styles:

```css
@media (max-width: 520px) {
  .event-graph-hypothesis-placeholder {
    align-items: flex-start;
    flex-direction: column;
  }
}
```

- [x] **Step 4: Run focused GREEN and production build**

Run:

```powershell
cd frontend
npx playwright test tests/e2e/source-matrix.spec.ts --grep "renders local evidence edges"
npm run build
```

Expected: 2 focused tests pass (desktop and mobile); Vue type checking and Vite
build exit 0 with 98 modules unless the module count legitimately changes.

### Task 3: Review, Full Gate, And Implementation Commit

**Files:**

- Modify: `docs/superpowers/plans/2026-07-14-rm055-phase3-hypothesis-placeholder.md`

- [x] **Step 1: Run the full frontend gate**

Run:

```powershell
cd frontend
npm run test:e2e
cd ..
git diff --check
```

Expected: all existing plus modified desktop/mobile tests pass; diff check exits
0. No backend suite is required because no backend, API, DTO, or shared contract
changes.

- [x] **Step 2: Stage only the implementation and plan report**

Run:

```powershell
git add -- frontend/src/components/EventGraph.vue frontend/tests/e2e/source-matrix.spec.ts docs/superpowers/plans/2026-07-14-rm055-phase3-hypothesis-placeholder.md
git diff --cached --check
git diff --cached --name-status
node .gitnexus/run.cjs detect-changes --scope staged --repo message-platform --branch feature/academic-reading-signals
```

Expected staged paths: exactly the three listed above. Explain any HIGH/CRITICAL
risk before proceeding.

- [x] **Step 3: Obtain independent review**

Review from design base `cbb62a4`. Require findings first and exact file/line
references. Fix every Critical/Important finding with a new RED test; assess
Minor findings explicitly.

Review record:

- The first reviewer attempt failed before producing a code conclusion with
  `account_share_mode_unbound`; it was replaced rather than treated as approval.
- The replacement review requested changes for the essential no-data copy's
  WCAG AA contrast. It also noted that the evidence-preservation and overflow
  assertions were too weak.
- The repair test failed on both projects at the intended contrast assertion
  (`3.8428017787704145 < 4.5`). The production repair moved status and disclaimer
  copy to `--text-muted-2` while keeping the decorative sample faint. The focused
  desktop/mobile rerun then passed (`2 passed`).
- Both Minor suggestions were incorporated: the test now compares evidence-row
  content plus SVG node/edge counts before and after enabling the layer, and
  checks the placeholder's `scrollWidth <= clientWidth`.
- Fresh post-repair evidence: production build passed with 98 modules and the
  full Playwright matrix passed (`180 passed`). Final reviewer approval remains
  required after the refreshed staged-scope check.
- The repair re-review approved the product change and raised one new
  non-blocking test-helper Minor: opaque three-component `rgb(...)` values were
  treated as transparent when alpha was absent. The fallback was corrected from
  `0` to the CSS default `1`, and the focused desktop/mobile test remained green
  (`2 passed`). Final confirmation then returned APPROVE with no Critical,
  Important, or Minor findings on the exact staged diff.

- [x] **Step 4: Commit implementation**

After final approval and fresh focused/full evidence:

```powershell
git commit -m "feat: reserve hypothesis layer in event graph"
```

Do not push or merge `master`.

Committed as `5a53e41 feat: reserve hypothesis layer in event graph`.

### Task 4: Closeout And Claude Handoff

**Files:**

- Modify: `spec/current-state.md`
- Modify: `spec/roadmap.md`
- Modify: `spec/roadmap-ledger.md`
- Modify: `spec/CHANGELOG.md`
- Modify locally only: `.agent-bridge/BOARD.md`
- Modify locally only: `.agent-bridge/TO_CLAUDE.md`

- [x] **Step 1: Record final evidence in this plan**

Mark every completed step, add exact commit IDs, test counts, GitNexus scope,
review result, residual boundaries, and deferred human decisions. Do not erase
failed runs or review repairs.

- [x] **Step 2: Update current truth**

Mark Phase 3 done while keeping the 2026-07-27 source/fulltext evidence gate
open. If no other executable RM-055 item remains, state that the next autonomous
action is a correctness-focused code audit rather than inventing a product
feature.

- [x] **Step 3: Update Claude locally**

Prepend one concise handoff with implementation commit, behavior, tests, review,
and next action. Keep `.agent-bridge/` untracked and preserve older messages.

- [x] **Step 4: Run the documentation gate and commit separately**

Run strict UTF-8/reference checks, `git diff --check`, secret/database status,
and staged GitNexus on tracked documentation only. Then commit:

```powershell
git commit -m "docs: close RM-055 Phase 3 gate"
```

Do not push or merge `master`.

## Closeout Evidence

- Implementation commit: `5a53e41`.
- Initial feature RED: the desktop/mobile scenario failed because the accessible
  hypothesis switch did not exist. Initial focused GREEN: `2 passed`.
- Review-repair RED: desktop and mobile both failed at the new WCAG assertion
  with `3.8428017787704145 < 4.5`. The repaired text measures `5.835:1`.
- Final focused browser gate: `2 passed`; production build: 98 modules; full
  desktop/mobile E2E: `180 passed`.
- Final review: `APPROVE`, with no Critical, Important, or Minor findings on the
  exact staged implementation diff.
- Final implementation GitNexus scope: 3 files, 7 symbols, 0 flows, `low`.
- Detailed task report:
  `docs/operations/rm055-phase3-task-report-2026-07-14.md`.
- Residual boundary: no hypothesis generation, storage, API, DTO, backend, or
  LLM path was added. Source expansion and fulltext scope remain at the existing
  2026-07-27 human evidence gate.
- No new human decision was discovered for Phase 3. The next authorized
  autonomous action is a correctness-focused code audit.
