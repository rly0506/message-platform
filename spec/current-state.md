# Current State

Last updated: 2026-07-14.

This is the compact context reset point for future agents. It records current product truth, not the full work log. The previous 410-line snapshot is preserved verbatim at `spec/archive/current-state/current-state-through-2026-07-12.md`.

## Current Checkpoint

- Branch: `feature/academic-reading-signals`.
- Current implementation HEAD: `f83f2f3` (test-database isolation audit); latest product implementation remains Phase 3 at `5a53e41`.
- Current product roadmap: `RM-055`, defined in `spec/roadmap-supply-chain-2026-07-12.md` and indexed by `spec/roadmap-ledger.md`.
- Coverage API/instrument, event analogue consumer, cross-device curiosity queue, fact-first briefing loop, and the evidence/inference UI boundary are integrated on this branch.
- Source expansion is on evidence HOLD until the two-week gate in `docs/operations/rm055-source-expansion-gate-2026-07-13.md` is satisfied.
- No autonomous RM-055 product phase remains before the 2026-07-27 source/fulltext evidence gate; correctness-focused audit work continues in independent batches, with test-database isolation completed in `f83f2f3`.
- Do not merge to `master` or push without explicit human approval.

## RM-055 Progress

| Milestone | Status | Current truth |
|---|---|---|
| M1': optional data-line validation + analogue consumer | Done | Phase 0 report is recorded; U1 analogue UI and audit fixes are in `69ca3aa` / `29f9cf8`. |
| M2': auditable coverage | Done | Coverage API, evidence-linked distributions, honest unknowns, and the frontend instrument are live in `dfdb9c1` / `4532d02` / `29f9cf8`. |
| M3': cross-device queue | Done | Dedicated persistence landed in `98efa59`; revision/tombstone concurrency, causal outbox recovery, and cross-tab hardening landed in `4723b0b`. |
| M3': source expansion | Evidence gate | No batch is justified yet; collect two weeks of recurring gap evidence before selecting at most three feeds. |
| M4': briefing loop | Done | Original persisted title/snippet facts, honest coverage labels, evidence/workbench links, scheduled-email fallback, and read-only one-domain questions landed in `2fd9155`, `8cb9f9b`, and `ff85f65`. |
| Phase 3: hypothesis-layer boundary | Done | A fresh EventGraph defaults the local layer off; enabling it reveals only a neutral dashed sample, an explicit hypothesis badge, and honest no-data copy. No generated relation, persistence, API, DTO, backend, or LLM path was added (`5a53e41`). |

The project is at the **RM-055 audit and evidence-gate checkpoint**. Source-gap observation continues in parallel, no source batch is justified before 2026-07-27, and no replacement product feature should be invented merely to keep implementation moving.

## Latest Correctness Audit

- Backend pytest sessions now use unique file-backed SQLite directories; the
  shared `C:\TEMP\dossier_test.db` path and swallowed startup deletion are gone.
- Test processes ignore local `backend/.env` through a version-independent,
  process-local dotenv no-op installed before any `app.*` import.
- Session finish disposes the shared engine before cleanup, and cleanup failure
  is a visible non-zero gate result. DiscoveryStore fixtures use `tmp_path`.
- Review required three repair rounds and ended `APPROVE`. Final evidence:
  focused `8 passed`, full backend `335 passed, 1 warning`, GitNexus 5 files / 32
  symbols / 0 flows / `low`, and no real environment or database changes.

## Latest Delivered Gate

- EventGraph now exposes one accessible, component-local hypothesis-layer switch that is off on every fresh render.
- The enabled state contains no relation endpoints or causal claims: only a gray dashed sample, an explicit `假设` badge, and `尚无假设数据。证据边不会自动转成因果判断。`
- Existing evidence rows, SVG nodes, and SVG evidence edges remain unchanged when the layer is toggled; the placeholder has no persistence, API, DTO, backend, or LLM dependency.
- Independent review first requested a WCAG AA repair. The final text contrast is `5.835:1`; the evidence-preservation and mobile overflow checks were strengthened, and final review ended `APPROVE` with no findings.
- Fresh verification: frontend build passed with 98 modules; full desktop/mobile Playwright passed (`180 passed`); the exact focused test passed in both projects (`2 passed`).
- Final staged GitNexus scope was 3 files / 7 symbols / 0 flows / `low`.

## Implemented Product Capabilities

### Core collection and analysis

- FastAPI, SQLModel, and SQLite provide topic, article, source, analysis, job, and graph persistence.
- RSS/GNews/GDELT/Reddit/Hacker News and curated source paths support collection with honest degradation.
- Core collection and local analysis run without an LLM key.
- Optional LLM enrichment fails soft and must not break the no-LLM path.
- Source registry metadata exposes coverage, access state, last tested time, limitations, and state-media classification.
- Local analysis includes clustering, scoring, categorization, entities, evidence links, and source comparison signals.

### Reading and evidence workflows

- The frontend provides a workbench for topics, reports, source matrices, sentiment/community signals, academic evidence, event networks, and cognition marks.
- Deep links can open a topic, event, and contrast view.
- A cross-device deep-dive queue connects low-friction reading to later analysis and retains offline mutations locally.
- A fact-first daily briefing exposes source snippets, coverage micro-labels, original evidence, and auditable contrast deep links in UI and email.
- The event graph reserves an explicit default-off hypothesis layer without turning evidence edges into inferred or causal relations.
- Event contrasts can link differences back to supporting articles.
- Sentiment and community layers are presented as signals rather than facts.

### Event and academic layers

- Event graph V1 and selected-event detail are implemented.
- Event analogues have a frontend consumer with explicit similarity basis, mandatory difference warnings, stable event identity, and evidence links.
- Academic discovery uses OpenAlex plus Crossref fallback/merge and records provenance and links.
- Cross-topic synthesis and discovery/cognition archive workflows exist with async job handling.

## Partial Or Missing Capabilities

- The event graph is driven by local analysis results; LLM deep-analysis output does not currently update `Event` or `EventRelation`.
- Hypothesis generation, persistence, contradiction evidence, and causal relation contracts remain unimplemented by design; any future U3 work requires a separate evidence-backed roadmap decision.
- Additional official and multilingual sources still require freshness testing and honest availability labels.
- Static public publishing and zero-backend archive search are not current product capabilities.
- Logical-form-guided graph reasoning and inspectable multi-hop answer paths are not current product capabilities.

## Known Debts

1. Define the source of truth between local event extraction and optional LLM deep analysis before synchronizing graph rows.
2. Keep source freshness and disabled/limited-source semantics explicit; never silently fall back to unavailable sources.
3. Keep hypotheses and inferred relations separate from observed evidence relations.

The former shared test-database cleanup debt was resolved in `f83f2f3`; the
remaining debts are product or architecture boundaries and should not be mixed
into test-infrastructure batches.

## External Architecture Inputs

User feedback, reflections, developer observations, and external project references are indexed under `spec/feedback-and-ideas/`. The 2026-07-12 publishing and reasoning review is preserved at `spec/feedback-and-ideas/references/knowledge-publishing-and-reasoning-reference-2026-07-12.md`.

- Astro/Pagefind knowledge-base pattern: useful for a future public or read-only archive through content/display separation, repository dispatch with scheduled fallback, build-time publication whitelists, and static full-text search. It must not replace the operational FastAPI workbench.
- OpenSPG/KAG: useful as a design reference for schema-constrained evidence graphs, source-to-knowledge mutual indexing, explicit query plans, and inspectable multi-hop evidence paths. Do not insert KAG/OpenSPG into RM-055 without a separate evidence-backed decision; direct integration would add Docker, graph-platform, and LLM complexity.

Neither reference changes the no-LLM core-path constraint or creates a current roadmap item.

## Ownership And Safety Boundaries

- Human: final authority for direction, commits, merges, and releases.
- Codex: cross-layer implementation and documentation governance while Claude is offline, by explicit human authorization.
- Claude: independent review and frontend collaboration when available; handoff is maintained in `TO_CLAUDE.md`.
- Avoid concurrent edits to the same files.
- Before editing code symbols, run GitNexus impact analysis and report high/critical risk.
- Before committing, run GitNexus `detect-changes` and verify the affected scope.
- Never write the real `backend/dossier.db` during tests or reviews.
- Never commit real secrets, proxy details, local database files, `.agent-bridge/`, or unrelated generated/local files.
- Treat `AGENTS.md` and `CLAUDE.md` working-tree GitNexus injections as outside the current documentation commit.

## Verification State

The latest accepted release-quality evidence is:

```text
cd backend
..\venv\Scripts\python.exe -m pytest -q
# 335 passed, 1 warning after the test-database isolation audit

cd ..\frontend
npm run build
# 98 modules transformed

playwright test
# 180 passed (desktop + mobile)
```

This is recorded context, not permission to skip fresh verification after new code changes. Documentation-only work should at minimum pass link checks, UTF-8 validation, `git diff --check`, and staged GitNexus scope review.

## Read Next

1. `AGENTS.md` for engineering rules and project map.
2. `.agent-bridge/BOARD.md` for the live checkpoint and next gate.
3. `spec/roadmap-ledger.md` for authoritative roadmap status.
4. `spec/README.md` for task-specific routing.
5. `spec/acceptance.md` before any completion or release claim.

Historical sprint narration, old dirty-tree snapshots, and prior test runs belong in the archived snapshot, not in this live file.
