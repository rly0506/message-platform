# Current State

Last updated: 2026-07-12.

This is the compact context reset point for future agents. It records current product truth, not the full work log. The previous 410-line snapshot is preserved verbatim at `spec/archive/current-state/current-state-through-2026-07-12.md`.

## Current Checkpoint

- Branch: `feature/academic-reading-signals`.
- Baseline HEAD before the current uncommitted batches: `3327008`.
- Current product roadmap: `RM-050`, defined in `spec/roadmap-dual-mode-2026-07-09.md` and indexed by `spec/roadmap-ledger.md`.
- Current engineering gate: an uncommitted backend P1 stabilization batch has passed code review and produced `308 passed, 1 warning` twice. It still requires exact-file staging and staged GitNexus `detect-changes` before human final review.
- Documentation governance is being closed as a separate batch. Do not mix it with backend P1.
- Do not merge to `master`, push, or claim RM-050 complete without explicit human approval.

## RM-050 Progress

| Milestone | Status | Current truth |
|---|---|---|
| M1: dual-mode entry V1a | Done | Deep-dive queue, local marks, homepage/event deep links, and evidence positioning are in baseline commit `3327008`. |
| M2: analogy consumption | Partial | U1 backend analogue generation landed in `7922021`; the user-facing similar-precedents strip and full consumption loop remain incomplete. |
| M3: cross-device queue and sources | Not done | `dig_later` persistence and another verified official-source batch remain pending. |
| M4: briefing loop | Not done | Fact-first briefing summaries, email deep links, and one-domain-today are not a complete workflow. |

The project is in **RM-050 M2 plus a backend stabilization gate**, not at RM-050 closure.

## Backend P1 Active Gate

The accepted working-tree batch addresses:

1. preserving explicit user values in cognition profiles;
2. rejecting invalid job types in `/rerun`;
3. adding auto-refresh mutual exclusion and transactional rollback;
4. preferring fresh events in analogue candidates;
5. preventing local rule analysis from overwriting existing LLM deep analysis.

Current evidence:

- Claude completed line-by-line review and accepted the implementation.
- The same backend code and command produced `308 passed, 1 warning` twice.
- Claude withdrew the earlier claim that this batch introduced test contamination; the initial failures could not be reproduced.
- The remaining gate is exact-file staging followed by staged GitNexus `detect-changes` and human review of the reported symbols and processes.

Keep this batch separate from documentation and unrelated local changes. Its file list is recorded in `.agent-bridge/BOARD.md` and the current mailbox exchange.

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
- A local deep-dive queue connects low-friction reading to later analysis.
- Event contrasts can link differences back to supporting articles.
- Sentiment and community layers are presented as signals rather than facts.

### Event and academic layers

- Event graph V1 and selected-event detail are implemented.
- Event analogue generation exists in the backend with explicit similarity basis and difference warnings.
- Academic discovery uses OpenAlex plus Crossref fallback/merge and records provenance and links.
- Cross-topic synthesis and discovery/cognition archive workflows exist with async job handling.

## Partial Or Missing Capabilities

- The analogue backend does not yet have a complete frontend consumption loop.
- `dig_later` is not yet persisted across devices.
- The event graph is driven by local analysis results; LLM deep-analysis output does not currently update `Event` or `EventRelation`.
- Morning briefing output is not yet a fact-first, email-linked daily loop.
- One-domain-today remains a product direction, not a finished feature.
- Additional official and multilingual sources still require freshness testing and honest availability labels.
- Static public publishing and zero-backend archive search are not current product capabilities.
- Logical-form-guided graph reasoning and inspectable multi-hop answer paths are not current product capabilities.

## Known Debts

1. Test database cleanup is session-scoped and may swallow `OSError`; improve isolation or fail visibly in a separate batch.
2. Define the source of truth between local event extraction and optional LLM deep analysis before synchronizing graph rows.
3. Tighten analogue evidence granularity together with the future frontend consumer.
4. Keep source freshness and disabled/limited-source semantics explicit; never silently fall back to unavailable sources.
5. Keep hypotheses and inferred relations separate from observed evidence relations.

These debts are real but are not regressions introduced by the current backend P1 batch.

## External Architecture Inputs

User feedback, reflections, developer observations, and external project references are indexed under `spec/feedback-and-ideas/`. The 2026-07-12 publishing and reasoning review is preserved at `spec/feedback-and-ideas/references/knowledge-publishing-and-reasoning-reference-2026-07-12.md`.

- Astro/Pagefind knowledge-base pattern: useful for a future public or read-only archive through content/display separation, repository dispatch with scheduled fallback, build-time publication whitelists, and static full-text search. It must not replace the operational FastAPI workbench.
- OpenSPG/KAG: useful as a design reference for schema-constrained evidence graphs, source-to-knowledge mutual indexing, explicit query plans, and inspectable multi-hop evidence paths. Do not adopt KAG/OpenSPG during the current RM-050 gate; direct integration would add Docker, graph-platform, and LLM complexity.

Neither reference changes the no-LLM core-path constraint or creates a current roadmap item.

## Ownership And Safety Boundaries

- Human: final authority for direction, commits, merges, and releases.
- Codex: backend line and documentation governance for the current batch.
- Claude: frontend line and independent review.
- Avoid concurrent edits to the same files.
- Before editing code symbols, run GitNexus impact analysis and report high/critical risk.
- Before committing, run GitNexus `detect-changes` and verify the affected scope.
- Never write the real `backend/dossier.db` during tests or reviews.
- Never commit real secrets, proxy details, local database files, `.agent-bridge/`, or unrelated generated/local files.
- Treat `AGENTS.md` and `CLAUDE.md` working-tree GitNexus injections as outside the current documentation commit.

## Verification State

The latest accepted backend evidence is:

```text
cd backend
..\venv\Scripts\python.exe -m pytest -q
308 passed, 1 warning
```

This is recorded context, not permission to skip fresh verification after new code changes. Documentation-only work should at minimum pass link checks, UTF-8 validation, `git diff --check`, and staged GitNexus scope review.

## Read Next

1. `AGENTS.md` for engineering rules and project map.
2. `.agent-bridge/BOARD.md` for the live checkpoint and next gate.
3. `spec/roadmap-ledger.md` for authoritative roadmap status.
4. `spec/README.md` for task-specific routing.
5. `spec/acceptance.md` before any completion or release claim.

Historical sprint narration, old dirty-tree snapshots, and prior test runs belong in the archived snapshot, not in this live file.
