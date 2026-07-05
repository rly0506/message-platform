# Current State

Last updated: 2026-07-05.

This file is the context reset point for future agents. Read it before choosing the next iteration.

## Active Sprint

Current active work is the **14 点反馈验收修复 Sprint**. Do not describe the working tree as complete until the 14-point acceptance table is proved item by item.

Coordination split:

- Claude owns backend collection, source freshness, OpenCLI integration review, news/source quality, academic sources, and academic synthesis quality.
- Codex owns frontend UX, media trend readability, contextual drilldown, event network semantics, selected-node inline details, cognition cards, sentiment presentation, and e2e evidence.
- The main checkout is the integration tree. Apply small patches and avoid two agents editing the same file set at the same time.
- Do not commit `.agent-bridge/`, `.agents/`, `backend/.env`, or `backend/dossier.db`.

Latest coordination state:

- #5 OpenCLI WinError 193 has a tested fix in the working tree and Claude has reviewed it as acceptable.
- #2 freshness diagnosis: the collector/DB/payload/UI chain is not proven broken; old topics were not re-collected. Fresh July articles exist in the DB for newer topics.
- #2 frontend stale-state explanation now exists: stale latest-report dates are labeled as last collected time with a manual refresh fallback. The human chose option B, backend auto-refresh implementation is now present in the working tree with backend pytest passing, and Codex has wired the frontend auto-refresh status/run UI to the new API shape. Claude has now replied `ready for human final review = YES`; human final review and final full gate remain before any completion claim.
- #2 event-detail drilldown now has a fallback: if no backend subtopic suggestions exist, the inline selected-event detail shows `围绕此事件` and searches with the parent topic context, such as `俄乌战争 前线态势更新`, instead of a naked event phrase.
- #3 source registry now persists and returns classified source coverage metadata: `coverage`, `access`, `last_tested`, `coverage_reason`, and `state_media`. The frontend Source Manager displays these fields and counts limited sources separately.
- #3 collection boundary is now protected: if source registry rows exist but are all disabled/limited, `collect_topic()` no longer falls back to the raw curated `feeds.json` list. The raw curated fallback is only for empty-registry bootstrap. This supports "limited sources visible but not collected".
- #3 first classified fresh-source batch is now accepted for this repair sprint as `V1 Done with known limitation`: `backend/config/feeds.json` has 25 curated feeds, including 8 `fresh_rss` + `public` sources (UN News, NPR World, The Conversation, CNBC World, The White House, Federal Reserve, European Central Bank, WTO News). This still does not mean full WSJ/AFP/Xinhua/paywalled-wire/API-only/multilingual/G20 coverage; those are future source batches.
- #10/#11 academic layer now has a Crossref second-source backend path in addition to OpenAlex, and Claude accepted it on 2026-07-05. Crossref-only fallback, DOI merge, OpenAlex survival when Crossref fails, `sources/source_count/source_links` persistence, and OpenAlex + Crossref academic-summary/source wording are covered by backend tests. The frontend Academic panel can show `OpenAlex + Crossref`, `来源 N`, and Crossref links per paper. #10 is `Done` for V1 source breadth; #11 is `V1 Done with known limitation`.
- #6 sentiment timeline now labels its linked evidence as `代表样本`, so the user can see which posts support each platform/time/frame bucket.
- #12 cognition boundary cards now use the explicit label `为什么现在重要`, in addition to summary, report connection, deep-dive reason, and suggested path.
- Codex-side P1 frontend slices have fresh targeted desktop e2e evidence: `contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `27 passed (50.8s)`, followed by `npm run build` passing in 428ms and full frontend e2e `84 passed (2.5m)`. The latest 2026-07-05 final gate has backend pytest `218 passed`, frontend build passing in 565ms, and full frontend e2e `88 passed (2.5m)`.
- Fresh final gate evidence is green for backend/frontend/hygiene after Claude's final review and the latest status-doc updates. GitNexus `detect-changes` is now `low` (`19 files`, `41 symbols`, `0` affected processes) after commit1 separated the backend/source/academic integration tree; the earlier pre-final `critical` warning remains historically important for reviewing commit1 but no longer applies to the remaining commit2 frontend/spec surface.
- The current 14-point acceptance ledger is `spec/14-point-acceptance-2026-07-04.md`; use it instead of older audit summaries when deciding what remains.
- The remaining decision packet is `spec/14-point-remaining-decisions-2026-07-04.md`; it now records Claude's #3/#10/#11/#13 final acceptance and the final-gate-only closure path.
- The human final-review packet is `spec/14-point-human-review-2026-07-05.md`; use it as the short decision view for final gate evidence, GitNexus risk, and commit strategy.
- `.agent-bridge/BOARD.md` has been synced with this 14-point sprint state; older 2026-07-03 blocks in that file are historical records only.

## Dirty Worktree Snapshot

Captured from `git status --short` on 2026-07-04 after the acceptance-ledger status cleanup:

```text
 M AGENTS.md
 M CLAUDE.md
 M backend/app/api.py
 M backend/app/collectors/openalex.py
 M backend/app/collectors/reddit_sentiment.py
 M backend/app/db.py
 M backend/app/discovery/run.py
 M backend/app/feed_registry.py
 M backend/app/pipeline/academic.py
 M backend/app/pipeline/sentiment.py
 M backend/app/pipeline/synthesize.py
 M backend/app/schemas/search.py
 M backend/app/services/payloads.py
 M backend/app/services/search_service.py
 M backend/app/topic_ops.py
 M backend/config/feeds.json
 M backend/tests/test_academic_layer.py
 M backend/tests/test_cognition_marks.py
 M backend/tests/test_cross_synthesis.py
 M backend/tests/test_deep_analysis.py
 M backend/tests/test_discovery.py
 M backend/tests/test_openalex_collector.py
 M backend/tests/test_reddit_sentiment_collector.py
 M backend/tests/test_sentiment_layer.py
 M backend/tests/test_synthesize_pipeline.py
 M backend/tests/test_topic_ops.py
 M frontend/src/App.vue
 M frontend/src/api/dossierApi.ts
 M frontend/src/components/AcademicPanel.vue
 M frontend/src/components/CrossPanel.vue
 M frontend/src/components/DiscoveryPanel.vue
 M frontend/src/components/MediaPanel.vue
 M frontend/src/components/SentimentPanel.vue
 M frontend/src/composables/useEventWorkbench.ts
 M frontend/src/composables/useJobRunner.ts
 M frontend/src/composables/useTopicData.ts
 M frontend/src/style.css
 M frontend/src/types/dossier.ts
 M frontend/tests/e2e/academic-panel.spec.ts
 M frontend/tests/e2e/discovery-cognition.spec.ts
 M frontend/tests/e2e/sentiment-panel.spec.ts
 M frontend/tests/e2e/source-matrix.spec.ts
 M run_dev.ps1
 M spec/CHANGELOG.md
 M spec/README.md
 M spec/project.md
 M spec/roadmap.md
?? .agents/
?? backend/app/services/evidence_package.py
?? backend/app/services/opencli_diagnostics.py
?? backend/app/services/source_registry.py
?? backend/tests/test_opencli_diagnostics.py
?? backend/tests/test_project_topic_management.py
?? backend/tests/test_source_registry.py
?? frontend/tests/e2e/contextual-drilldown.spec.ts
?? frontend/tests/e2e/cross-synthesis-reuse.spec.ts
?? frontend/tests/e2e/job-topic-race.spec.ts
?? frontend/tests/e2e/project-management.spec.ts
?? frontend/tests/e2e/source-registry.spec.ts
?? spec/14-point-acceptance-2026-07-04.md
?? spec/14-point-remaining-decisions-2026-07-04.md
?? spec/2026-07-03-frontend-feedback.md
?? spec/current-state.md
?? spec/debug-audit-2026-07-03.md
?? spec/final-audit-2026-07-03.md
?? spec/redundancy-audit-2026-07-03.md
?? spec/regression-audit-2026-07-03.md
?? spec/self-audit-2026-07-03.md
```

This snapshot is broad and cumulative. Treat it as a review-size risk, not as proof that every listed file still needs active editing.

## Product Positioning

The project has moved from a general event-intelligence desk toward a personal cognition-expansion workbench.

Core positioning:

> We cannot understand the world without stories, but we can train ourselves not to be trapped by one story.

The product should not claim to be a truth machine or a system that fully understands the user. Its job is to expose evidence, counterexamples, uncertainty, and reusable thinking models so the user can inspect narratives more clearly.

## Governance

- The user has final decision authority on major product direction and disputed design choices.
- Each iteration must report what changed, how it was verified, what risks remain, and what should happen next.
- Claude/Codex bridge files can be used for coordination, but the repository and `spec/` remain the source of truth.
- Local-first operation is a product goal, not only a fallback. LLM features are optional enhancements.

## Implemented

- Core event workbench:
  - topic search and collection;
  - article storage;
  - local event timeline;
  - source matrix;
  - media, academic, community, cross-synthesis, and LLM-analysis panels.
- Media layer:
  - substance-density visibility;
  - fulltext-assisted emotion-manipulation badge when body text is available;
  - narrative-convergence evidence cards with neutral wording;
  - text-first event structure tree that avoids causal claims.
- Academic layer:
  - OpenAlex-based paper collection;
  - priority-reading signals such as high citation, recent, sample-foundational, venue-clear, and low-information;
  - design notes for later academic reading maps.
- Community layer:
  - Reddit, Hacker News, and OpenCLI-backed platform samples where available;
  - platform coverage status explaining sampled, failed, and no-sample platforms;
  - community content framed as sentiment signal, not fact.
- Discovery / intelligence desk:
  - cognition-frontier daily reports;
  - report archive APIs and frontend history selector;
  - local cross-day cognition timeline tree based on similarity evidence, not causality;
  - cognition-boundary queue;
  - one-click `我懂了` / `存疑` feedback;
  - seed-to-analysis bridge.
- Cognition layer:
  - seed-level cognition marks;
  - local cognition profile initialization;
  - current working tree extends the profile with `depth`, `interest`, `confidence`, `evidence`, and `recommended_seed_style`;
  - current working tree uses profile evidence to explain why boundary seeds are recommended;
  - current working tree adds local workflow prompts for analysis habits such as source checks, numeric口径追问, cost/price/demand framing, financial-statement checks, macro-liquidity framing, open-source risk review, paper checks, and rhetoric-pressure detection.
- Documentation:
  - spec harness, acceptance checklist, roadmap, local capability boundary, academic filtering design, event/literature graph design, and discovery archive / cognition timeline design.

## Partially Implemented

- Cognition expansion loop:
  - boundary queue and profile evidence exist;
  - the profile is not yet continuously calibrated from long-term behavior;
  - the system does not yet confidently answer "which blind spot should be pushed next" from accumulated evidence.
- Local-first intelligence desk:
  - local archive and timeline tree exist;
  - historical search/query/filter across reports, seeds, sources, and marks is not yet implemented.
- Fulltext-dependent judgement:
  - emotion-manipulation badges are deliberately hidden when fulltext is unavailable;
  - Google News redirect URLs still limit body extraction coverage.
- Academic reading:
  - priority-reading labels exist;
  - formal journal ranking and visual literature maps are not implemented.
- Cognition tests:
  - first calibration dialogue produced useful signals;
  - more rounds are needed before treating the profile as stable recommendation evidence.

## Not Implemented / Deferred

- Sentence-level perspective analysis remains deferred unless it becomes fulltext reading assistance or anti-manipulation annotation.
- Large cognition maps and visual graph canvases remain deferred until enough local marks and profile evidence accumulate.
- Vector databases, Supabase, Clerk, Pinecone, heavy queues, and other SaaS migrations are not part of the current plan.
- Google Trends has only been discussed as a possible search-signal supplement; it is not implemented.
- Formal JCR / CAS journal ranking is not implemented.
- LLM causal explanations for cross-day timelines are deferred until local evidence links prove useful.

## Current Working Tree

Latest committed feature before this cleanup:

- `8731f0e feat(discovery): archive daily reports + local cognition timeline tree`

Uncommitted implementation work currently present includes:

- cognition-profile calibration V1 in backend, frontend, tests, and roadmap/changelog;
- 14-point repair implementation across project/topic CRUD, source registry, academic layer, sentiment/OpenCLI, cross-synthesis reuse, media trend/event network, and discovery/cognition cards;
- P0 OpenCLI Windows runner fix in `backend/app/collectors/reddit_sentiment.py` plus tests;
- P1 Codex frontend slices for contextual drilldown and media trend evidence;
- GitNexus metadata updates in `AGENTS.md` and `CLAUDE.md`;
- local untracked `.agents/` and `.agent-bridge/` coordination files, which should not be committed unless explicitly reviewed.

Do not revert these files casually. Treat them as active work that needs human review, final verification, and a commit decision.

## Verification Baseline

Most recent recorded full-gate verification before the latest P0/P1 follow-up:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `198 passed, 3 warnings`;
- `cd frontend; npm run build` -> passed;
- `cd frontend; npm run test:e2e -- --workers=1` -> `62 passed`;
- `git diff --check` -> exit 0, LF/CRLF warnings only;
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, expected for the broad cumulative 14-point repair surface.

Fresh targeted verification from 2026-07-04 after the P0/P1 follow-up:

- Fresh final gate on 2026-07-05 after Claude final review and status-doc updates:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 31.31s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 565ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `88 passed (2.5m)`.
  - `git diff --check` -> pass, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`.
  - `node .gitnexus/run.cjs analyze` -> repository indexed successfully at current commit `0a9a97b`; FTS unavailable warning only.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `0a9a97b`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `low`, `19 files`, `41 symbols`, `0` affected processes.
- Fresh full pre-final gate on 2026-07-05:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `218 passed, 5 warnings in 24.34s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 451ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `88 passed (2.6m)`.
  - `git diff --check` -> pass, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`.
  - `node .gitnexus/run.cjs status` -> up-to-date at current commit `5ed0022`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `27 files`, `101 symbols`, `54` affected processes.
  - This is a verification checkpoint, not a completion claim; after Claude's final review, a fresh final gate remains.
- Fresh backend/GitNexus baseline after the latest coordination updates:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings in 52.41s`.
  - `node .gitnexus/run.cjs analyze` -> repository indexed successfully at current commit `5ed0022`; FTS unavailable warning only.
  - `node .gitnexus/run.cjs status` -> up-to-date at current commit `5ed0022`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `low`, `13 files`, `13 symbols`, `0` affected processes.
  - `git diff --check` -> pass with existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`.
- Fresh Codex-owned frontend retest after the latest `TO_CODEX.md` check:
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `27 passed (50.8s)`.
  - Covered parent-context drilldown, selected-event fallback drilldown, stale refresh context, auto-refresh status/run UI, media stance trend and small-sample downgrade, event network semantics, selected-node inline detail, LLM-refresh reuse, sentiment timeline/OpenCLI diagnostics, and cognition cards.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 428ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `84 passed (2.5m)`.
- Fresh #3 disabled/limited source boundary verification:
  - `node .gitnexus/run.cjs impact -r message-platform "collect_topic" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/topic_ops.py" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/feed_registry.py" --direction upstream --include-tests` -> risk `LOW`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py::test_collect_topic_does_not_fallback_to_curated_feeds_when_registry_sources_are_disabled -q` -> red first because collection fell back to all curated feeds, then `1 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_source_registry.py -q` -> `11 passed, 5 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_topic_ops.py tests/test_api_helpers.py -q` -> `13 passed, 4 warnings`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `210 passed, 5 warnings in 18.98s`.
- Fresh full gate after auto-refresh frontend wiring and GitNexus reindex:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings in 39.31s`.
  - `cd frontend; npm run build` -> passed.
  - `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
  - `git diff --check` -> pass, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`.
  - `node .gitnexus/run.cjs analyze` -> repository indexed successfully; FTS extension unavailable warning only.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `d028496`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `medium`, `16 files`, `45 symbols`, `1` affected execution flow (`RunCrossSynthesis -> FetchCrossSynthesis`).
- Fresh stage-5 full gate refresh:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings in 13.40s`.
  - `cd frontend; npm run build` -> passed (`vue-tsc -b && vite build`; built in 396ms).
  - `cd frontend; npm run test:e2e -- --workers=1` -> `76 passed (2.3m)`.
  - `git diff --check` -> exit 0, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
  - `node .gitnexus/run.cjs status` -> index up-to-date at current commit `8731f0e`.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; broad cumulative 14-point integration tree.
- Fresh full gate after the latest Codex frontend retest:
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `200 passed, 3 warnings in 22.21s`.
  - `cd frontend; npm run build` -> passed.
  - `cd frontend; npm run test:e2e -- --workers=1` -> `76 passed (2.3m)`.
  - `git diff --check` -> exit 0, existing LF/CRLF warnings only.
  - `git status --short -- backend/.env backend/dossier.db .agent-bridge .agents` -> only `?? .agents/`; no `.env`, DB, or bridge file was staged/tracked.
  - `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; broad cumulative 14-point integration tree.
- Fresh Codex high-risk frontend retest after reading the latest `TO_CODEX.md`:
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `25 passed (49.2s)`.
  - Covered parent-context drilldown, selected-event drilldown, stale refresh context, media stance trend and small-sample downgrade, event network semantics, selected-node inline detail, LLM-refresh reuse, sentiment timeline/OpenCLI diagnostics, and cognition cards.
- Fresh source-ingestion guide frontend verification:
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "source-ingestion path"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "coverage mix"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `6 passed`.
  - `cd frontend; npm run build` -> passed.
  - The source manager now visibly explains RSS / Newsletter / Google Alerts import, B站视频 / webpage leads, V1 no-transcript boundary, failed-source status, and current source type/quality-tier mix. This strengthens #3/#13 V1 evidence without implementing video transcription or broader crawler coverage.
- Fresh academic source-scope frontend verification:
  - `cd frontend; npm run test:e2e -- --project=desktop academic-panel.spec.ts -g "priority-reading"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop academic-panel.spec.ts` -> `2 passed`.
  - `cd frontend; npm run build` -> passed.
  - The academic panel now visibly states that the current sample is OpenAlex, that academic reviews must preserve author/year/venue/DOI-or-source links, and that the literature network only shows sample-internal citations. This strengthens #10/#11 UI evidence without resolving the OpenAlex-only backend source limitation.
- Fresh backend auto-refresh review:
  - `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/services/auto_refresh.py" --direction upstream --include-tests` -> target not indexed yet, risk `UNKNOWN`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/api.py" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:backend/app/config.py" --direction upstream --include-tests` -> risk `LOW`, impactedCount `0`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_auto_refresh.py -q` -> `8 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_api_helpers.py tests/test_discovery.py tests/test_source_registry.py -q` -> `56 passed`.
  - `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `208 passed, 5 warnings`.
  - `git diff --check -- backend/app/config.py backend/app/api.py backend/app/services/auto_refresh.py backend/tests/test_auto_refresh.py` -> pass with existing LF/CRLF warning.
  - Codex review sent to `.agent-bridge/TO_CLAUDE.md` found two status-semantics risks; Claude later fixed both: topic-level failures now surface through `news_errors`, and synchronous `refresh_once()` returns after `running=False`.
- Fresh frontend auto-refresh status wiring:
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/App.vue" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/api/dossierApi.ts" --direction upstream --include-tests` -> risk `MEDIUM`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/types/dossier.ts" --direction upstream --include-tests` -> risk `MEDIUM`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/tests/e2e/source-matrix.spec.ts" --direction upstream --include-tests` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "auto-refresh status"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `15 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `26 passed`.
  - `cd frontend; npm run build` -> passed.
  - `cd frontend; npm run test:e2e -- --workers=1` -> `82 passed (2.8m)`.
  - `git diff --check -- frontend/src/App.vue frontend/src/api/dossierApi.ts frontend/src/types/dossier.ts frontend/src/style.css frontend/tests/e2e/source-matrix.spec.ts` -> pass with existing LF/CRLF warning.
- Fresh event-detail drilldown fallback verification:
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/components/MediaPanel.vue" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/composables/useJobRunner.ts" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/tests/e2e/contextual-drilldown.spec.ts" --direction upstream --include-tests` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts -g "event-title drilldown"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts` -> `3 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "selected event detail|event structure tree|local evidence edges"` -> `3 passed` after rerunning serially.
  - `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `15 passed`.
  - `cd frontend; npm run build` -> passed.
- Fresh sentiment timeline evidence-label verification:
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/components/SentimentPanel.vue" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/tests/e2e/sentiment-panel.spec.ts" --direction upstream --include-tests` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts -g "sentiment change timeline"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts` -> `3 passed`.
  - `cd frontend; npm run build` -> passed.
- Fresh cognition-card importance wording verification:
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/src/components/DiscoveryPanel.vue" --direction upstream --include-tests` -> risk `LOW`.
  - `node .gitnexus/run.cjs impact -r message-platform "File:frontend/tests/e2e/discovery-cognition.spec.ts" --direction upstream --include-tests` -> risk `LOW`.
  - `cd frontend; npm run test:e2e -- --project=desktop discovery-cognition.spec.ts -g "seed summary"` -> red first, then `1 passed`.
  - `cd frontend; npm run test:e2e -- --project=desktop discovery-cognition.spec.ts` -> `6 passed`.
  - `cd frontend; npm run build` -> passed.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `31 passed` in 49.8s on the latest Codex-owned frontend retest.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `25 passed` in 49.3s after the latest bridge-plan review.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts project-management.spec.ts cross-synthesis-reuse.spec.ts job-topic-race.spec.ts source-matrix.spec.ts sentiment-panel.spec.ts discovery-cognition.spec.ts` -> `26 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "keeps existing LLM analysis"` -> `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `11 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts -g "selected event detail"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop contextual-drilldown.spec.ts source-matrix.spec.ts` -> `13 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts -g "summarizes source coverage"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-registry.spec.ts` -> `4 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "explains stale"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "refreshes stale"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "summarizes media stance"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts -g "degrades media stance"` -> red first, then `1 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts` -> `14 passed`.
- `cd frontend; npm run test:e2e -- --project=desktop sentiment-panel.spec.ts -g "sentiment change timeline"` -> red first, then `1 passed`.
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
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> risk `critical`, `47 files`, `281 symbols`, `75` affected processes; broad cumulative 14-point integration tree.

Covered by that targeted desktop run:

- project/topic CRUD;
- contextual subtopic drilldown with parent topic context;
- stale latest-report date warning with a manual refresh fallback that uses the current topic context;
- selected event detail contains contextual drilldown chips;
- standalone cross-synthesis reuse mode;
- async academic/sentiment/cross job completion after topic switch;
- LLM analysis remains visible when refreshing only the academic layer;
- discovery cognition cards, report archive, and cognition timeline tree;
- media source matrix, stance trend panel with count/share changes and small-sample downgrade, event network, selected-event inline detail, and LLM bundle reuse path;
- source manager status summary for total/enabled/failed sources, latest successful fetch, and failed-source reasons;
- sentiment sample cards, opinion-change timeline with tiny-bucket markers, and OpenCLI diagnostics.
- academic citation metadata UI and readable literature network, with OpenAlex + Crossref provenance now present in the backend and frontend evidence.

These numbers are recorded for context. Future agents must rerun the relevant commands before claiming a new change is complete.

## Next Iteration Candidates

Recommended next sprint actions:

1. Rerun the full final gate after the latest status/doc updates.
2. Record the final gate evidence and GitNexus risk explanation in the acceptance/current-state/changelog docs.
3. Stage only frontend/spec files for commit2, excluding `AGENTS.md`, `CLAUDE.md`, `.agent-bridge/`, `.agents/`, `backend/.env`, and `backend/dossier.db`.
4. Before any completion claim, produce a 14-point table using only:
   - `Done`
   - `V1 Done with known limitation`
   - `Blocked by external account/API`
