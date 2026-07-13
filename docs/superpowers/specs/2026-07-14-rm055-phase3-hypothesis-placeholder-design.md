# RM-055 Phase 3 Hypothesis-Layer Placeholder Design

## Approval Basis

The human already approved RM-055 and delegated subsequent roadmap stages to
Codex while Claude is offline. This design narrows the previously approved F3
contract from RM-030/RM-055; it does not introduce a new product direction.

## Goal

Reserve a clearly separate, default-off hypothesis layer inside the existing
event graph so future inferred relations cannot be confused with the current
auditable evidence edges.

## Fixed Scope

- Frontend only: `EventGraph.vue` plus focused Playwright coverage.
- No API, DTO, database, prompt, LLM call, or generated hypothesis data.
- The evidence graph remains unchanged and visible whether the hypothesis layer
  is off or on.
- The layer is off on every fresh page load and is not persisted.
- Enabling it shows only an honest empty placeholder and the future visual
  language: neutral gray, dashed line, and an explicit `假设` badge.

## Approaches Considered

### A. Local Layer Inside `EventGraph.vue` (selected)

Keep one local boolean in the graph component and render a sibling section after
the evidence list. This keeps evidence and inference adjacent enough to compare,
but structurally separate. It requires no parent props or cross-page state.

### B. Separate `MediaPanel.vue` Disclosure

Add another collapsed panel beside the event network. This is easy to build but
visually disconnects the future layer from the graph it qualifies and adds one
more top-level media panel.

### C. Global Workbench Mode

Add hypothesis state to App/composables and thread it through MediaPanel. This
would support persistence later, but it creates cross-layer state for a data-less
placeholder and violates the small reversible scope.

Approach A is the smallest implementation that makes the epistemic boundary
visible without inventing future architecture.

## UI Contract

`EventGraph.vue` adds a compact `section.event-graph-hypothesis` after the
evidence rows:

1. A text label `假设层` and status `默认关闭` or `已显示`.
2. A native button with `role="switch"`, accessible name `显示假设层`, and an
   accurate `aria-checked` value.
3. When off, the hypothesis placeholder body is absent.
4. When on, the body contains:
   - one gray dashed visual sample marked `假设`;
   - `尚无假设数据。证据边不会自动转成因果判断。`;
   - no nodes, relation endpoints, claims, or generated prose.

The sample line is decorative (`aria-hidden="true"`) and must not look like an
actual edge. The text is the accessible source of truth.

## State And Data Flow

`const hypothesisVisible = ref(false)` is component-local. A click flips the
boolean. No watcher, storage, API request, event emission, or parent contract is
added. Existing `nodes`, `edges`, selection, hover, and evidence rendering are
untouched.

## Visual Boundary

- Evidence keeps its existing colored solid/dashed styles and evidence rows.
- The placeholder uses existing neutral tokens (`--text-faint`,
  `--border-strong`, `--surface-tint`) with a dashed top boundary.
- The `假设` badge is outlined rather than filled with an evidence color.
- Layout uses flex wrapping and `overflow-wrap: anywhere`; it must fit the
  existing desktop and Pixel 5 viewports without horizontal page overflow.

## Error And Empty States

There is no failure path because the layer has no data source. “On” never
fabricates a relation; it always shows the explicit no-data boundary. An event
graph with zero evidence edges keeps its existing `暂无可连接的事件边。` message and
can still expose the separate hypothesis placeholder.

## Tests

Extend `frontend/tests/e2e/source-matrix.spec.ts`:

- open the existing event network;
- assert the switch is off and the placeholder body is absent;
- assert evidence-boundary copy remains visible;
- enable the switch and assert `aria-checked=true`, dashed hypothesis sample,
  `假设` badge, and honest empty text;
- assert no relation row is added to `.event-graph-evidence-list`;
- run the same assertions in desktop and mobile projects and check the section
  stays within the viewport.

Run the focused Playwright test RED before implementation, then GREEN, followed
by production build and the complete desktop/mobile E2E gate.

## Acceptance

- Fresh load is always default-off.
- Enabling the layer never changes or hides evidence edges.
- No hypothesis data or causal statement is generated.
- Visual and accessible labels both say `假设`.
- No backend/frontend contract or dependency is added.
- GitNexus impact and staged detect-changes match the two intended frontend
  files; independent review finds no unclosed Critical or Important issue.
