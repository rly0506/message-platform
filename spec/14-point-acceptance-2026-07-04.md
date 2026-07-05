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

Fresh residual-delta gate on 2026-07-05 after Stage 0B source, media-trend, OpenCLI diagnostics, and status-doc updates:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `223 passed, 5 warnings in 31.06s`.
- `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 410ms).
- `cd frontend; npm run test:e2e -- --workers=1` -> `90 passed (2.6m)`.
- `git diff --check` -> pass, existing LF/CRLF warnings only.
- `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> no output.
- `git check-ignore -v backend/.env backend/dossier.db .agent-bridge .agents` -> all four paths are ignored by `.gitignore`.
- `node .gitnexus/run.cjs status` -> index up-to-date at current commit `e6e277f`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `low`, `18 files`, `40 symbols`, `0` affected processes.

Historical targeted checks after the P0/P1 follow-up:

- Fresh Codex final gate on 2026-07-05 after Claude final review and status-doc updates:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 31.31s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 565ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `88 passed (2.5m)`.
  - `git diff --check` -> pass, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge/database file was staged/tracked.
  - `node .gitnexus/run.cjs analyze` -> repository indexed successfully at current commit `0a9a97b`; FTS unavailable warning only.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `0a9a97b`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `low`, `19 files`, `41 symbols`, `0` affected processes. The earlier broad `critical` warning applied to the full integration tree before commit1 separated the backend/source/academic changes; the remaining commit2 frontend/spec surface is low risk.
- Fresh Codex full pre-final gate on 2026-07-05:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 24.34s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 451ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `88 passed (2.6m)`.
  - `git diff --check` -> pass, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge/database file was staged/tracked.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `5ed0022`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `27 files`, `101 symbols`, `54` affected processes. This is expected for the broad integration tree because central DB/source-registry symbols (`SourceRegistry`, `Paper`, `_migrate`, `_seed_source_registry`) affect many job flows. It is not a new narrow frontend failure, but it still requires Claude/human review before commit.
  - This is a pre-final gate, not a sprint completion claim: #3 source-expansion V1 acceptance, Claude #10/#11 review, #13 source-ingestion acceptance, and human final review still remain.
- Fresh Codex source-registry classified metadata persistence:
  - GitNexus impact `SourceRegistry` / `File:backend/app/db.py` -> risk `CRITICAL` because the central DB model is imported broadly; change is additive fields plus lightweight migration.
  - GitNexus impact `source_payload` -> risk `LOW`.
  - GitNexus impact `File:backend/app/services/source_registry.py` -> risk `LOW`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py::test_sources_api_preserves_classified_coverage_metadata -q` -> red first for missing `coverage`, then `1 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py -q` -> `10 passed, 5 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_api_helpers.py tests/test_topic_ops.py tests/test_deep_analysis.py -q` -> `26 passed, 5 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `209 passed, 5 warnings in 41.60s`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `7 passed`.
  - `cd frontend; npm run build` -> passed.
  - `git diff --check -- backend/app/db.py backend/app/services/source_registry.py backend/tests/test_source_registry.py frontend/src/App.vue frontend/src/types/dossier.ts frontend/src/style.css frontend/tests/e2e/source-registry.spec.ts` -> pass, existing LF/CRLF warnings only.
  - This makes `coverage/access/last_tested/coverage_reason/state_media` persist through the DB and API to the UI. At this stage it did not add the actual classified mainstream source batch; the later #3 source-expansion evidence below supersedes that limitation.
- Fresh Codex #3 disabled/limited registry collection boundary:
  - GitNexus impact `collect_topic` -> risk `LOW`.
  - GitNexus impact `File:backend/app/topic_ops.py` -> risk `LOW`.
  - GitNexus impact `File:backend/app/feed_registry.py` -> risk `LOW`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py::test_collect_topic_does_not_fallback_to_curated_feeds_when_registry_sources_are_disabled -q` -> red first because collection fell back to all 17 curated feeds, then `1 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py -q` -> `11 passed, 5 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_topic_ops.py tests/test_api_helpers.py -q` -> `13 passed, 4 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `210 passed, 5 warnings in 18.98s`.
  - Behavior change: curated `feeds.json` fallback is now only a bootstrap path when the registry is empty; once registry rows exist, disabled/limited sources remain visible but are not silently collected.
  - This supports #3's visible-but-not-collected rule. At this stage it did not add the actual classified mainstream source batch; the later #3 source-expansion evidence below supersedes that limitation.
- Fresh Codex #3 current-tree source expansion evidence on 2026-07-05:
  - `backend/config/feeds.json` now contains `25` curated feeds.
  - `8` feeds are explicitly classified as `coverage=fresh_rss` and `access=public`: UN News, NPR World, The Conversation, CNBC World, The White House, Federal Reserve, European Central Bank, and WTO News.
  - `5` feeds are `tier=official`: UN News, The White House, Federal Reserve, European Central Bank, and WTO News.
  - The White House carries `state_media=true` through curated-feed seeding via the backend boolean parser, so it is an official narrative sample rather than a neutral authority source.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `5ed0022`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/feed_registry.py" --direction upstream --include-tests` -> risk `LOW`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py -q` -> `11 passed, 5 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_topic_ops.py tests/test_api_helpers.py -q` -> `13 passed, 4 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 36.44s`.
  - This proves the first classified fresh-source batch is present in the current tree. It does not prove full WSJ/AFP/Xinhua/paywalled-wire coverage, multilingual coverage, a full crawler, or same-event G20 coverage.
- Fresh Codex academic multi-source provenance display:
  - GitNexus impact `File:frontend/src/components/AcademicPanel.vue` -> risk `LOW`.
  - GitNexus impact `File:frontend/src/types/dossier.ts` -> risk `MEDIUM`, direct import dependents only; new fields are optional and backwards-compatible.
  - GitNexus impact `File:frontend/tests/e2e/academic-panel.spec.ts` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop academic-panel.spec.ts -g "source provenance"` -> red first for fixed `当前学界样本：OpenAlex`, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop academic-panel.spec.ts` -> `3 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts academic-panel.spec.ts` -> `10 passed`.
  - `cd frontend; npm run build` -> passed.
  - `git diff --check -- frontend/src/components/AcademicPanel.vue frontend/src/types/dossier.ts frontend/tests/e2e/academic-panel.spec.ts` -> pass, existing LF/CRLF warnings only.
  - This prepares the UI for Claude's #10 second academic source payload (`sources/source_count/source_links`) but does not implement Crossref/OpenAlex merge in the backend.
- Fresh Codex #10 Crossref academic collector and merge hardening:
  - GitNexus impact `crossref_work_url` -> risk `LOW`, direct caller `normalize_work`, indirect caller `search_works`.
  - GitNexus impact `File:backend/app/collectors/crossref.py` -> risk `LOW`.
  - GitNexus impact `search_works` was ambiguous across OpenAlex/Crossref, but both candidates reported max risk `LOW`.
  - GitNexus impact `synthesize_academic_consensus` -> risk `LOW`, affected process `run_academic_analysis`.
  - GitNexus impact `File:backend/app/pipeline/academic.py` -> risk `LOW`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_crossref_collector.py -q` -> red first for unencoded DOI path and placeholder Crossref User-Agent email, then `4 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_academic_layer.py::test_run_academic_analysis_keeps_openalex_when_crossref_fails -q` -> `1 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_academic_layer.py::test_synthesize_academic_consensus_describes_multi_source_sample -q` -> red first because the prompt still called the sample `OpenAlex 学术论文样本` / `OpenAlex top-N`, then `1 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_academic_layer.py::test_run_academic_analysis_uses_crossref_when_openalex_has_no_results -q` -> red first because `sort_strategy` still described OpenAlex-only relevance, then `1 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_crossref_collector.py tests/test_openalex_collector.py -q` -> `8 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_academic_layer.py -q` -> `16 passed, 5 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 29.11s`.
  - Behavior now verified: Crossref can supply papers when OpenAlex has no results; OpenAlex + Crossref records merge by DOI and preserve `sources/source_count/source_links`; Crossref failures fail soft and leave OpenAlex-only results intact; Crossref work links encode DOI path slashes; academic summary prompts and `sort_strategy` now describe the sample as OpenAlex + Crossref instead of OpenAlex-only.
  - This closes the OpenAlex-only backend limitation for #10 at V1 source breadth level. Claude accepted the academic-source and citation-discipline review on 2026-07-05; the final sprint gate still remains before any final completion claim.
- Fresh Codex source-manager classified coverage display:
  - GitNexus impact `File:frontend/src/App.vue` -> risk `LOW`.
  - GitNexus impact `File:frontend/src/types/dossier.ts` -> risk `MEDIUM`, direct import dependents only; new fields are optional and backwards-compatible.
  - GitNexus impact `File:frontend/tests/e2e/source-registry.spec.ts` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "classified source coverage"` -> red first for missing `摘要源`, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `7 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts --workers=1` -> `15 passed`.
  - `cd frontend; npm run build` -> passed.
  - `git diff --check -- frontend/src/App.vue frontend/src/types/dossier.ts frontend/src/style.css frontend/tests/e2e/source-registry.spec.ts` -> pass, existing LF/CRLF warnings only.
  - This prepared the UI for Claude's #3 classified source payload (`coverage/access/last_tested/coverage_reason/state_media`); the backend fresh-source batch is now recorded in the 2026-07-05 #3 source-expansion evidence above.
- Fresh backend/GitNexus baseline after the latest coordination updates:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings in 52.41s`.
  - `node .gitnexus/run.cjs analyze` -> repository indexed successfully at current commit `5ed0022`; FTS unavailable warning only.
  - `node .gitnexus/run.cjs status` -> up-to-date at current commit `5ed0022`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `low`, `13 files`, `13 symbols`, `0` affected processes.
- Latest Claude review update from `.agent-bridge/TO_CODEX.md`:
  - #2 auto-refresh/freshness is `ready for human final review = YES`.
  - #6/#7/#8/#11/#12 semantic review is PASS; Claude independently checked the frontend wording and found no pseudo-causal or authority-ranking red-line violation.
  - Human direction for #10 is multi-source academic coverage; OpenAlex-only is not accepted as the final sprint answer.
  - Claude has landed the first #3 classified fresh-source batch in the working tree and is now needed for source-scope review/acceptance rather than from-scratch implementation.
- Fresh Codex-owned frontend retest after the latest `TO_CODEX.md` check:
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `27 passed (50.8s)`.
  - This rechecks parent-context drilldown, selected-event fallback drilldown, stale refresh context, auto-refresh status/run UI, media stance trend, small-sample downgrade, event network semantics, selected-node inline detail, LLM-refresh reuse, sentiment timeline/OpenCLI diagnostics, and cognition cards.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 428ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `84 passed (2.5m)`.
  - This is fresh frontend evidence only; it does not close #3 source-scope acceptance, #10 academic second-source review, or Claude semantic/source review.
- Fresh full gate after auto-refresh frontend wiring and GitNexus reindex:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings in 39.31s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 460ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
  - `git diff --check` -> pass, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
  - `node .gitnexus/run.cjs analyze` -> repository indexed successfully; FTS extension unavailable warning only.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `d028496`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `medium`, `16 files`, `45 symbols`, `1` affected execution flow (`RunCrossSynthesis -> FetchCrossSynthesis`), explained as expected broad integration-tree drift plus new auto-refresh/API/frontend status surface.
- Fresh Codex review of the backend auto-refresh implementation now present in the working tree:
  - GitNexus impact `File:backend/app/services/auto_refresh.py` -> target not indexed yet, risk `UNKNOWN`.
  - GitNexus impact `File:backend/app/api.py` -> risk `LOW`, impactedCount `0`.
  - GitNexus impact `File:backend/app/config.py` -> risk `LOW`, impactedCount `0`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_auto_refresh.py -q` -> `8 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_api_helpers.py tests/test_discovery.py tests/test_source_registry.py -q` -> `56 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings`.
  - `git diff --check -- backend/app/config.py backend/app/api.py backend/app/services/auto_refresh.py backend/tests/test_auto_refresh.py` -> pass, existing LF/CRLF warning only.
  - Codex review notes sent to `.agent-bridge/TO_CLAUDE.md` found two status-semantics risks; Claude later fixed both: single-topic failures now surface through `news_errors`, and synchronous `refresh_once()` returns after `running=False`.
- Fresh Codex frontend auto-refresh status wiring:
  - GitNexus impact `File:frontend/src/App.vue` -> risk `LOW`.
  - GitNexus impact `File:frontend/src/api/dossierApi.ts` -> risk `MEDIUM`, direct import dependents only.
  - GitNexus impact `File:frontend/src/types/dossier.ts` -> risk `MEDIUM`, direct import dependents only.
  - GitNexus impact `File:frontend/tests/e2e/source-matrix.spec.ts` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "auto-refresh status"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `15 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `26 passed`.
  - `cd frontend; npm run build` -> passed.
  - `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
  - `git diff --check -- frontend/src/App.vue frontend/src/api/dossierApi.ts frontend/src/types/dossier.ts frontend/src/style.css frontend/tests/e2e/source-matrix.spec.ts` -> pass, existing LF/CRLF warnings only.
- Fresh Codex event-detail drilldown fallback:
  - GitNexus impact `File:frontend/src/components/MediaPanel.vue` -> risk `LOW`, direct upstream `App.vue`.
  - GitNexus impact `File:frontend/src/composables/useJobRunner.ts` -> risk `LOW`, direct upstream `App.vue`.
  - GitNexus impact `File:frontend/tests/e2e/contextual-drilldown.spec.ts` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts -g "event-title drilldown"` -> red first for missing `围绕此事件`, then green after adding the inline fallback.
  - Same test also caught the original naked-search risk: the fallback must search `俄乌战争 前线态势更新`, not `前线态势更新`.
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts` -> `3 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "selected event detail|event structure tree|local evidence edges"` -> `3 passed` after rerunning serially; an earlier parallel run failed from dev-server port refusal, not an assertion.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `15 passed`.
  - `cd frontend; npm run build` -> passed.
- Fresh Codex sentiment timeline evidence label:
  - GitNexus impact `File:frontend/src/components/SentimentPanel.vue` -> risk `LOW`, direct upstream `App.vue`.
  - GitNexus impact `File:frontend/tests/e2e/sentiment-panel.spec.ts` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts -g "sentiment change timeline"` -> red first for missing `代表样本`, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts` -> `3 passed`.
  - `cd frontend; npm run build` -> passed.
- Fresh Codex cognition-card importance wording:
  - GitNexus impact `File:frontend/src/components/DiscoveryPanel.vue` -> risk `LOW`, direct upstream `App.vue`.
  - GitNexus impact `File:frontend/tests/e2e/discovery-cognition.spec.ts` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop discovery-cognition.spec.ts -g "seed summary"` -> red first for missing `为什么现在重要`, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop discovery-cognition.spec.ts` -> `6 passed`.
  - `cd frontend; npm run build` -> passed.
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
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "source-ingestion path"` -> red first, then `1 passed` after adding the visible RSS/newsletter/Google Alerts plus B站/video lead guide.
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "coverage mix"` -> red first, then `1 passed` after adding source type and quality-tier coverage mix.
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `6 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "explains stale"` -> red first, then `1 passed` after adding the stale latest-report warning.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "refreshes stale"` -> red first, then `1 passed` after making the stale refresh use the current topic context.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "summarizes media stance"` -> red first, then `1 passed` after adding stance share-change evidence such as `占比 0% → 56%`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "degrades media stance"` -> red first, then `1 passed` after adding the small-sample downgrade.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `14 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts -g "sentiment change timeline"` -> red first, then `1 passed` after adding the `小样本线索` marker.
- `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts` -> `3 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts sentiment-panel.spec.ts` -> `17 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts source-registry.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `35 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop academic-panel.spec.ts -g "priority-reading"` -> red first, then `1 passed` after adding the visible OpenAlex sample scope, academic citation requirements, and sample-internal citation network boundary.
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

Latest status overrides before reading the row-level table:

- #2 is no longer waiting for Claude backend confirmation. Claude has replied `ready for human final review = YES`; it now waits for human final review and the final sprint gate.
- #6/#7/#8/#11/#12 are no longer waiting for Claude semantic review. Claude review is PASS, with V1 limitation wording preserved.
- #3/#10/#11/#13 had Claude final-review acceptance in `.agent-bridge/TO_CODEX.md` on 2026-07-05, but the human later chose to keep optimizing where gaps remain. Treat the branch as a staged audited baseline, not as final closure. #3/#11/#13 remain `V1 Done with known limitation`; #10 remains `Done` for V1 academic source breadth. The final sprint gate still must be rerun before any completion claim.

| # | User feedback | Current status | Evidence | Remaining action |
|---|---|---|---|---|
| 1 | Project/topic management needs real CRUD. | `Done`. | `frontend/tests/e2e/project-management.spec.ts`; `backend/tests/test_project_topic_management.py`; targeted desktop run includes project management; fresh full gate evidence is recorded above. | No item-specific work remains; include in final human review before any commit. |
| 2 | Deep-dive chips must preserve parent context; latest dates/freshness must not silently go stale. | `Done` for context drilldown, stale-state explanation/manual fallback, backend-running auto-refresh implementation, and frontend auto-refresh status UI/e2e; waits only for human final review. | `frontend/tests/e2e/contextual-drilldown.spec.ts`; event-detail drilldown now appears inside selected event detail and still searches `俄乌战争 前线态势`; when no backend subtopic suggestions exist, the inline event-detail fallback shows `围绕此事件` and searches `俄乌战争 前线态势更新` instead of a naked event phrase; `frontend/tests/e2e/source-matrix.spec.ts` covers stale latest-report dates as last collected time, verifies the manual refresh fallback uses the current topic context, and now verifies `/api/auto-refresh/status` plus `/api/auto-refresh/run` without losing the current topic; Claude freshness diagnosis in `.agent-bridge/TO_CODEX.md`: old topics were not re-collected, while newer topics have July data; human has chosen option B; Claude has replied `ready for human final review = YES`; latest full pre-final gate: backend `218 passed`, frontend build passed, full e2e `88 passed`, `git diff --check` passed, secret/DB status clean except `?? .agents/`, GitNexus `detect-changes` remains expected `critical`. | Human final review remains before marking the whole sprint complete. |
| 3 | Need broader, higher-quality news/source coverage and local pre-analysis. | `V1 Done with known limitation`; Stage 0B continues the source-quality patch without claiming full closure. | `backend/config/feeds.json` now has 38 curated feeds. Stage 0B adds fresh public RSS for U.S. State Department, European Commission, France 24 Spanish, Folha Mundo, France 24 Arabic, and Meduza; keeps OECD/World Bank/IMF/Reuters candidates disabled with honest `zombie/proxy_only/api_license` reasons; and records RT/TASS/RIA/RT Russian as disabled `state_media=true` narrative samples. Source registry persists and returns `coverage/access/last_tested/coverage_reason/state_media`; collection skips `coverage in {zombie, proxy_only}` and `access in {paywalled, api_license}` even if mis-enabled; `backend/tests/test_source_registry.py` -> `13 passed`; targeted RSS checks were run with feedparser on 2026-07-05. | Known limitations: not a full crawler; same-event G20 coverage is not guaranteed; WSJ/AFP/Xinhua/paywalled-wire/API integrations are not solved; some official/multilingual feeds timed out or returned HTML and remain disabled. |
| 4 | Refreshing one panel after LLM deep analysis should not force rerunning or losing LLM analysis. | `Done`. | `frontend/tests/e2e/cross-synthesis-reuse.spec.ts`; `frontend/tests/e2e/job-topic-race.spec.ts`; new `frontend/tests/e2e/source-matrix.spec.ts` test `keeps existing LLM analysis visible when refreshing only the academic layer`; `backend/tests/test_cross_synthesis.py`; fresh full gate evidence is recorded above. | No material-input invalidation hash yet; that is a future improvement, not the core bug. |
| 5 | Community/OpenCLI fails on Windows despite Chrome login. | `Done` for WinError runner and structured diagnostics; platform login/session failures remain `Blocked by external account/API`. | `backend/app/collectors/reddit_sentiment.py`; `.cmd/.bat -> cmd /c` behavior and WinError 193 isolation remain covered by `backend/tests/test_reddit_sentiment_collector.py`; `backend/app/services/opencli_diagnostics.py` now returns optional structured `start_error` for command not found / cannot start / startup timeout; `backend/tests/test_opencli_diagnostics.py` -> `3 passed`; frontend keeps the action order: fix `OPENCLI_COMMAND` first, then Chrome/platform login state. | Platform login/session/API failures still need user environment or platform-specific diagnostics. |
| 6 | Attitude/public-opinion over time is not usable. | `V1 Done with known limitation`. | Media trend evidence in `frontend/src/components/MediaPanel.vue` now shows count deltas, share deltas such as `占比 0% → 56%`, turning periods, sources, and representative reports; backend and frontend now both use conservative first-period vs last-period semantics, and total sample `< 6` or weak count/share deltas stay distribution-only; sentiment sample timeline in `frontend/src/components/SentimentPanel.vue` shows platform, time, confidence, `代表样本`, and `小样本线索`; `backend/tests/test_local_analyze.py`; `frontend/tests/e2e/source-matrix.spec.ts`; `frontend/tests/e2e/sentiment-panel.spec.ts`; `backend/tests/test_sentiment_layer.py`; Claude semantic review PASS found no pseudo-trend red-line issue. | Human final review only; keep wording as sample/platform signals, not public-opinion truth. |
| 7 | Event structure tree should be developmental network/tree. | `V1 Done with known limitation`. | `frontend/src/components/MediaPanel.vue`; `frontend/tests/e2e/source-matrix.spec.ts` event network tests; Claude semantic review PASS confirms edges are local evidence links, not causal proof. | Human final review whether local evidence network is enough for V1. Causal/historical chains are intentionally not claimed. |
| 8 | Event structure tree and event-development flow may be merged. | `V1 Done with known limitation`. | Media UI now centers on `事件发展网络`; source-matrix and timeline details share the same evidence surface; `frontend/tests/e2e/source-matrix.spec.ts`; Claude semantic review PASS. | Further information architecture refinement can follow after final 14-point gate; avoid starting a new graph-workbench feature in this sprint. |
| 9 | Selected Node should appear under clicked event, not bottom. | `Done`. | `frontend/tests/e2e/source-matrix.spec.ts` `shows selected event detail inline below the clicked timeline node`; `frontend/tests/e2e/contextual-drilldown.spec.ts` `shows contextual drilldown inside the selected event detail` and `offers an event-title drilldown when no suggested subtopics exist`; no bottom `.feed-pane > .event-detail`; inline country comparison action visible; fresh full gate evidence is recorded above. | G20/same-event coverage remains limited by source evidence and is tracked under #3. |
| 10 | Academic view needs DOI/authors/journal/source hygiene and academic-review discipline. | `Done`. Claude final review accepted OpenAlex + Crossref as the V1 academic source-breadth answer. | `backend/app/pipeline/academic.py` calls OpenAlex + Crossref through `fetch_academic_papers`; `backend/app/collectors/openalex.py`; `backend/app/collectors/crossref.py`; `backend/tests/test_crossref_collector.py` (`4 passed`); `backend/tests/test_academic_layer.py` (`14 passed, 5 warnings`) verifies Crossref-only fallback, DOI merge, OpenAlex survival when Crossref fails, sample-internal citation discipline, and persisted `sources/source_count/source_links`; `frontend/tests/e2e/academic-panel.spec.ts` (`3 passed`) verifies authors, year, venue, DOI/OpenAlex links, priority-reading signals, readable literature network, and OpenAlex + Crossref provenance display; Claude reviewed DOI normalization, provenance retention, missing-field-only merge behavior, OpenAlex citation primacy, and Crossref fail-soft semantics in `.agent-bridge/TO_CODEX.md` on 2026-07-05. | Formal journal ranking and a third source such as Semantic Scholar remain future academic-quality work, not this sprint's closure criterion. Final sprint gate still required. |
| 11 | Citation graph is unreadable; prefer readable tree/network. | `V1 Done with known limitation`. Claude final review accepted the sample-internal literature network boundary. | `frontend/tests/e2e/academic-panel.spec.ts` (`3 passed`); `backend/tests/test_academic_layer.py` (`14 passed, 5 warnings`); readable literature network in `AcademicPanel.vue` shows nodes and explicit `引用` edges instead of the old unreadable citation-chip graph, with visible wording that it only shows sample-internal citations; paper cards can now show multi-source provenance links when available; Claude confirmed there is no authority-ranking pseudo-claim in `.agent-bridge/TO_CODEX.md` on 2026-07-05. | Known limitation: the network is still sample-internal and does not represent a complete academic/bibliometric map. |
| 12 | Cognition expansion cards need summary, motivation, report link, and deeper path. | `V1 Done with known limitation`. | `frontend/tests/e2e/discovery-cognition.spec.ts`; `frontend/src/components/DiscoveryPanel.vue`; boundary cards now show `摘要`, `相关日报线索`, `深入理由`, `为什么现在重要`, and `建议路径`; discovery archive/timeline tests; fresh full gate evidence is recorded above. | Long-term profile calibration remains future work. |
| 13 | Bilibili video/newsletter/Google Alerts information collection method should inform the source pipeline. | `V1 Done with known limitation`. Claude final review accepted the source-ingestion lead boundary. | `spec/2026-07-03-frontend-feedback.md`; `backend/config/feeds.json`; source registry/import tests; `frontend/src/App.vue` source manager now exposes a visible `情报源导入路径` guide for RSS / Newsletter / Google Alerts, B站视频 / 网页线索, V1 no-transcript boundary, and failed-source status; Claude accepted this scope in `.agent-bridge/TO_CODEX.md` on 2026-07-05. | Newsletter/RSS/Google Alerts leads are represented in source registry/import and the UI now states how video/web leads enter V1. Bilibili/video remains a lead, not a full transcript pipeline; Filo Mail is not an integrated workflow. |
| 14 | Write the conversation into the workspace. | `Done`. | `spec/2026-07-03-frontend-feedback.md`; `spec/current-state.md`; this matrix; audit docs under `spec/`. | Keep UTF-8 files; ignore terminal mojibake from PowerShell display. |

## Remaining Sprint Blockers

1. #3/#10/#11/#13 product-scope reviews are now resolved by Claude's 2026-07-05 final acceptance in `.agent-bridge/TO_CODEX.md`.
2. Final acceptance must rerun the full gate after the final docs/status updates:
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
| #2 | `Done` for parent-context drilldown, stale/manual fallback, backend-running auto-refresh, and frontend status UI/e2e. | Final full gate remains. |
| #3 | `V1 Done with known limitation`. | Final full gate remains; future source batches should not reopen this sprint. |
| #4 | `Done` | Nothing item-specific. |
| #5 | `Done` for Windows runner/diagnostics; external platform login/API may be `Blocked by external account/API`. | Real platform login/API failures remain environment-dependent. |
| #6 | `V1 Done with known limitation`. | Final full gate remains. |
| #7/#8 | `V1 Done with known limitation`. | Final full gate remains. |
| #9 | `Done` | Nothing item-specific. |
| #10 | `Done` for V1 second-source breadth. | Final full gate remains. |
| #11 | `V1 Done with known limitation`. | Final full gate remains. |
| #12 | `V1 Done with known limitation` | Nothing item-specific for this sprint. |
| #13 | `V1 Done with known limitation`. | Final full gate remains. |
| #14 | `Done` | Nothing item-specific. |

## Completion Audit - Pending Final Gate

Claude's final-review acceptance resolves the remaining product-scope decisions. The remaining proof requirement is a fresh final gate after these status updates.

| Item | Current proof | What is still missing | Unblocker |
|---|---|---|---|
| #2 backend freshness automation | Frontend stale explanation and manual refresh are covered; Claude diagnosed old topics were not re-collected; human chose backend-running auto refresh for news/frontier; backend auto-refresh implementation is now present and backend pytest passes; Codex wired frontend status UI/e2e to `/api/auto-refresh/status` and `/api/auto-refresh/run`; Claude replied `ready for human final review = YES`; latest full pre-final gate has backend `218 passed`, frontend build passed, full e2e `88 passed`, `git diff --check` clean except LF/CRLF warnings, secret/DB status clean except `?? .agents/`, and GitNexus `critical` explained as broad central-symbol impact. | Fresh final gate after status/doc updates. | Final gate. |
| #3 news/source quality | Source registry, source manager status, failure reasons, evidence package tests, disabled/limited collection boundary, and classified source batches exist. Current tree evidence: 38 curated feeds; Stage 0B adds U.S. State Dept, EU Commission, France 24 ES/AR, Folha Mundo, and Meduza as fresh/public RSS; OECD/World Bank/IMF/Reuters are disabled with honest reasons; RT/TASS/RIA/RT Russian are disabled state-media samples; backend source-registry tests `13 passed`. | Fresh final gate after status/doc updates. | Final gate. |
| #6 media/community trend semantics | Frontend trend and sentiment timeline e2e pass, with share changes, small-sample downgrade, tiny-bucket markers, and a weak-delta distribution-only regression. Backend and frontend trend semantics now use conservative first-period vs last-period comparison; total sample `< 6` and weak count/share deltas do not produce trend assertions. Codex semantic scan found the UI explicitly says `报道样本`, `不代表民间舆论`, `当前样本只能显示立场分布`, `样本趋势，非事实时间线`, and `小样本线索`; tests assert the key boundaries. | Fresh final gate after status/doc updates. | Final gate. |
| #7/#8 event network semantics | Event network and selected-node e2e pass; Codex semantic scan found no unqualified causal wording in the event-network UI. The visible boundary says `本地证据边，不显示 LLM 因果假设`, and tests assert it; Claude semantic review PASS confirms local evidence links are not being packaged as causal proof. | Fresh final gate after status/doc updates. | Final gate. |
| #10 academic source breadth | Metadata, prompt discipline, DOI/OpenAlex/Crossref provenance, and academic UI tests pass; backend now has OpenAlex + Crossref collection, DOI merge, and Crossref fail-soft tests; Claude accepted DOI normalization, provenance, merge discipline, OpenAlex citation primacy, and Crossref fail-soft behavior. | Fresh final gate after status/doc updates. | Final gate. |
| #11 literature network source hygiene | UI readable literature network passes e2e, paper cards can show OpenAlex + Crossref provenance, and Claude accepted the sample-internal boundary. | Fresh final gate after status/doc updates. | Final gate. |
| #13 source-ingestion lead | Newsletter/RSS and Google Alerts source import have tests; Bilibili video is documented as a lead; source manager now shows a visible source-ingestion path for feeds/newsletters/alerts and video/web leads; Claude accepted the no-transcript V1 boundary. | Fresh final gate after status/doc updates. | Final gate. |

## Completion Rule

Do not mark the sprint complete from this matrix alone.

This matrix is a checkpoint. It becomes final evidence only after the remaining decisions/reviews are resolved and the full gate is freshly rerun.
