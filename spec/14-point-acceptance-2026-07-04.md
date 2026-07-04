# 14-Point Acceptance Matrix - 2026-07-04

This matrix is the current acceptance ledger for the **14 点反馈验收修复 Sprint**.

It does not declare the sprint complete. It records the strongest evidence currently available and names the remaining decision or verification needed before a final commit or completion claim.

For the remaining human/Claude choices and Codex read-only source/academic evidence audit, see `spec/14-point-remaining-decisions-2026-07-04.md`.

Allowed final statuses from the sprint plan:

- `Done`
- `V1 Done with known limitation`
- `Blocked by external account/API`

Temporary working statuses used in this matrix:

- `Pending human decision`
- `Pending Claude review`
- `Pending Claude implementation/review`

## Current Gate Evidence

Fresh targeted checks after the P0/P1 follow-up:

- Fresh stage-5 full gate refresh:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings in 13.40s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 396ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `76 passed (2.3m)`.
  - `git diff --check` -> exit 0, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `8731f0e`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; still explained as the broad cumulative 14-point repair integration tree.
- Fresh full gate rerun after the Codex-owned frontend retest:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings in 22.21s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 499ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `76 passed (2.3m)`.
  - `git diff --check` -> exit 0, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; still explained as the broad cumulative 14-point repair integration tree.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `31 passed` in 49.8s on the latest Codex-owned frontend retest. This covers project CRUD, contextual drilldown, stale refresh context, media stance trend, event network, selected-node inline detail, LLM-refresh reuse, sentiment timeline, OpenCLI diagnostics UI, and cognition cards.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `25 passed` in 49.2s on the latest Codex-owned high-risk frontend retest. This rechecks parent-context drilldown, selected-event drilldown, stale refresh context, media stance trend and small-sample downgrade, event network semantics, selected-node inline detail, LLM-refresh reuse, sentiment timeline/OpenCLI diagnostics, and cognition cards.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `25 passed` in 49.3s after the latest bridge-plan review. This rechecks the Codex-owned high-risk frontend paths: parent-context drilldown, selected-event drilldown, stale refresh context, media stance trend and small-sample downgrade, event network semantics, selected-node inline detail, LLM-refresh reuse, sentiment timeline/OpenCLI diagnostics, and cognition cards.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `26 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "keeps existing LLM analysis"` -> `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `11 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts -g "selected event detail"` -> red first, then `1 passed` after adding event-detail drilldown.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts` -> `13 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "summarizes source coverage"` -> red first, then `1 passed` after adding the source manager status summary.
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `4 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "explains stale"` -> red first, then `1 passed` after adding the stale latest-report warning.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "refreshes stale"` -> red first, then `1 passed` after making the stale refresh use the current topic context.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "summarizes media stance"` -> red first, then `1 passed` after adding stance share-change evidence such as `占比 0% → 56%`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "degrades media stance"` -> red first, then `1 passed` after adding the small-sample downgrade.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `14 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts -g "sentiment change timeline"` -> red first, then `1 passed` after adding the `小样本线索` marker.
- `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts` -> `3 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts sentiment-panel.spec.ts` -> `17 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts source-registry.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `35 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop academic-panel.spec.ts` -> `2 passed`.
- `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_academic_layer.py -q` -> `12 passed, 3 warnings`.
- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings`.
- `cd frontend; npm run test:e2e -- --workers=1` -> `76 passed`.
- `cd frontend; npm run build` -> passed.
- `git diff --check` -> exit 0, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db` -> no output.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; still explained as the broad cumulative 14-point repair integration tree, not a narrow single-feature diff.

Earlier full-gate baseline recorded before the latest P0/P1 follow-up:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `198 passed, 3 warnings`.
- `cd frontend; npm run build` -> passed.
- `cd frontend; npm run test:e2e -- --workers=1` -> `62 passed`.
- `git diff --check` -> exit 0, LF/CRLF warnings only.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, explained as broad cumulative 14-point repair scope.

Before a final claim, rerun the full gate from `spec/acceptance.md`; the earlier full-gate numbers are context, not final proof.

## Matrix

| # | User feedback | Current status | Evidence | Remaining action |
|---|---|---|---|---|
| 1 | Project/topic management needs real CRUD. | `Done`. | `frontend/tests/e2e/project-management.spec.ts`; `backend/tests/test_project_topic_management.py`; targeted desktop run includes project management; fresh full gate evidence is recorded above. | No item-specific work remains; include in final human review before any commit. |
| 2 | Deep-dive chips must preserve parent context; latest dates/freshness must not silently go stale. | Split status: context drilldown is `Done`; stale-state explanation/manual fallback is `Done`; backend auto-refresh is `Pending human decision`. | `frontend/tests/e2e/contextual-drilldown.spec.ts`; event-detail drilldown now appears inside selected event detail and still searches `俄乌战争 前线态势`; `frontend/tests/e2e/source-matrix.spec.ts` covers stale latest-report dates as last collected time, and verifies the refresh fallback uses the current topic context instead of a residual search-box query; Claude freshness diagnosis in `.agent-bridge/TO_CODEX.md`: old topics were not re-collected, while newer topics have July data. | Human must choose freshness option A/B/C before backend scheduling. Recommended C: backend-running auto refresh for news/frontier plus visible stale state and manual fallback. |
| 3 | Need broader, higher-quality news/source coverage and local pre-analysis. | `V1 Done with known limitation`, pending Claude review. | `backend/config/feeds.json`; `backend/app/services/source_registry.py`; `backend/app/services/evidence_package.py`; `backend/tests/test_source_registry.py`; `frontend/tests/e2e/source-registry.spec.ts`; source manager now summarizes total/enabled/failed sources, latest successful fetch, and failed-source reasons; deep-analysis evidence package tests. | Claude to confirm source registry quality/freshness status and whether more source families are needed before final claim. Full crawler and same-event G20 coverage remain out of V1. |
| 4 | Refreshing one panel after LLM deep analysis should not force rerunning or losing LLM analysis. | `Done`. | `frontend/tests/e2e/cross-synthesis-reuse.spec.ts`; `frontend/tests/e2e/job-topic-race.spec.ts`; new `frontend/tests/e2e/source-matrix.spec.ts` test `keeps existing LLM analysis visible when refreshing only the academic layer`; `backend/tests/test_cross_synthesis.py`; fresh full gate evidence is recorded above. | No material-input invalidation hash yet; that is a future improvement, not the core bug. |
| 5 | Community/OpenCLI fails on Windows despite Chrome login. | `Done` for WinError runner and diagnostics; platform login/session failures remain `Blocked by external account/API`. | `backend/app/collectors/reddit_sentiment.py`; `backend/tests/test_reddit_sentiment_collector.py`; `backend/app/services/opencli_diagnostics.py`; `backend/tests/test_opencli_diagnostics.py`; `frontend/tests/e2e/sentiment-panel.spec.ts`; Claude reviewed `_opencli_args` / `_run_opencli` as acceptable; fresh full gate evidence is recorded above. | Platform login/session failures still need user environment or platform-specific diagnostics. |
| 6 | Attitude/public-opinion over time is not usable. | `V1 Done with known limitation`. | Media trend evidence in `frontend/src/components/MediaPanel.vue` now shows count deltas, share deltas such as `占比 0% → 56%`, turning periods, sources, and representative reports; small media samples downgrade to distribution-only; sentiment sample timeline in `frontend/src/components/SentimentPanel.vue` shows platform, time, representative posts, confidence, and `小样本线索` for tiny buckets; `frontend/tests/e2e/source-matrix.spec.ts`; `frontend/tests/e2e/sentiment-panel.spec.ts`; `backend/tests/test_sentiment_layer.py`. | Claude review for pseudo-trend risk. Keep wording as sample/platform signals, not public-opinion truth. |
| 7 | Event structure tree should be developmental network/tree. | `V1 Done with known limitation`. | `frontend/src/components/MediaPanel.vue`; `frontend/tests/e2e/source-matrix.spec.ts` event network tests. | Human/Claude review whether local evidence network is enough for V1. Causal/historical chains are intentionally not claimed. |
| 8 | Event structure tree and event-development flow may be merged. | `V1 Done with known limitation`. | Media UI now centers on `事件发展网络`; source-matrix and timeline details share the same evidence surface; `frontend/tests/e2e/source-matrix.spec.ts`. | Further information architecture refinement can follow after final 14-point gate; avoid starting a new graph-workbench feature in this sprint. |
| 9 | Selected Node should appear under clicked event, not bottom. | `Done`. | `frontend/tests/e2e/source-matrix.spec.ts` `shows selected event detail inline below the clicked timeline node`; `frontend/tests/e2e/contextual-drilldown.spec.ts` `shows contextual drilldown inside the selected event detail`; no bottom `.feed-pane > .event-detail`; inline country comparison action visible; fresh full gate evidence is recorded above. | G20/same-event coverage remains limited by source evidence and is tracked under #3. |
| 10 | Academic view needs DOI/authors/journal/source hygiene and academic-review discipline. | `Pending Claude implementation/review`. Metadata, review prompt, and frontend citation display are V1, but the academic collector is still OpenAlex-only. | `backend/app/pipeline/academic.py` calls `openalex.search_works`; `backend/app/collectors/openalex.py`; `backend/tests/test_academic_layer.py` (`12 passed`); `frontend/tests/e2e/academic-panel.spec.ts` (`2 passed`) verifies authors, year, venue, DOI/OpenAlex links, priority-reading signals, and readable literature network. | Claude must either add a second academic source path such as Crossref/Semantic Scholar/arXiv to the academic layer, or ask the human to accept OpenAlex-only as a known limitation. Formal journal ranking remains deferred. |
| 11 | Citation graph is unreadable; prefer readable tree/network. | `V1 Done with known limitation`, but dependent on #10 source review. | `frontend/tests/e2e/academic-panel.spec.ts` (`2 passed`); `backend/tests/test_academic_layer.py` (`12 passed`); readable literature network in `AcademicPanel.vue` shows nodes and explicit `引用` edges instead of the old unreadable citation-chip graph. | UI readability V1 exists, but the graph is built from OpenAlex sample-internal references. Claude review needed before final status. |
| 12 | Cognition expansion cards need summary, motivation, report link, and deeper path. | `V1 Done with known limitation`. | `frontend/tests/e2e/discovery-cognition.spec.ts`; `frontend/src/components/DiscoveryPanel.vue`; discovery archive/timeline tests; fresh full gate evidence is recorded above. | Long-term profile calibration remains future work. |
| 13 | Bilibili video/newsletter/Google Alerts information collection method should inform the source pipeline. | `V1 Done with known limitation`, pending Claude review. | `spec/2026-07-03-frontend-feedback.md`; `backend/config/feeds.json`; source registry/import tests. | Newsletter/RSS leads are represented in source registry/import. Bilibili video remains a documented lead, not full transcript review; Filo Mail and Google Alerts are not integrated workflows. Claude should confirm whether this is enough for V1. |
| 14 | Write the conversation into the workspace. | `Done`. | `spec/2026-07-03-frontend-feedback.md`; `spec/current-state.md`; this matrix; audit docs under `spec/`. | Keep UTF-8 files; ignore terminal mojibake from PowerShell display. |

## Remaining Sprint Blockers

1. Freshness/automatic update needs a human decision before backend scheduling or UI stale-state work:
   - A. stale warning + one-click refresh;
   - B. backend-running auto refresh for news/frontier;
   - C. both, recommended.
2. Claude should review or implement current source/academic claims before any final status:
   - news source quality and source status explanation;
   - OpenAlex-only academic layer versus the user's request for broader academic sources;
   - readable literature network and academic review hygiene.
3. Final acceptance must rerun the full gate:
   - backend full pytest;
   - frontend build;
   - frontend full e2e;
   - `git diff --check`;
   - GitNexus `detect-changes`;
   - secret/database status checks.

## Final Status Projection

This projection names what can be closed after explicit decisions. It is not a completion claim.

| Item | Current finalizable status | What prevents final closure |
|---|---|---|
| #1 | `Done` | Nothing item-specific. |
| #2 | `Done` for parent-context drilldown and stale/manual fallback; auto-refresh remains undecided. | Human must choose A/B/C; B/C requires Claude backend work. |
| #3 | `V1 Done with known limitation` if accepted. | Claude/human must accept V1 source scope or request more source families. |
| #4 | `Done` | Nothing item-specific. |
| #5 | `Done` for Windows runner/diagnostics; external platform login/API may be `Blocked by external account/API`. | Real platform login/API failures remain environment-dependent. |
| #6 | `V1 Done with known limitation` if accepted. | Claude semantic review for pseudo-trend risk. |
| #7/#8 | `V1 Done with known limitation` if accepted. | Claude/human acceptance that this is a local evidence network, not a causal graph. |
| #9 | `Done` | Nothing item-specific. |
| #10 | Not final-green as `Done` while OpenAlex-only. | Claude implements a second academic source, or human accepts OpenAlex-only V1 limitation. |
| #11 | `V1 Done with known limitation`, tied to #10. | Source hygiene follows #10. |
| #12 | `V1 Done with known limitation` | Nothing item-specific for this sprint. |
| #13 | `V1 Done with known limitation` if accepted. | Claude/human must accept docs/import V1 or request ingestion entry implementation. |
| #14 | `Done` | Nothing item-specific. |

## Completion Audit - Still Open

Fresh verification proves the current integration tree is test-green, but it does not prove the whole sprint is complete. The remaining open items are product-scope decisions, not missing frontend regression evidence.

| Item | Current proof | What is still missing | Unblocker |
|---|---|---|---|
| #2 backend freshness automation | Frontend stale explanation and manual refresh are covered; Claude diagnosed old topics were not re-collected. | Human must choose whether backend-running auto refresh is in this sprint, and if so whether option A, B, or C is approved. | Human decision, then Claude backend implementation if B/C. |
| #3 news/source quality | Source registry, source manager status, failure reasons, and evidence package tests exist. | Claude must confirm V1 source-quality scope or implement more source families. Same-event G20/full crawler remains outside current proof. | Claude review/implementation. |
| #6 media/community trend semantics | Frontend trend and sentiment timeline e2e pass, with share changes, small-sample downgrade, and tiny-bucket markers. Codex semantic scan found the UI explicitly says `报道样本`, `不代表民间舆论`, `当前样本只能显示立场分布`, `样本趋势，非事实时间线`, and `小样本线索`; tests assert the key boundaries. | Claude still needs to independently review whether wording/data semantics avoid pseudo-trend or overclaiming. | Claude semantic review. |
| #7/#8 event network semantics | Event network and selected-node e2e pass; Codex semantic scan found no unqualified causal wording in the event-network UI. The visible boundary says `本地证据边，不显示 LLM 因果假设`, and tests assert it. | Claude/human still need to accept local evidence network as V1 rather than a true causal historical graph. | Claude/human review. |
| #10 academic source breadth | Metadata, prompt discipline, DOI/OpenAlex links, and academic UI tests pass. | Academic collector is still OpenAlex-only. The user explicitly questioned whether one source is too thin. | Claude adds Crossref/Semantic Scholar/arXiv path, or human accepts OpenAlex-only V1 limitation. |
| #11 literature network source hygiene | UI readable literature network passes e2e. | Network is built from OpenAlex sample-internal references, so final semantics depend on #10. | Claude review after #10 decision. |
| #13 source-ingestion lead | Newsletter/RSS and Google Alerts source import have tests; Bilibili video is documented as a lead. | Claude must decide whether this is enough for V1 or whether a clearer video/web/newsletter ingestion entry is required this sprint. | Claude review/implementation. |

## Completion Rule

Do not mark the sprint complete from this matrix alone.

This matrix is a checkpoint. It becomes final evidence only after the remaining decisions/reviews are resolved and the full gate is freshly rerun.
