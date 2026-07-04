# Spec Changelog

## 2026-07-04

### Acceptance Ledger Status Cleanup

- Cleaned stale #2 wording in the acceptance ledger and current-state handoff:
  - backend-running auto-refresh is now recorded as implemented and verified in the latest gate;
  - the remaining #2 action is Claude's explicit `ready for human final review: yes/no` plus human final review;
  - #3 mainstream source expansion and #10 academic second-source breadth remain open.
- No business code changed.

### Verification

```powershell
rg -n "still needs to implement|implementation remain|can become `Done` after implementation|backend auto-refresh work|backend auto-refresh,|final-green|#2 backend auto-refresh" spec/14-point-acceptance-2026-07-04.md spec/current-state.md spec/14-point-remaining-decisions-2026-07-04.md .agent-bridge/BOARD.md
git diff --check -- spec/14-point-acceptance-2026-07-04.md spec/current-state.md spec/CHANGELOG.md
```

### Full Gate After Auto-Refresh Frontend Wiring

- Reran the main acceptance gate after the auto-refresh frontend status UI and e2e were added.
- Reindexed GitNexus because `status` initially reported a stale index at `8731f0e` while the current commit was `d028496`.
- The refreshed `detect-changes` result is now risk `medium`, not the earlier stale-index result; it reports one affected execution flow and no high/critical warning.
- Kept the sprint open: source expansion (#3), academic second source (#10), and Claude semantic/source reviews (#6/#7/#8/#11/#13) remain unresolved despite the green gate.

### Verification

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings in 39.31s`.
- `cd frontend; npm run build` -> passed.
- `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
- `git diff --check` -> pass with existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`.
- `node .gitnexus/run.cjs analyze` -> repository indexed successfully; FTS extension unavailable warning only.
- `node .gitnexus/run.cjs status` -> index up-to-date at current commit `d028496`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `medium`, `16 files`, `45 symbols`, `1` affected execution flow (`RunCrossSynthesis -> FetchCrossSynthesis`).

### Auto-Refresh Frontend Status

- Wired the frontend to the backend auto-refresh status API:
  - `GET /api/auto-refresh/status` is shown in the topic summary area;
  - `POST /api/auto-refresh/run` can be triggered from the same status strip;
  - status shows enabled/running state, last finish time, news refresh count, frontier refresh, skipped active jobs, and per-topic errors;
  - failures are displayed inline without breaking topic reading.
- Kept the existing stale-topic manual collection fallback. The auto-refresh run button does not rewrite the search box, switch topics, or drop the current topic context.
- Kept the sprint open: #2 still needs Claude line-1 backend final verification and a full sprint gate before final-green; #3/#10/#11/#13 remain unresolved.

### Verification

- `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/App.vue" --direction upstream --include-tests` -> risk `LOW`.
- `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/api/dossierApi.ts" --direction upstream --include-tests` -> risk `MEDIUM`.
- `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/types/dossier.ts" --direction upstream --include-tests` -> risk `MEDIUM`.
- `node .gitnexus/run.cjs impact -r message-platform "File:frontend/tests/e2e/source-matrix.spec.ts" --direction upstream --include-tests` -> risk `LOW`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "auto-refresh status"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `15 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `26 passed`.
- `cd frontend; npm run build` -> passed.
- `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
- `git diff --check -- frontend/src/App.vue frontend/src/api/dossierApi.ts frontend/src/types/dossier.ts frontend/src/style.css frontend/tests/e2e/source-matrix.spec.ts` -> pass with existing LF/CRLF warnings only.

### Auto-Refresh Backend Review

- Reviewed the backend-running auto-refresh implementation that is now present in the working tree:
  - `backend/app/services/auto_refresh.py`
  - `backend/app/config.py`
  - `backend/app/api.py`
  - `backend/tests/test_auto_refresh.py`
- Verified the core behavior:
  - stale active topics are refreshed with `collect_topic(... use_curated_feeds=True)` followed by local `analyze_topic(... persist=True)`;
  - empty/fresh/archived topics are skipped;
  - active jobs cause topic skip;
  - frontier refresh uses `run_and_save(annotate=False)`;
  - no LLM/OpenCLI/academic/sentiment/cross-synthesis auto-run path is exercised in tests.
- Sent review notes to `.agent-bridge/TO_CLAUDE.md` instead of editing Claude-owned backend files:
  - topic-level auto-refresh failures are isolated but not yet exposed in status;
  - synchronous `refresh_once()` can return a snapshot with `running=True`.
- Claude later fixed both review findings:
  - topic-level failures now surface through `news_errors`;
  - synchronous `refresh_once()` returns after `running=False`.

### Verification

- `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/services/auto_refresh.py" --direction upstream --include-tests` -> target not indexed yet, risk `UNKNOWN`.
- `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/api.py" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
- `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/config.py" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
- `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_auto_refresh.py -q` -> `8 passed`.
- `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_api_helpers.py tests/test_discovery.py tests/test_source_registry.py -q` -> `56 passed`.
- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings`.
- `git diff --check -- backend/app/config.py backend/app/api.py backend/app/services/auto_refresh.py backend/tests/test_auto_refresh.py` -> pass with existing LF/CRLF warning only.

### 14-Point Sprint Decision Update

- Updated the 14-point acceptance and remaining-decision documents after the latest Claude inbox:
  - #2 now records the human decision to implement option B, backend-running auto refresh for news/frontier;
  - #3 no longer closes as an accepted V1 limitation, because the human requested broader mainstream source expansion;
  - #3 now requires classified source expansion that distinguishes fresh public RSS from paywalled, API/license-only, stale-RSS, summary-only, or Google-News-proxy-only sources.
- Wrote the updated split plan to `.agent-bridge/TO_CLAUDE.md` and synced `.agent-bridge/BOARD.md`.
- No business code changed in this coordination update.

### Verification

- Read latest `.agent-bridge/TO_CODEX.md`, `.agent-bridge/BOARD.md`, `spec/14-point-acceptance-2026-07-04.md`, and `spec/14-point-remaining-decisions-2026-07-04.md`.
- Ran quick source availability checks for WSJ/Guardian/AFP/Xinhua-style feeds to inform the classification plan; results are recorded in `spec/14-point-remaining-decisions-2026-07-04.md`.

### Academic Source Scope Boundary

- Added a visible academic source-scope note to the Academic panel:
  - current academic sample is OpenAlex;
  - academic review citations must keep author, year, venue, DOI or source link;
  - literature network only shows sample-internal citations and does not represent the full academic lineage.
- Kept #10 strict: this does not add Crossref/Semantic Scholar/arXiv and does not make OpenAlex-only final-green.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/components/AcademicPanel.vue" --direction upstream --include-tests` -> risk `LOW`, direct upstream `App.vue`.
- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/tests/e2e/academic-panel.spec.ts" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
- `cd frontend && npm run test:e2e -- --project=desktop academic-panel.spec.ts -g "priority-reading"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop academic-panel.spec.ts` -> `2 passed`.
- `cd frontend && npm run build` -> passed.

### Source Manager Coverage Mix

- Added a visible source mix summary to the source manager:
  - quality-tier mix, ordered by source quality tier such as `wire`, `professional`, `mainstream`, `newsletter`, `research`, and `user`;
  - source-type mix such as `rss`.
- This strengthens #3's user-facing explanation for "why did media resources become fewer" by making the current source composition inspectable beside total/enabled/failed counts and latest success time.
- Kept the limitation explicit: this is source-status transparency, not full crawler coverage or same-event G20 reporting.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/App.vue" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
- `cd frontend && npm run test:e2e -- --project=desktop source-registry.spec.ts -g "coverage mix"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `6 passed`.
- `cd frontend && npm run build` -> passed.

### Source-Ingestion Guide V1

- Added a visible source-ingestion guide to the source manager:
  - RSS / Newsletter / Google Alerts feed URLs enter the source registry and local pre-analysis path;
  - B站视频 / webpage links are treated as V1 leads or platform samples, not full video-transcript ingestion;
  - failed-source causes remain visible in the source status table.
- Kept the boundary explicit for #13: this improves the user-facing ingestion path, but does not implement Bilibili transcript review, Filo Mail integration, or a general web crawler.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/App.vue" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/tests/e2e/source-registry.spec.ts" --direction upstream --include-tests` -> target not found in index; treated as e2e-only verification target.
- `cd frontend && npm run test:e2e -- --project=desktop source-registry.spec.ts -g "source-ingestion path"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `5 passed`.
- `cd frontend && npm run build` -> passed.

### Codex High-Risk Frontend Retest After Latest Inbox Read

- Reread the latest `TO_CODEX.md`, acceptance matrix, remaining-decision packet, and current-state snapshot.
- Confirmed there was no new Claude decision after the #5/#2 freshness letter.
- Rechecked the Codex-owned high-risk frontend paths without touching backend/source/academic files:
  - parent-context drilldown and selected-event drilldown;
  - stale refresh context;
  - media stance trend and small-sample downgrade;
  - event network semantics and selected-node inline detail;
  - LLM-refresh reuse;
  - sentiment timeline/OpenCLI diagnostics;
  - cognition cards.
- Kept the sprint open because the remaining blockers are still #2 backend auto-refresh, #3/#13 source scope, #6/#7/#8 semantic acceptance, and #10/#11 academic source breadth.

### Verification

- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `25 passed (49.2s)`.

### Stage 5 Full Gate Refresh

- Reran the stage-5 verification gate for the current 14-point integration tree.
- Updated `spec/14-point-acceptance-2026-07-04.md` and `spec/current-state.md` with fresh pass counts.
- Updated `spec/14-point-remaining-decisions-2026-07-04.md` to use the same fresh pass counts.
- Added a `Final Status Projection` table to both the acceptance matrix and remaining-decision packet so reviewers can see which items are decision-bound rather than test-bound.
- Kept the sprint open because the remaining blockers are still product-scope decisions/reviews:
  - #2 backend auto-refresh A/B/C;
  - #3/#13 source-ingestion V1 scope;
  - #6/#7/#8 Claude semantic review;
  - #10/#11 second academic source versus OpenAlex-only V1 limitation.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings in 13.40s`.
- `cd frontend && npm run build` -> passed (`vue-tsc -b && vite build`; built in 396ms).
- `cd frontend && npm run test:e2e -- --workers=1` -> `76 passed (2.3m)`.
- `git diff --check` -> exit 0, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
- `node .gitnexus/run.cjs status` -> index up-to-date at current commit `8731f0e`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; broad cumulative 14-point integration tree.

### Codex Frontend Focused Retest After Bridge Plan

- Rechecked the Codex-owned high-risk frontend paths after reading the latest Claude inbox and writing the auto-refresh split plan back to `TO_CLAUDE.md`.
- Coverage included parent-context drilldown, selected-event drilldown, stale refresh context, media stance trend and small-sample downgrade, event network semantics, selected-node inline detail, LLM-refresh reuse, sentiment timeline/OpenCLI diagnostics, and cognition cards.
- Updated `spec/14-point-acceptance-2026-07-04.md` and `spec/current-state.md` with the fresh evidence.
- Kept the sprint open: #2 backend auto-refresh, #10 academic second source/OpenAlex-only decision, and #3/#13 source scope still require human/Claude decisions.
- Added a short `Human Decision Brief` to `spec/14-point-remaining-decisions-2026-07-04.md` so the remaining choices can be answered without rereading the full packet.
- Synced `.agent-bridge/BOARD.md` with the latest 14-point sprint truth so Claude/Codex do not continue from the older 2026-07-03 goals.

### Verification

- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `25 passed (49.3s)`.
- `git diff --check -- spec/14-point-remaining-decisions-2026-07-04.md spec/CHANGELOG.md` -> exit 0.
- `git diff --check -- spec/current-state.md .agent-bridge/TO_CLAUDE.md` -> exit 0.

### Source And Academic Read-Only Evidence Audit

- Extended `spec/14-point-remaining-decisions-2026-07-04.md` with Codex's read-only evidence audit for #3/#10/#11/#13.
- Evidence reviewed:
  - source registry service, feed registry, curated feeds, source registry backend tests, and source-registry e2e;
  - academic pipeline, academic backend tests, academic UI, and academic e2e.
- Conclusions:
  - #3 has enough evidence for `V1 Done with known limitation` if full crawler/paywalled exclusives/G20 same-event coverage are deferred;
  - #10 metadata/prompt/UI is V1-ready, but source breadth remains OpenAlex-only;
  - #11 UI readability is V1-ready but inherits #10's source limitation;
  - #13 RSS/newsletter/Google Alerts import is V1-ready if video ingestion is deferred.
- GitNexus MCP resource read failed with MCP startup handshake failure in this session; this was a read-only audit using current files/tests instead.

### Verification

- `git diff --check -- spec/14-point-remaining-decisions-2026-07-04.md spec/14-point-acceptance-2026-07-04.md spec/current-state.md spec/CHANGELOG.md .agent-bridge/TO_CLAUDE.md` -> exit 0.

### Remaining Decision Packet

- Added `spec/14-point-remaining-decisions-2026-07-04.md` as the decision packet for the open 14-point sprint blockers.
- The packet turns the remaining #2/#3/#6/#7/#8/#10/#11/#13 blockers into explicit options, recommended decisions, known limitations, final status mapping, and ownership boundaries.
- Linked the packet from `spec/README.md`, `spec/current-state.md`, and `spec/14-point-acceptance-2026-07-04.md`.

### Verification

- `git diff --check -- spec/14-point-remaining-decisions-2026-07-04.md spec/README.md spec/current-state.md spec/14-point-acceptance-2026-07-04.md spec/CHANGELOG.md .agent-bridge/TO_CLAUDE.md` -> exit 0.

### Codex Semantic Self-Audit

- Ran a focused semantic scan over Codex-owned media, event-network, sentiment, and cognition UI copy/tests.
- Confirmed the current UI boundaries for #6/#7/#8:
  - media stance timeline is framed as `报道样本` and explicitly says it does not represent public opinion;
  - small media samples downgrade to distribution-only with `当前样本只能显示立场分布`;
  - sentiment timeline is labeled `样本趋势，非事实时间线`, with `小样本线索` for tiny buckets;
  - event network is labeled `本地证据边，不显示 LLM 因果假设`;
  - narrative convergence remains `不代表事实真假或操控判定`.
- Kept Claude semantic review open; this is Codex self-audit evidence, not independent acceptance.

### Verification

- `rg -n "导致|证明|根因|因果" frontend/src/components frontend/tests/e2e spec/14-point-acceptance-2026-07-04.md spec/current-state.md` -> matches only negative/boundary wording for `因果`.
- `rg -n "不代表|非事实|样本趋势|小样本|本地证据边|不显示 LLM 因果假设|当前样本只能|占比" frontend/src/components/MediaPanel.vue frontend/src/components/SentimentPanel.vue frontend/tests/e2e/source-matrix.spec.ts frontend/tests/e2e/sentiment-panel.spec.ts` -> found the expected boundary copy and test assertions.

### Completion Audit Clarification

- Added a `Completion Audit - Still Open` section to `spec/14-point-acceptance-2026-07-04.md`.
- Clarified that the fresh full gate is green, but sprint completion remains open because of decision/review items rather than missing Codex-owned frontend evidence:
  - #2 backend auto-refresh option;
  - #3 news/source quality scope;
  - #6/#7/#8 pseudo-trend and pseudo-causality review;
  - #10 second academic source or human-accepted OpenAlex-only V1 limitation;
  - #11 literature-network source hygiene;
  - #13 source-ingestion scope.
- Updated `spec/current-state.md` with the same completion boundary so future agents do not loop on already-passing tests.

### Verification

- `git diff --check -- spec/14-point-acceptance-2026-07-04.md spec/current-state.md spec/CHANGELOG.md .agent-bridge/TO_CLAUDE.md` -> exit 0.

### Fresh Full Gate Rerun

- Reran the sprint-level acceptance gate after the latest Codex frontend retest.
- The gate strengthens the evidence for the integrated 14-point repair tree, but it does not close remaining product decisions:
  - #2 backend auto-refresh still needs the human A/B/C decision;
  - #3/#10/#11/#13 still need Claude review or implementation for source/academic/source-ingestion scope.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings in 22.21s`.
- `cd frontend && npm run build` -> passed.
- `cd frontend && npm run test:e2e -- --workers=1` -> `76 passed (2.3m)`.
- `git diff --check` -> exit 0, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; expected for the broad cumulative 14-point repair integration tree.

### Codex Frontend Retest

- Reran the Codex-owned frontend acceptance slice for the 14-point sprint:
  - project/topic CRUD;
  - contextual drilldown with parent topic context;
  - stale refresh using the current topic context;
  - media stance trend evidence and small-sample downgrade;
  - event network and selected-node inline detail;
  - LLM analysis retained after single-panel refresh;
  - sentiment timeline/OpenCLI diagnostics UI;
  - cognition cards, report connection, and deeper path.
- This refresh strengthens the evidence for #1/#2/#4/#6/#7/#8/#9/#12, but it does not close backend/source/academic decisions.

### Verification

- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `31 passed` in 49.8s.

### Acceptance Ledger Status Cleanup

- Updated `spec/14-point-acceptance-2026-07-04.md` after the fresh recorded full-gate evidence:
  - #1, #4, and #9 now use plain `Done` instead of `Done, pending final full gate`;
  - #12 now uses `V1 Done with known limitation`, with long-term profile calibration kept as future work;
  - #5 now explicitly separates the completed Windows OpenCLI runner/diagnostics fix from platform-login/session failures that may remain `Blocked by external account/API`.
- Refreshed the dirty worktree snapshot in `spec/current-state.md` so the newly added acceptance ledger is visible in the frozen state.
- Kept the sprint open: #2 backend auto-refresh still requires the human A/B/C decision, and #3/#10/#11/#13 still require Claude review or implementation.

### Verification

- `git diff --check -- spec/14-point-acceptance-2026-07-04.md spec/CHANGELOG.md spec/current-state.md` -> exit 0.
- `rg -n "pending final full gate|Needs final full gate" spec/14-point-acceptance-2026-07-04.md` -> no matches.

### Academic UI Verification Boundary

- Reverified the Codex-owned frontend side of #10/#11 without changing backend collectors:
  - academic paper cards expose authors/citation text, year, venue, DOI link, and OpenAlex link;
  - priority-reading signals remain neutral (`高引用`, `新近`, `样本内奠基`, `venue明确`, `低信息`);
  - literature network renders readable nodes and explicit `引用` edges instead of an unreadable citation-chip graph.
- Kept the source limitation explicit: the academic collector is still OpenAlex-only until Claude adds a second source path or asks the human to accept that V1 limitation.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/components/AcademicPanel.vue" --direction upstream --include-tests` -> risk `LOW`, direct upstream `App.vue`.
- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/tests/e2e/academic-panel.spec.ts" --direction upstream --include-tests` -> risk `LOW`, direct upstream `0`.
- `cd frontend && npm run test:e2e -- --project=desktop academic-panel.spec.ts` -> `2 passed`.
- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_academic_layer.py -q` -> `12 passed, 3 warnings`.
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings`.
- `cd frontend && npm run test:e2e -- --workers=1` -> `76 passed`.
- `cd frontend && npm run build` -> passed.
- `git diff --check` -> exit 0, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db` -> no output.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; expected for the broad cumulative 14-point repair integration tree.

### Media Stance Share Trend

- Strengthened the media stance timeline for the 14-point sprint:
  - each major trend now shows article-count change and sample-share change, for example `占比 0% → 56%`;
  - the trend card still shows turning period, driving sources, and representative reports;
  - tiny samples downgrade to distribution-only instead of presenting a false trend;
  - wording remains limited to media-report samples, not full public opinion.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/components/MediaPanel.vue" --direction upstream --include-tests` -> risk `LOW`, direct upstream `App.vue`.
- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/tests/e2e/source-matrix.spec.ts" --direction upstream --include-tests` -> risk `LOW`, direct upstream `0`.
- `cd frontend && npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "summarizes media stance"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "degrades media stance"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `14 passed`.
- `cd frontend && npm run build` -> passed.

### Sentiment Timeline Small-Sample Marker

- Strengthened the community sentiment timeline for #6:
  - timeline buckets with fewer than 3 samples now show `小样本线索`;
  - the timeline still keeps platform, time bucket, sample count, confidence, dominant frame, sentiment label, and representative posts visible;
  - this keeps partial community signals inspectable without pretending they are broad public-opinion trends.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/components/SentimentPanel.vue" --direction upstream --include-tests` -> risk `LOW`, direct upstream `App.vue`.
- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/tests/e2e/sentiment-panel.spec.ts" --direction upstream --include-tests` -> risk `LOW`, direct upstream `0`.
- `cd frontend && npm run test:e2e -- --project=desktop sentiment-panel.spec.ts -g "sentiment change timeline"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop sentiment-panel.spec.ts` -> `3 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts source-registry.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `35 passed`.
- `cd frontend && npm run build` -> passed.

### Freshness Stale-State Warning

- Added a frontend stale-state warning for old topic data:
  - labels `latest_published_at` as the local last collected time when it is older than the freshness threshold;
  - explicitly says this does not mean the outside world has no newer reports;
  - provides a manual `刷新采集` fallback that reuses the existing search/collection action.
- Fixed the manual fallback to use the current topic query/name explicitly, so a residual value in the search box cannot refresh the wrong topic.
- This does not implement backend auto-refresh. The backend scheduling direction still requires the human A/B/C decision from the 14-point sprint plan.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/App.vue" --direction upstream --include-tests` -> risk `LOW`, direct upstream `0`.
- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/tests/e2e/source-matrix.spec.ts" --direction upstream --include-tests` -> risk `LOW`, direct upstream `0`.
- `cd frontend && npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "explains stale"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "refreshes stale"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `13 passed`.
- `cd frontend && npm run build` -> passed.

### Source Manager Status Summary

- Added a frontend source-manager summary for the active 14-point sprint:
  - total registered sources;
  - enabled source count;
  - failed source count;
  - latest successful fetch time;
  - up to three failed-source reasons.
- Kept this as a UI explainability slice only. It does not claim that news-source quality, same-event G20 coverage, or crawler expansion is final; those remain under Claude review for #3.

### Verification

- `node .gitnexus/run.cjs impact --repo message-platform "File:frontend/src/App.vue" --direction upstream --include-tests` -> risk `LOW`, direct upstream `0`.
- `cd frontend && npm run test:e2e -- --project=desktop source-registry.spec.ts -g "summarizes source coverage"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `4 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts source-registry.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `32 passed`.
- `cd frontend && npm run build` -> passed.

### 14-Point Sprint Acceptance Ledger

- Added `spec/14-point-acceptance-2026-07-04.md` as the active acceptance ledger for the 14-point feedback repair sprint.
- Updated `spec/current-state.md` and `spec/README.md` to point future agents to the ledger before relying on older audit summaries.
- The ledger explicitly keeps freshness/automatic update as pending human decision and source/academic items as pending Claude review, so the sprint is not accidentally declared complete from targeted frontend evidence.
- Tightened #10 after code inspection: the academic layer still calls OpenAlex as the only paper collector, so the user's "OpenAlex 是否单薄" concern remains pending Claude implementation/review unless the human accepts it as a known limitation.
- Added event-detail contextual drilldown: the selected event inline detail now shows `继续下钻` / `历史相似` chips and reuses the existing parent-context search behavior.

### Verification

- `git diff --check -- spec/14-point-acceptance-2026-07-04.md` -> exit 0.
- `rg -n "Crossref|Semantic Scholar|arXiv|OpenAlex" backend frontend/src spec backend/config -S` and source inspection confirmed arXiv is used for discovery/frontier, not as a second academic-layer collector.
- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts -g "selected event detail"` -> red first, then `1 passed`.
- `cd frontend && npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts` -> `13 passed`.
- `cd frontend && npm run build` -> passed.

### Independent Follow-Up Audit

- Addressed Claude's independent audit findings on the 14-point repair tree:
  - fixed async topic switching races for academic, sentiment, and cross-synthesis jobs;
  - fixed discovery timeline tree item selection so branches over the display limit keep the latest report run;
  - changed event-network shared evidence edges from directional arrows to symmetric links.
- Added regression coverage:
  - `frontend/tests/e2e/job-topic-race.spec.ts`
  - `backend/tests/test_discovery.py::test_timeline_tree_items_prefer_latest_runs_when_branch_exceeds_limit`
  - stronger event-network edge assertions in `frontend/tests/e2e/source-matrix.spec.ts`
- Updated audit reports to replace the earlier "no new bug found" conclusion with the independent follow-up result.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `198 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- --workers=1` -> `62 passed`
- `git diff --check` -> exit 0, with existing LF-to-CRLF warnings only
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `261 symbols`, `75` affected processes; still explained as cumulative 14-point repair scope plus follow-up fixes
- `git status --short -- backend/.env backend/dossier.db` -> no output

## 2026-07-03

### Audit

- Added whole-repository self-audit deliverables:
  - `spec/self-audit-2026-07-03.md`
  - `spec/debug-audit-2026-07-03.md`
  - `spec/redundancy-audit-2026-07-03.md`
  - `spec/regression-audit-2026-07-03.md`
  - `spec/final-audit-2026-07-03.md`
- Confirmed the 14 feedback items have code, UI, and test evidence or documented V1 residual risk.
- Ran a systematic debug pass over search/local analysis, deep analysis/evidence package, academic/OpenAlex, sentiment/OpenCLI/HN/Reddit, cross-synthesis reuse, and project/topic CRUD.
- Chose not to apply business-code refactors during Phase 3 because the current repair diff is already large and core search impact is GitNexus CRITICAL.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `197 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- --workers=1` -> `56 passed`
- `git diff --check` -> exit 0, with existing LF-to-CRLF warnings only
- `node .gitnexus/run.cjs status` -> index up-to-date at `8731f0e`
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `45 files`, `253 symbols`, `68` affected processes; explained as cumulative 14-point repair scope
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Documentation

- Added `spec/current-state.md` as the context reset point for future agents:
  - records the current product positioning;
  - separates implemented, partially implemented, deferred, and current working-tree items;
  - captures the latest verification baseline without treating it as future proof;
  - names the next iteration candidates.
- Updated `spec/README.md` so `spec/current-state.md` is read immediately after `AGENTS.md`.
- Updated `spec/project.md` to reflect the shift from an event-intelligence desk toward a cognition-expansion workbench.
- Updated `spec/roadmap.md` to point to the context reset document and to preserve the narrative-calibration positioning.

### Verification

- `git diff --check` -> exit 0, with existing LF-to-CRLF warnings only.
- `git status --short` -> confirmed this cleanup only added/changed `spec/` docs on top of the existing uncommitted implementation files.

### Added

- Implemented cognition-profile calibration V1:
  - expanded local cognition profile fields with `depth`, `interest`, `confidence`, `evidence`, and `recommended_seed_style`;
  - added a broader default domain universe covering AI infrastructure, finance, macro finance, open source, energy/electricity, biotech, crypto, geopolitics, industrial policy, law/regulation, social structure, engineering infrastructure, and media literacy;
  - kept `level` and `note` compatible with existing profile rows;
  - added lightweight SQLite column migration and per-domain backfill for legacy profile rows.
- Strengthened the discovery boundary queue:
  - ranks seeds with local profile fields instead of only fixed keyword order;
  - shows profile evidence and confidence on each boundary card;
  - adds local workflow prompts such as mechanism tracing, financial-model checks, macro liquidity framing, risk checks, paper checks, project evaluation, and rhetoric-pressure checks.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_cognition_marks.py -q` -> `7 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `177 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- discovery-cognition` -> `10 passed`
- `cd frontend && npm run test:e2e` -> `30 passed`

### Planning

- Added the next cognition direction to `spec/roadmap.md`:
  - cognition-profile calibration should be repeated and lightweight, not a single long questionnaire;
  - each profile item should track `depth`, `interest`, `confidence`, `evidence`, and `recommended_seed_style`;
  - the profile must be calibrated by later behavior such as `我懂了`, `存疑`, `深入`, skipped domains, and repeated interests;
  - future calibration should use a domain universe instead of only the current AI/finance/geopolitics core.
- Defined a layered domain-universe planning target:
  - intelligence core: AI infrastructure, open-source ecosystems, finance/accounting, macro finance, energy/electricity, geopolitics/industrial policy, media literacy;
  - expansion layer: law/regulation, social structure/demographics, science foundations, biotech/health, cybersecurity/defense, culture/media, organization/management;
  - naturalist layer: geography/resources, history/institutions, philosophy/thought history, anthropology/social psychology, engineering/infrastructure.
- Kept the calibration target non-diagnostic:
  - no scores;
  - no personality labels;
  - no claim that a short test fully maps the user;
  - use the result as editable recommendation evidence only.

### Added

- Implemented discovery report archive V1:
  - added read-only backend archive APIs for report list, report detail, and local timeline tree;
  - kept `/api/discovery/latest` unchanged while reusing the same safe report reader;
  - frontend now shows a compact archive selector in the intelligence desk;
  - selecting an older report loads archived markdown/seeds without starting a new discovery job.
- Implemented local cognition timeline tree V1:
  - groups archived discovery seeds across reports by local domain evidence;
  - only emits branches with evidence from at least two report run IDs;
  - caps visible branch items and keeps at least two run IDs visible when a branch qualifies;
  - labels the panel as local similarity, not a causal chain.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_discovery.py -q` -> `38 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `175 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- discovery-cognition` -> `8 passed`

### Planning

- Strengthened the next product direction around a **local-first intelligence desk**:
  - historical `认知前沿日报` should be browsable instead of only showing the latest report;
  - `认知时间树` should connect seeds/events across days with local evidence before any LLM explanation;
  - no-LLM mode should support useful classification, collection, archive browsing, query/search, and evidence retrieval.
- Updated `spec/roadmap.md`:
  - current priority now names the local-first intelligence desk foundation;
  - near-term work includes discovery archive V1, local cognition timeline tree V1, and local query/search direction;
  - local capability boundary is treated as a product target, not only a warning label.
- Updated `spec/discovery-archive-cognition-timeline-design.md`:
  - added `Local-First Operating Mode`;
  - added local-mode acceptance criteria;
  - clarified that local branches use evidence such as domain, domain label, source/domain, URL reuse, keyword overlap, and repeated signals.
- Updated `spec/local-capability-boundary.md`:
  - reframed no-LLM mode as a usable local intelligence workbench;
  - added local archive, classification, cross-day connection, query/filter, and partial-result preservation goals.

### Verification

- Documentation-only change.
- `git diff --check` -> exit 0.

## 2026-07-02

### Fixed

- Clarified the Media-tab event structure tree semantics:
  - renamed the misleading `触发/行动` node to `入选/归类依据`;
  - keeps the node tied to event classification / selection basis, not causal triggers;
  - adds an always-visible caveat that the node does not represent the event trigger cause;
  - adds panel-level copy that nodes are parallel reading slices, not a timeline or causal chain;
  - makes source-matrix branch details include the actual branch label.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/MediaPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/tests/e2e/source-matrix.spec.ts" -d upstream --include-tests` -> risk LOW, no upstream dependents
- `cd frontend && npm run test:e2e -- source-matrix` -> RED after test update, missing new boundary copy
- `cd frontend && npm run test:e2e -- source-matrix` -> RED after first implementation, node caveat only existed on fallback path
- `cd frontend && npm run test:e2e -- source-matrix` -> `14 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `24 passed`
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk LOW, 5 files, 7 symbols, 0 affected processes
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Planning

- Added `spec/discovery-archive-cognition-timeline-design.md`:
  - records the user request that `认知前沿日报` should expose older dates, not only the latest report;
  - records the next design direction for a local-first `认知时间树` that links today's seeds/events with previous daily reports;
  - keeps V1 read-only and archive-first, with optional LLM explanations deferred until local links are useful;
  - requires every cross-day link to show evidence and avoid causal language.
- Updated `spec/README.md` to link the new design note.
- Updated `spec/roadmap.md`:
  - added discovery archive V1 as a near-term candidate;
  - added cross-day cognition timeline tree as design-first work;
  - clarified that the immediate code candidate before new features is the event-structure semantic fix.

### Verification

- `git diff --check` -> exit 0
- `git status --short` -> only `spec/` documents changed

### Added

- Implemented Media-tab event structure tree V1:
  - added a default-collapsed `事件结构树` panel derived only from existing frontend payload data;
  - groups the selected event into current node, trigger/action, source-matrix branches, narrative similarity, key objects, and stance changes when data exists;
  - keeps a boundary note that the structure is a reading aid, not a causal judgement;
  - no backend/API/DTO/LLM changes.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/MediaPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- source-matrix` -> RED before implementation, missing `事件结构树`
- `cd frontend && npm run test:e2e -- source-matrix` -> `14 passed`

### Planning

- Updated `spec/roadmap.md` so the next implementation candidate is academic reading-map V1, while event tree V1 moves into observation/tuning.

### Planning

- Added `spec/event-tree-literature-graph-design.md`:
  - separates event tree, academic literature graph, and cognition map;
  - defines text-first V1 shapes before any visual graph work;
  - lists existing data sources for media event structure and academic reading maps;
  - keeps V1 no-LLM, no new backend/API, and no graph library by default.
- Updated `spec/README.md` to link the new design note.
- Updated `spec/roadmap.md` so the next direction is design-first event tree / academic literature graph planning.

### Verification

- `git diff --check` -> exit 0
- `git status --short` -> only `spec/` documents changed after the narrative-convergence commit

### Committed

- Committed `4e25c38` (`feat(media): clarify narrative convergence signals`):
  - media narrative-convergence signals now render as compact evidence cards;
  - the panel uses neutral `相似说法` wording and keeps a boundary note that these are similarity signals, not truth or manipulation judgements;
  - no backend/API/LLM changes.

### Verification

- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- source-matrix` -> `12 passed`
- `cd frontend && npm run test:e2e` -> `22 passed`
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk LOW, 4 files, 2 symbols, 0 affected processes
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Added

- Clarified the Media tab narrative-convergence signals:
  - changed each topic-local signal into a compact evidence card with neutral `相似说法` labeling;
  - shows source count, article count, time span, source chips, and representative titles from existing payload fields;
  - keeps an explicit boundary note that convergence is a same-topic similarity signal, not a truth or manipulation judgement;
  - no backend/API/LLM changes.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/MediaPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- source-matrix` -> RED before implementation, missing `相似说法`
- `cd frontend && npm run test:e2e -- source-matrix` -> `12 passed`

### Added

- Added platform coverage status to the Sentiment tab:
  - shows attempted community platforms as compact chips: `有样本`, `暂不可用`, or `已尝试无样本`;
  - labels Hacker News as public API and Chinese OpenCLI platforms as requiring Chrome login state;
  - keeps community samples framed as sentiment signals, not facts, with no backend/API changes.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/SentimentPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- sentiment-panel` -> RED before implementation, missing `.sentiment-platform-coverage`
- `cd frontend && npm run test:e2e -- sentiment-panel` -> `2 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `20 passed`

### Added

- Documented the no-LLM local capability boundary:
  - added `spec/local-capability-boundary.md`;
  - linked it from `spec/README.md`;
  - added a compact local capability note to the LLM tab when no LLM analysis exists.
- Updated `spec/roadmap.md` so the next planned candidate is community readability / sentiment evidence cards.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/LlmPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- llm-panel` -> RED before implementation, missing `.local-capability-note`
- `cd frontend && npm run test:e2e -- llm-panel` -> `2 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `20 passed`

### Added

- Implemented academic priority-reading signals in the Academic tab:
  - added a compact `优先阅读信号` summary for high-citation, recent, sample-foundational, and low-information paper counts;
  - added neutral paper badges: `高引用`, `新近`, `样本内奠基`, `venue明确`, `低信息`;
  - kept the logic frontend-derived from existing OpenAlex payload fields, with no backend/API/LLM changes and no paper hiding or ranking claims.

### Verification

- `node .gitnexus/run.cjs impact -u "File:frontend/src/components/AcademicPanel.vue" -d upstream --include-tests` -> risk LOW, direct upstream `App.vue`
- `node .gitnexus/run.cjs impact -u "File:frontend/src/style.css" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run test:e2e -- academic-panel` -> `2 passed`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `18 passed`

### Planning

- Added `spec/academic-filtering-design.md`:
  - frames academic filtering as neutral priority-reading signals, not formal journal ranking;
  - uses existing OpenAlex fields (`venue`, `year`, `cited_by_count`, concepts, internal citations);
  - defines V1 labels: `高引用`, `新近`, `样本内奠基`, `venue明确`, `低信息`;
  - keeps V1 frontend-derived and avoids backend/API changes unless later reuse needs them.
- Updated `spec/roadmap.md` so academic filtering is the next planned implementation candidate.
- Linked the design from `spec/README.md`.

### Verification

- `git diff --check` -> exit 0
- `git status --short` -> only `spec/` documents changed before commit

### Added

- Enhanced the cognition-boundary queue cards in the intelligence desk:
  - each boundary seed now shows `推荐原因`, `挑战点`, and `下一步`;
  - the boundary card reuses existing seed/profile data and does not change backend APIs;
  - the boundary card now includes a visible `深入` action that reuses the existing seed analysis flow.

### Verification

- `node .gitnexus/run.cjs impact boundaryReason -d upstream --include-tests` -> risk LOW
- `node .gitnexus/run.cjs impact -u "Function:frontend/src/components/DiscoveryPanel.vue:boundaryQueue" -d upstream --include-tests` -> risk LOW
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- discovery-cognition` -> `4 passed`
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk MEDIUM, 2 files, 2 symbols, 1 expected boundary queue flow
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Planning

- Added `spec/roadmap.md` to record the next iteration direction:
  - near-term priority is cognition-boundary card enhancement in the intelligence desk;
  - #5 event tree / academic literature graph is now captured as design-first work;
  - #7 no-LLM local capability note is now captured as near-term documentation work;
  - sentence-level perspective remains deferred unless upgraded into fulltext reading assistance or anti-manipulation annotation.
- Linked `spec/roadmap.md` from `spec/README.md`.

### Frontend收口

- Committed `be5afaf` (`refactor(discovery): calm rest seed browsing`):
  - rest seeds are default-collapsed;
  - rest seeds exclude cognition-boundary queue items and already-known seeds;
  - social-feed style emoji clutter was removed;
  - e2e coverage now checks collapsed rest seeds and no duplicate boundary seeds.

### Verification

- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- discovery-cognition` -> `4 passed`
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk LOW, 2 files, 3 symbols, 0 affected processes
- `git status --short -- backend/.env backend/dossier.db` -> no output

### Added

- Reliability + discovery-layer round (human-approved "A" plan, Claude impl / GPT review):
  - **#9 academic LLM-synthesis timeout no longer strands the job.** `run_academic_analysis`
    wraps `synthesize_academic` in try/except: on timeout/failure the summary degrades to ""
    and the synthesize step reports `warning`, while `persist` still runs so fetched papers +
    citation graph are not lost. `run_academic_analysis_job` uses `mark_running_steps_done()`
    (not `mark_all_steps_done()`) so the `warning` is not masked as `done`. `fail_job` untouched
    (avoids its CRITICAL blast radius).
  - **#2/#3 discovery layer stops reading like a social feed.** Removed the `🔥 signal` heat
    badge from seeds (signal still drives ranking, just not shown). The cognition-boundary queue
    now has a one-click `我懂了` (marks `known`, reuses existing seed mark) that filters the item
    out of the queue — a visible closure — plus an auxiliary `存疑`. Removed the four-way
    classification buttons and the free-text "reason" editor from the seed stream (the friction
    the user flagged). Empty queue shows "今天都过了一遍 👍".
  - **#6 deep-analysis now includes cross-synthesis without double-running voices.** The
    cross-synthesis job gained a `refresh_voices: bool = True` flag. The standalone 三方对照 button
    keeps the full-refresh 6-step path (re-runs media/academic/sentiment then synthesizes). The
    LLM bundle calls it with `refresh_voices=false` — a lite 3-step path (gather/synthesize/persist)
    that reuses the just-persisted voices instead of re-running all three. `cross_synthesis_steps`,
    payload and args all split on the flag so the UI never shows 6 steps for a 3-step run. Missing
    voices still synthesize (handled by `gather_voices`).

### Two cross-synthesis semantics (by design)

- Standalone 「三方对照」button = full refresh (re-runs all three voices, then synthesizes).
- 「深度分析（LLM · 媒体+学界+民间+三方对照）」= reuses the voices just persisted by the bundle
  (`refresh_voices=false`), so nothing runs twice.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `164 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `14 passed` (run twice, stable)
- `git diff --check` -> exit 0
- `node .gitnexus/run.cjs impact run_cross_synthesis_job -d upstream` -> risk LOW
- `node .gitnexus/run.cjs impact run_academic_analysis -d upstream` -> risk LOW

## 2026-06-30

### Added

- Added a fulltext-assisted emotion-manipulation badge to the media article feed,
  rendered next to the substance-density badge (`6281282`):
  - `fulltext.extract_url_proxied` reuses the proven httpx + SOCKS5/trust_env path
    from `rss.py` to fetch HTML, then feeds `extract_from_html` — bypassing
    trafilatura's proxy-less downloader;
  - `enrich_topic_articles` concurrently fetches article bodies before each LLM
    batch (8s timeout, falls back to title+snippet on failure, never blocks);
  - the enrich LLM call emits two extra fields `emotion_score` / `emotion_note`
    in the same pass (zero extra calls);
  - pending re-enrichment includes `emotion_score < 0` only when fulltext is on,
    so disabling fulltext does not re-run the LLM for un-scorable emotion;
  - frontend shows `情绪 N` only when `emotion_score >= 0` (red=high manipulation).
- Config `FULLTEXT_FETCH_TIMEOUT=8`, `ENRICH_FETCH_FULLTEXT=1` (off → title+snippet only).

### Fixed

- Forced `emotion_score=-1` at the code level when no fulltext was fetched,
  ignoring whatever the LLM returns (`803b7d1`). Real-data validation showed the
  LLM ignores the prompt's "return -1 without body" instruction and scores
  emotion from title+snippet alone — a pseudo-judgement leak. The red line is now
  enforced in code, not by trusting the prompt. `substance_score` is left
  unchanged (title/snippet conservative estimate is acceptable; evidence bar differs).

### Reason

Emotion manipulation is a whole-article rhetorical pattern, so it must be judged
from body text, not the opening hook in a snippet. Fulltext is an *assist*, not a
dependency: when extraction fails, substance scoring continues and the emotion
badge simply does not show — never a fabricated judgement.

### Known limitation

- The emotion badge (and any fulltext-dependent feature) is only effective for
  sources whose body can be extracted (direct links / native RSS). The primary
  source — Google News RSS — yields `news.google.com/rss/articles/CBMi...` redirect
  URLs that trafilatura cannot extract, so those articles keep `emotion_score=-1`
  and show no badge. Resolving Google News redirect/encoded URLs is intentionally
  out of scope this round (redirect-following and `CBMi` base64 decoding are both
  fragile, and the resolved target may still block scraping). Fulltext-class
  features need a direct-link / better source to be broadly useful.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `162 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `14 passed`
- `git diff --check` -> exit 0
- `git check-ignore backend/.env backend/dossier.db` -> both ignored
- `node .gitnexus/run.cjs impact enrich_topic_articles -d upstream` -> risk LOW
- Real-data run (topic 1, enrich_limit=10): `fulltext_hits=0` (confirms the Google
  News limitation); 4 pseudo emotion scores leaked pre-hotfix were reset to -1 in
  the live DB with human approval (dry-run → UPDATE → recount 0).

## 2026-06-29

### Added

- Moved cognition marking from the media article feed to today's intelligence desk:
  - added a local cognition profile initialized from the user's 10 boundary-test answers;
  - added seed-level cognition marks with stable `target_key` URLs and optional notes;
  - added a small cognition-boundary queue in `DiscoveryPanel`;
  - removed article-level cognition sorting from the original article feed while keeping substance-score visibility;
  - allowed `PUT` in local CORS so browser saves can pass preflight.

### Reason

The cognition labels are useful for new frontier items, not for forcing the user to classify 100+ raw reports. V1 now collects low-friction judgement data from a small queue before any larger cognition map exists.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_cognition_marks.py -q` -> `5 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `153 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `14 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk medium, affected processes 3

### Added

- Implemented the readable-cognition roadmap in five small commits:
  - surfaced article substance-score coverage in the media feed;
  - rendered community sentiment as compact readable sample cards;
  - added on-demand article perspective for summary/fulltext sentence inspection;
  - added topic-local narrative convergence signals;
  - added one-click cognition marks and a lightweight cognition accumulation panel.

### Reason

Prioritize reading experience before larger cognition-map work: make substance, signals, and personal judgement markers visible without making LLM or heavy infrastructure part of the core path.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest tests/test_cognition_marks.py -q` -> `2 passed, 3 warnings`
- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `150 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e -- tests/e2e/source-matrix.spec.ts -g "groups original articles"` -> `2 passed`
- `cd frontend && npm run test:e2e` -> `10 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk medium, affected processes 5

### Added

- Created the spec harness:
  - `spec/README.md`
  - `spec/project.md`
  - `spec/development.md`
  - `spec/acceptance.md`
- Extended `AGENTS.md` with project map, one-sentence goal, project structure, non-negotiable constraints, verification commands, and spec links.
- Added this changelog and linked it from `AGENTS.md` and `spec/README.md`.

### Reason

Give future agents a stable project map and reproducible acceptance standard before they edit code or claim work is complete.

### Verification

- `cd backend && ..\venv\Scripts\python.exe -m pytest -q` -> `140 passed, 3 warnings`
- `cd frontend && npm run build` -> build passed
- `cd frontend && npm run test:e2e` -> `8 passed`
- `git diff --check` -> exit 0
- `git status --short -- backend/.env backend/dossier.db` -> no output
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`
- `node .gitnexus/run.cjs detect-changes --scope all` -> risk low, affected processes 0
