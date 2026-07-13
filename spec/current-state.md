# Current State

Last updated: 2026-07-14.

This is the compact context reset point for future agents. It records current product truth, not the full work log. The previous 410-line snapshot is preserved verbatim at `spec/archive/current-state/current-state-through-2026-07-12.md`.

## Current Checkpoint

- Branch: `feature/academic-reading-signals`.
- Current implementation HEAD: `ff85f65` (M4' fact-first briefing plus review repairs).
- Current product roadmap: `RM-055`, defined in `spec/roadmap-supply-chain-2026-07-12.md` and indexed by `spec/roadmap-ledger.md`.
- Coverage API/instrument, event analogue consumer, cross-device curiosity queue, and fact-first briefing loop are integrated on this branch.
- Source expansion is on evidence HOLD until the two-week gate in `docs/operations/rm055-source-expansion-gate-2026-07-13.md` is satisfied.
- Next executable product stage: RM-055 Phase 3, a default-off hypothesis-layer UI placeholder that keeps evidence and inference visually separate.
- Do not merge to `master` or push without explicit human approval.

## RM-055 Progress

| Milestone | Status | Current truth |
|---|---|---|
| M1': optional data-line validation + analogue consumer | Done | Phase 0 report is recorded; U1 analogue UI and audit fixes are in `69ca3aa` / `29f9cf8`. |
| M2': auditable coverage | Done | Coverage API, evidence-linked distributions, honest unknowns, and the frontend instrument are live in `dfdb9c1` / `4532d02` / `29f9cf8`. |
| M3': cross-device queue | Done | Dedicated persistence landed in `98efa59`; revision/tombstone concurrency, causal outbox recovery, and cross-tab hardening landed in `4723b0b`. |
| M3': source expansion | Evidence gate | No batch is justified yet; collect two weeks of recurring gap evidence before selecting at most three feeds. |
| M4': briefing loop | Done | Original persisted title/snippet facts, honest coverage labels, evidence/workbench links, scheduled-email fallback, and read-only one-domain questions landed in `2fd9155`, `8cb9f9b`, and `ff85f65`. |

The project is at the **RM-055 Phase 3 start point**, with source-gap observation running in parallel and no source batch justified before 2026-07-27.

## Latest Delivered Gate

- `GET /api/briefing/latest`, the discovery front page, and scheduled email share one read-only persisted-data briefing contract; no LLM key is required.
- Facts use original article title/snippet fields, never LLM-enriched translations. Unknown source/language/fulltext data and “未采集到 ≠ 未报道” remain visible.
- Briefing loading or failure does not gate discovery reports, topic loading, or email/workbench deep links. Invalid app-base configuration falls back to relative links.
- “今日一个领域” rotates deterministic questions from CognitionProfile without changing profile or mark rows.
- Independent review ended `APPROVE` after two repair commits. Fresh verification: backend `327 passed, 1 warning`; frontend build passed (98 modules); full desktop/mobile E2E `180 passed`.
- Initial staged GitNexus was 13 files / 35 symbols / 8 flows / `high`; reviewed repair scopes were `medium` and stayed inside briefing/test flows.

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
- Event contrasts can link differences back to supporting articles.
- Sentiment and community layers are presented as signals rather than facts.

### Event and academic layers

- Event graph V1 and selected-event detail are implemented.
- Event analogues have a frontend consumer with explicit similarity basis, mandatory difference warnings, stable event identity, and evidence links.
- Academic discovery uses OpenAlex plus Crossref fallback/merge and records provenance and links.
- Cross-topic synthesis and discovery/cognition archive workflows exist with async job handling.

## Partial Or Missing Capabilities

- The event graph is driven by local analysis results; LLM deep-analysis output does not currently update `Event` or `EventRelation`.
- The Phase 3 hypothesis-layer placeholder remains unimplemented; evidence and inference must stay separate and the future hypothesis layer must default off.
- Additional official and multilingual sources still require freshness testing and honest availability labels.
- Static public publishing and zero-backend archive search are not current product capabilities.
- Logical-form-guided graph reasoning and inspectable multi-hop answer paths are not current product capabilities.

## Known Debts

1. Test database cleanup is session-scoped and may swallow `OSError`; improve isolation or fail visibly in a separate batch.
2. Define the source of truth between local event extraction and optional LLM deep analysis before synchronizing graph rows.
3. Keep source freshness and disabled/limited-source semantics explicit; never silently fall back to unavailable sources.
4. Keep hypotheses and inferred relations separate from observed evidence relations.

These debts are real but are not regressions introduced by the cross-device queue batch.

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
327 passed, 1 warning

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
