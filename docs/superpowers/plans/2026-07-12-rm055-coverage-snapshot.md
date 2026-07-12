# RM-055 Coverage Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate optional data lines and add an evidence-linked, no-LLM coverage snapshot API for topic and event scopes.

**Architecture:** A new read-only service selects persisted evidence and builds deterministic distributions with article IDs. A thin FastAPI route delegates to it. Phase 0 runs collectors directly and records redacted operational results without touching the real database.

**Tech Stack:** Python 3, FastAPI, SQLModel, SQLite, pytest, existing collectors.

---

### Task 1: Phase 0 operational validation

**Files:**
- Create: `docs/operations/rm055-phase0-validation-2026-07-12.md`
- Read: `backend/app/config.py`
- Read: `backend/app/collectors/rss.py`
- Read: `backend/app/pipeline/fulltext.py`
- Read: `backend/app/collectors/searxng.py`

- [ ] Capture only boolean capability flags; never print keys, proxy ports, or endpoint values.
- [ ] Run a small multilingual GNews query set and aggregate decoding methods, success, latency, and failures.
- [ ] Verify failed/disabled decoding retains a usable original URL.
- [ ] Probe Scrapling and SearXNG softly; unavailable optional services do not block Phase 1.
- [ ] Write the evidence and enable/hold recommendation to the validation report.

### Task 2: Topic coverage contract, red first

**Files:**
- Create: `backend/tests/test_coverage_snapshot.py`

- [ ] Seed topic articles spanning collectors, languages, countries, decoding states, exact registry matches, and an unmatched source.
- [ ] Assert deterministic buckets with evidence IDs, `unknown` values, `unclassified` registry rows, nullable no-GNews rate, and unknown full text.
- [ ] Run `D:\意向项目\venv\Scripts\python.exe -m pytest backend/tests/test_coverage_snapshot.py -q` and confirm the missing route fails.

### Task 3: Coverage aggregation service

**Files:**
- Create: `backend/app/services/coverage_snapshot.py`
- Test: `backend/tests/test_coverage_snapshot.py`

- [ ] Implement normalization and `{key, count, article_ids}` buckets sorted by count then key.
- [ ] Implement exact registry lookup with no heuristic fallback.
- [ ] Load topic article rows and assemble source count, distributions, GNews decoding, and unknown full-text status.
- [ ] Run focused tests until topic behavior passes.

### Task 4: Event scope and API route

**Files:**
- Modify: `backend/app/api.py`
- Modify: `backend/app/services/coverage_snapshot.py`
- Modify: `backend/tests/test_coverage_snapshot.py`

- [ ] Run GitNexus upstream impact before editing existing symbols; report HIGH/CRITICAL risk.
- [ ] Add red tests for event intersection and missing/cross-topic 404s.
- [ ] Implement event ownership validation and evidence intersection.
- [ ] Add `GET /api/topics/{topic_id}/coverage` with optional `event_id` as a thin route.
- [ ] Run the focused test file and confirm green.

### Task 5: Verification and review gate

**Files:**
- Verify: `backend/app/api.py`
- Verify: `backend/app/services/coverage_snapshot.py`
- Verify: `backend/tests/test_coverage_snapshot.py`
- Verify: `docs/operations/rm055-phase0-validation-2026-07-12.md`

- [ ] Run `D:\意向项目\venv\Scripts\python.exe -m pytest backend/tests -q`.
- [ ] Run `git diff --check` and confirm only planned RM-055 files changed.
- [ ] Run `node D:\意向项目\.gitnexus\run.cjs detect-changes --scope all` and confirm expected scope.
- [ ] Report Phase 0 evidence, API contract, test count, affected symbols, and exact staged paths before commit.
