# Current State

Last updated: 2026-07-13.

This is the compact context reset point for future agents. It records current product truth, not the full work log. The previous 410-line snapshot is preserved verbatim at `spec/archive/current-state/current-state-through-2026-07-12.md`.

## Current Checkpoint

- Branch: `feature/academic-reading-signals`.
- Current implementation HEAD: `98efa59` (`dig_later` cross-device persistence).
- Current product roadmap: `RM-055`, defined in `spec/roadmap-supply-chain-2026-07-12.md` and indexed by `spec/roadmap-ledger.md`.
- Coverage API, the coverage instrument, event analogue consumer, and cross-device curiosity queue are integrated on this branch.
- Source expansion is on evidence HOLD until the two-week gate in `docs/operations/rm055-source-expansion-gate-2026-07-13.md` is satisfied.
- Next executable product stage: RM-055 M4' fact-first briefing, coverage labels, deep links, and one-domain-today.
- Do not merge to `master` or push without explicit human approval.

## RM-055 Progress

| Milestone | Status | Current truth |
|---|---|---|
| M1': optional data-line validation + analogue consumer | Done | Phase 0 report is recorded; U1 analogue UI and audit fixes are in `69ca3aa` / `29f9cf8`. |
| M2': auditable coverage | Done | Coverage API, evidence-linked distributions, honest unknowns, and the frontend instrument are live in `dfdb9c1` / `4532d02` / `29f9cf8`. |
| M3': cross-device queue | Done | Dedicated queue persistence, offline outbox, fresh-device restore, and strict cognition isolation landed in `98efa59`. |
| M3': source expansion | Evidence gate | No batch is justified yet; collect two weeks of recurring gap evidence before selecting at most three feeds. |
| M4': briefing loop | Next | Fact-first summaries, coverage micro-labels, deep links, and one-domain-today remain to implement. |

The project is at the **RM-055 M4' start point**, with source-gap observation running in parallel.

## Latest Delivered Gate

- `DigQueueItem` is a separate SQLite dataset and API; it never enters cognition summary or calibration code.
- Frontend localStorage remains the offline cache. A persisted outbox replays add/delete operations, then reconciles with the server snapshot.
- Network failure leaves the queue usable and displays a truthful degraded state; queue sync does not gate topic loading or deep links.
- Fresh verification: backend `315 passed, 1 warning`; frontend build passed (98 modules); full desktop/mobile E2E `146 passed`.
- Staged GitNexus: 9 files, 46 symbols, 5 conservatively mapped cognition-adjacent flows, risk `medium`; exact scope reviewed before commit `98efa59`.

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
- Event contrasts can link differences back to supporting articles.
- Sentiment and community layers are presented as signals rather than facts.

### Event and academic layers

- Event graph V1 and selected-event detail are implemented.
- Event analogues have a frontend consumer with explicit similarity basis, mandatory difference warnings, stable event identity, and evidence links.
- Academic discovery uses OpenAlex plus Crossref fallback/merge and records provenance and links.
- Cross-topic synthesis and discovery/cognition archive workflows exist with async job handling.

## Partial Or Missing Capabilities

- The event graph is driven by local analysis results; LLM deep-analysis output does not currently update `Event` or `EventRelation`.
- Morning briefing output is not yet a fact-first, email-linked daily loop.
- One-domain-today remains a product direction, not a finished feature.
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
315 passed, 1 warning

cd ..\frontend
npm run build
# 98 modules transformed

playwright test
# 146 passed (desktop + mobile)
```

This is recorded context, not permission to skip fresh verification after new code changes. Documentation-only work should at minimum pass link checks, UTF-8 validation, `git diff --check`, and staged GitNexus scope review.

## Read Next

1. `AGENTS.md` for engineering rules and project map.
2. `.agent-bridge/BOARD.md` for the live checkpoint and next gate.
3. `spec/roadmap-ledger.md` for authoritative roadmap status.
4. `spec/README.md` for task-specific routing.
5. `spec/acceptance.md` before any completion or release claim.

Historical sprint narration, old dirty-tree snapshots, and prior test runs belong in the archived snapshot, not in this live file.
