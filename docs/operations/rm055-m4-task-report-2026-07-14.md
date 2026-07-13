# RM-055 M4' Fact-First Briefing Implementation Plan And Task Report

> **For agentic workers:** REQUIRED SUB-SKILL: use executing-plans and
> test-driven-development task by task. Keep this checklist current as each RED,
> GREEN, review, and closeout gate completes.

Status: **COMPLETE**

Branch: `feature/academic-reading-signals`

Push/merge policy: do not push; do not merge `master`.

**Goal:** Deliver a three-minute, fact-first daily briefing that exposes its
evidence boundary, links back to the exact workbench scope, and rotates one
domain-question scaffold without making LLM access mandatory.

**Architecture:** Add one read-only backend service that derives briefing items
from persisted Topic/TopicArticle/Article/Event rows and reuses the existing
Coverage snapshot. The API and scheduled email consume the same payload. The
Discovery front page renders the payload as a non-blocking enhancement; the
existing discovery report remains available below it.

**Tech stack:** FastAPI, SQLModel, SQLite, Python stdlib, Vue 3, TypeScript,
Playwright. No new package or database table.

## Product Contract

`GET /api/briefing/latest` returns:

```json
{
  "generated_at": "ISO-8601 UTC",
  "basis": "persisted_article_metadata",
  "note": "Facts use persisted titles and source snippets; article bodies are not stored.",
  "items": [
    {
      "topic_id": 1,
      "topic_name": "Tracked topic",
      "event_id": 2,
      "article_id": 3,
      "title": "Persisted article title",
      "fact_summary": "Persisted source snippet",
      "summary_basis": "persisted_title_and_snippet",
      "source": "Source name",
      "published_at": "ISO-8601",
      "evidence_url": "https://source.example/item",
      "deep_link_path": "/?topic=1&event=2&view=contrast",
      "deep_link_url": null,
      "fulltext": {"status": "unknown", "reason": "article_bodies_not_persisted"},
      "coverage": {
        "scope": "event",
        "article_count": 4,
        "independent_source_count": 3,
        "unknown_source_article_count": 1,
        "known_language_count": 2,
        "unknown_language_article_count": 1,
        "article_ids": [3, 4, 5, 6],
        "label": "事件样本 4 篇 · 3 源（1 篇来源未知） · 2 语种（1 篇语种未知）",
        "note": "Counts describe persisted articles; absence is not proof of no reporting."
      }
    }
  ],
  "domain_today": {
    "date": "YYYY-MM-DD",
    "domain_key": "energy",
    "domain_label": "能源 / 核能 / 新能源",
    "profile_level": "unfamiliar",
    "selection_basis": "deterministic_local_profile_rotation",
    "questions": [
      "Compare official, industry, research, and community framing.",
      "Find a historical analogue and name the different conditions.",
      "Ask one domain-specific mechanism or evidence question."
    ],
    "note": "Question scaffold, not a conclusion; reading it does not mutate the cognition profile."
  }
}
```

Contract rules:

- A fact summary uses one persisted article title/snippet. Coverage describes
  the surrounding event/topic sample and must not be worded as if all sources
  support the sentence.
- Unknown source, language, and fulltext data remain explicit; zero is never
  substituted for unknown.
- Deep-link paths always use the existing `topic/event/view=contrast` contract.
  Email gets an absolute URL only when `DAILY_DIGEST_APP_URL` is configured.
- No recent persisted article means an empty item list, not stale filler.
- Domain rotation reads CognitionProfile but never writes profile or marks.
- The briefing endpoint and UI fail soft; discovery reports remain usable if the
  briefing request fails.

## Task 1: Backend Briefing Payload

**Files:**

- Create: `backend/app/services/daily_briefing.py`
- Create: `backend/tests/test_daily_briefing.py`
- Modify: `backend/app/api.py`

- [x] Read RM-055/RM-050 M4 requirements and existing discovery, email,
  Coverage, event graph, profile, and deep-link code.
- [x] Run upstream impact analysis for existing symbols. Results:
  `build_daily_digest_body` LOW (2 direct callers / 2 processes),
  `daily_email_cmd` LOW (0), and `useDiscovery` LOW (App.vue only).
- [x] Write service and endpoint tests for event-scoped facts, topic fallback,
  honest unknowns, freshness filtering, deep links, and deterministic profile
  rotation.
- [x] Run `pytest tests/test_daily_briefing.py -q` and record the expected RED
  caused by the missing service/route.
- [x] Implement the smallest read-only service and `/api/briefing/latest` route.
- [x] Run the focused backend tests to GREEN.

## Task 2: Scheduled Email Consumer

**Files:**

- Modify: `backend/app/discovery/daily_email.py`
- Modify: `backend/cli.py`
- Modify: `backend/tests/test_daily_email.py`
- Modify: `docs/operations.md`

- [x] Write tests showing fact items precede frontier seeds, coverage/fulltext
  boundaries are visible, configured absolute deep links render, and the domain
  card contains questions rather than conclusions.
- [x] Write a CLI test proving preview/send paths attach the shared briefing
  payload without making an SMTP connection.
- [x] Run focused tests and record RED for missing briefing rendering/attachment.
- [x] Implement minimal rendering and `DAILY_DIGEST_APP_URL` integration while
  preserving the old report-only fallback.
- [x] Run `pytest tests/test_daily_email.py tests/test_daily_briefing.py -q` to
  GREEN.

## Task 3: Front-Page Consumer

**Files:**

- Modify: `frontend/src/types/dossier.ts`
- Modify: `frontend/src/api/dossierApi.ts`
- Modify: `frontend/src/composables/useDiscovery.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/DiscoveryPanel.vue`
- Modify: `frontend/tests/e2e/discovery-cognition.spec.ts`

- [x] Add desktop and mobile E2E assertions for fact-first order, coverage label,
  original evidence link, workbench deep link, honest fulltext boundary, and the
  one-domain question scaffold.
- [x] Run the focused Playwright file and record RED for the missing UI/API
  consumer.
- [x] Add typed API loading as an independent enhancement that never gates the
  discovery report or deep-link parsing.
- [x] Render an unframed fact-first section with repeated evidence items and a
  sibling domain scaffold; do not nest cards.
- [x] Run frontend build and focused desktop/mobile E2E to GREEN.

## Task 4: Full Gate And Review

- [x] Run the full backend suite.
- [x] Run the frontend production build.
- [x] Run the full desktop/mobile Playwright suite.
- [x] Run `git diff --check` and verify secret/database status.
- [x] Refresh GitNexus if stale; stage only M4' files and run staged
  detect-changes with explicit repo/branch.
- [x] Obtain independent code review; fix every Critical/Important finding and
  assess Minor findings with evidence.
- [x] Commit implementation separately from roadmap/report closeout.

## Task 5: Closeout And Handoff

- [x] Update this report with RED/GREEN evidence, exact commands, commit IDs,
  residual risks, and any human decisions deferred to the end.
- [x] Update `spec/current-state.md`, `spec/roadmap.md`,
  `spec/roadmap-ledger.md`, and `spec/CHANGELOG.md` only after product acceptance.
- [x] Update local `.agent-bridge/BOARD.md` and `TO_CLAUDE.md` with the current
  truth; preserve history and never commit `.agent-bridge/`.
- [x] Run the documentation gate and commit closeout separately.

## Final Evidence And Review

- Implementation: `2fd9155 feat: add fact-first daily briefing`.
- Review repairs: `8cb9f9b fix: harden fact-first briefing review gaps` and
  `ff85f65 fix: reject malformed briefing app URLs`.
- Initial staged GitNexus scope: 13 files, 35 symbols, 8 flows, `high`; all
  mapped flows were expected discovery/email paths. Repair scopes were
  `medium` (8 files / 14 symbols / 5 flows, then 3 files / 4 symbols / 2 flows).
- Independent review first found three Important issues: LLM-enriched Chinese
  fields presented as source text, hidden unknown-source articles, and future
  timestamps displacing current facts. It also found malformed app-base URL
  fallback gaps. TDD regressions failed for each issue before the fixes.
- The final reviewer result is `APPROVE` with no Critical, Important, or Minor
  findings. Briefing facts now use original title/snippet fields only; mixed
  unknown sources are counted; future timestamps are excluded; malformed,
  non-HTTP, query, fragment, authority, and port values retain relative links.
- Final backend gate: `..\venv\Scripts\python.exe -m pytest -q` ->
  `327 passed, 1 warning`.
- Final frontend gate: `npm run build` -> 98 modules; `npm run test:e2e` ->
  `180 passed` across desktop and mobile.
- Two earlier full E2E attempts exposed pre-existing harness races rather than
  product regressions: a stale live locator after project rename and a helper
  that silently skipped topic selection after five seconds. Both failures were
  reproduced from snapshots, fixed at the harness root, repeated in isolation,
  and covered by the final 180-test pass. No assertion was weakened.
- `git diff --check` passed. Real `.env`, `dossier.db`, and `discovery.db` were
  not staged or modified; all local/ghost files remain outside commits.

Residual product boundaries remain explicit: article bodies are not persisted,
so fulltext metrics stay `unknown`; source expansion remains behind the
2026-07-27 evidence gate; no real SMTP send was attempted without user-owned
credentials and destination.

## Human Decisions Deferred To The End

None discovered yet. `DAILY_DIGEST_APP_URL` is configuration, not a product
direction decision; sends remain backward compatible when it is absent and state
that the absolute workbench link is unavailable. Source expansion and fulltext
persistence remain the already-recorded 2026-07-27 human decision gate, not an
M4' completion blocker.
