# Debug Audit - 2026-07-03

## Scope

This file records the systematic debug pass for the 14-point repair working tree. It focuses on high-risk execution chains where regressions would be user-visible.

Method:

- Trace input -> service -> storage -> payload -> UI.
- Check error boundaries before proposing fixes.
- Require a reproducible failing case before changing business code.

Initial self-debug did not reproduce a bug. A later independent review from Claude found
two reproducible bugs and one semantic UI risk; those findings are recorded in the
follow-up section below.

## Independent Follow-Up Audit - 2026-07-04

Claude reviewed the real dirty diff and found three issues that the first self-audit
missed. Codex reproduced them with failing tests before applying fixes.

### Fixed Bug 1: Async Job Topic Race

Root cause:

- `finishAcademicJob`, `finishSentimentJob`, and `finishCrossSynthesisJob` used the
  live `selectedTopicId.value` after awaiting a background job.
- If the user started a job on topic A, switched to topic B, then topic A's job
  completed, the finish callback reloaded B's layer or wrote stale A data into the
  current UI state.

Fix:

- `runAcademicAnalysis`, `runSentimentAnalysis`, and `runCrossSynthesis` now pass the
  captured launch-time `topicId` into their finish callbacks.
- Finish callbacks only reload the layer when the captured topic is still selected.
- If the user has switched topics, the UI shows a completion note and does not refresh
  the current topic layer.

Regression evidence:

- `frontend/tests/e2e/job-topic-race.spec.ts` covers academic, sentiment, and
  cross-synthesis completion after switching topics.

### Fixed Bug 2: Timeline Tree Dropped Latest Reports

Root cause:

- `_choose_tree_items` grouped items by `run_id`, sorted run ids ascending, then took
  at most five runs. When a branch had more than five report days, the latest report
  could be excluded.

Fix:

- `_choose_tree_items` now iterates run ids in descending order, so the newest report
  receives first display priority while still preserving cross-run coverage.

Regression evidence:

- `backend/tests/test_discovery.py::test_timeline_tree_items_prefer_latest_runs_when_branch_exceeds_limit`
  proves the newest 2026-07-04 run is kept and the oldest run is dropped once the
  display limit is exceeded.

### Fixed Semantic Risk 1: Symmetric Event Edges Looked Directional

Root cause:

- The event development network rendered all edges as `#A → #B`.
- Only chronological edges are directional. Shared article/entity/source edges are
  symmetric local-evidence relationships.

Fix:

- `EventNetworkEdge` now carries `direction: "directed" | "symmetric"`.
- Chronological edges render with `→`; shared local-evidence edges render with `↔`.

Regression evidence:

- `frontend/tests/e2e/source-matrix.spec.ts` asserts chronological edges use `#1 → #2`
  while shared-object and shared-source edges use `#1 ↔ #2`.

## Chain 1: Search, Collection, Local Analysis

Flow:

- Input: `frontend/src/composables/useJobRunner.ts` `runEventSearch`.
- API/job: `POST /api/search/jobs` in `backend/app/api.py`.
- Service: `backend/app/services/search_service.py` `run_search`.
- Topic/storage: `backend/app/topic_ops.py` `get_or_create_topic`, `collect_topic`, `analyze_topic`.
- Payload: events, framing, stance evolution, keywords, entities, criteria, subtopics, analogues.
- UI: `finishSearchJob` writes `localData`, selected event index, diagnostics, subtopics; `MediaPanel.vue` renders timeline/source matrix/event network.

Evidence:

- GitNexus context found `run_search` and processes `Run_search -> Update_job`, `Run_search -> _migrate`, and related local-analysis processes.
- `frontend/tests/e2e/contextual-drilldown.spec.ts` verifies subtopic search becomes parent + subtopic.
- `frontend/tests/e2e/source-matrix.spec.ts` verifies source matrix, event network, and inline selected detail.
- Full backend and e2e gates pass.

Risk:

- GitNexus keyword search is degraded due FTS unavailability; source/test inspection was used instead.
- Structured parent/subtopic payload is not implemented; query composition remains string based.

## Chain 2: Deep Analysis And Evidence Package

Flow:

- Input: `POST /api/topics/{topic_id}/deep-analysis/jobs`.
- Service: `backend/app/services/search_service.py` `run_deep_analysis_job`.
- Core: `backend/app/topic_ops.py` `run_deep_analysis`.
- Enrichment: `enrich_topic_articles`; fulltext/emotion failures degrade and record warnings.
- Local LLM pre-context: `backend/app/services/evidence_package.py` builds source, article, event, entity, and narrative-signal evidence.
- Synthesis: `backend/app/pipeline/synthesize.py` receives `evidence_package`; fallback analysis exists when synthesis fails.
- Storage: timeline/framing/analysis rows via `persist_synthesis`.
- UI: `finishDeepAnalysisJob` reloads topic, articles, local events.

Evidence:

- GitNexus context found `run_deep_analysis` calling `enrich_topic_articles`, `synthesize_topic`, and `persist_synthesis`.
- `backend/tests/test_deep_analysis.py` verifies evidence package is passed and local fields survive without LLM-only assumptions.
- `backend/tests/test_synthesize_pipeline.py` verifies local evidence fields enter prompt context.

Risk:

- LLM output quality is prompt-constrained but not fully schema-validated for academic-style claims.
- Fulltext coverage remains dependent on redirect/body extraction limits.

## Chain 3: Academic/OpenAlex Metadata

Flow:

- Input: `POST /api/topics/{topic_id}/academic/jobs`.
- Service: `backend/app/services/search_service.py` `run_academic_analysis_job`.
- Collector: `backend/app/collectors/openalex.py` `search_works`.
- Analysis: `backend/app/pipeline/academic.py` `run_academic_analysis`, `build_citation_graph`, `analyze_schools`, `synthesize_academic`.
- Storage: `Paper`, `PaperCitation`, `TopicPaper`.
- API: `GET /api/topics/{topic_id}/academic` returns persisted papers plus latest academic job summary.
- UI: `frontend/src/components/AcademicPanel.vue` renders priority signals, DOI/OpenAlex links, citations, and literature network.

Evidence:

- GitNexus context found `run_academic_analysis` and its outgoing calls.
- `backend/tests/test_academic_layer.py` verifies DOI normalization, citation strings, literature network, translation fallback, and synthesize timeout degradation.
- `frontend/tests/e2e/academic-panel.spec.ts` verifies metadata and readable literature network.

Risk:

- OpenAlex requires `OPENALEX_API_KEY`; failures are surfaced as job failures or synthesize warnings depending on step.
- Quality filtering is heuristic only; formal journal ranking is deferred.

## Chain 4: Sentiment/OpenCLI/Hacker News/Reddit

Flow:

- Input: `POST /api/topics/{topic_id}/sentiment/jobs`.
- Service: `backend/app/services/search_service.py` `run_sentiment_analysis_job`.
- Query: `academic.academic_search_query(topic.name)` for Reddit/HN, original Chinese topic for Chinese platforms.
- Collector: `backend/app/collectors/reddit_sentiment.py` `search_all_platforms`.
- Platform boundaries: Reddit API if configured, OpenCLI fallback otherwise; Chinese platforms use OpenCLI; Hacker News uses public API.
- Storage: `SentimentPost`.
- API: `GET /api/topics/{topic_id}/sentiment` includes latest platform errors.
- UI: `SentimentPanel.vue` shows platform coverage, OpenCLI diagnostics, sample cards, comments, and sentiment timeline.

Evidence:

- GitNexus context found `run_sentiment_analysis` calling rank/summarize/persist/payload helpers.
- `backend/tests/test_reddit_sentiment_collector.py` verifies OpenCLI failure isolation and missing-command messages.
- `backend/tests/test_opencli_diagnostics.py` verifies resolved/recommended command diagnostics.
- `frontend/tests/e2e/sentiment-panel.spec.ts` verifies OpenCLI diagnostics and platform timeline.

Risk:

- OpenCLI command availability and Chrome/platform login are separate problems; diagnostics now separate command resolution from platform failures but do not auto-login.
- Low sample counts make sentiment timeline weak evidence by design.

## Chain 5: Cross-Synthesis Voice Reuse

Flow:

- Input: `POST /api/topics/{topic_id}/cross-synthesis/jobs`.
- Request: `CrossSynthesisRequest.refresh_voices`, default `false`.
- Service: `backend/app/services/search_service.py` `run_cross_synthesis_job`.
- If `refresh_voices=false`: gather persisted media/academic/sentiment voices, synthesize, persist.
- If `refresh_voices=true`: rerun media, academic, sentiment voice steps before synthesis.
- Storage: `CrossSynthesis`.
- UI: `frontend/src/composables/useJobRunner.ts` `runCrossSynthesis(false)` default, then `loadCrossSynthesisLayer`.

Evidence:

- GitNexus context found `run_cross_synthesis_job` and affected job update processes.
- `backend/tests/test_cross_synthesis.py` verifies reuse mode skips voice reruns and refresh mode chains voice layers while tolerating one failed voice.
- `frontend/tests/e2e/cross-synthesis-reuse.spec.ts` verifies standalone cross synthesis sends `{ refresh_voices: false }`.

Risk:

- There is no input hash or stale-voice invalidation yet. Reuse is explicit behavior, not automatic freshness reasoning.

## Chain 6: Project/Topic CRUD And Delete Protection

Flow:

- Project list/create/update/delete: `backend/app/api.py` `/api/projects`.
- Topic list/get/create/update/delete: `backend/app/api.py` `/api/topics`.
- Existing topics with no project are backfilled by `ensure_topic_projects`.
- Project deletion rejects non-empty projects with 409.
- Topic deletion calls `topic_ops.remove_topic(..., dry_run=False)`.
- UI: `frontend/src/App.vue` project manager.

Evidence:

- `backend/tests/test_project_topic_management.py` covers project backfill, create/update/archive/delete topic, archive project without deleting topics.
- `frontend/tests/e2e/project-management.spec.ts` covers create/edit/archive/delete project and topic.
- `backend/tests/test_remove_topic.py` covers topic removal cleanup and article sharing behavior.

Risk:

- GitNexus context could not resolve some dirty new API handler names because the index is fresh at commit `8731f0e`, while several handlers are uncommitted. `detect-changes` still reports the broader changed symbol scope.
- No duplicate/fork/search filter UX yet.

## Broad Exception Audit

Observed broad exception boundaries are mostly deliberate external or optional boundaries:

- Network/feed collectors collect request errors and continue where possible.
- OpenAlex retries and raises a clear `RuntimeError` after final failure.
- Academic LLM synthesis failure becomes a warning while papers/citations persist.
- Fulltext extraction returns extraction errors rather than breaking enrichment.
- Search jobs catch top-level task exceptions and store job failure state.

No new fix was applied because no failing reproduction was found. The broad exception boundaries should stay visible through diagnostics, job errors, or warning steps.

## Debug Pass Result

Phase 2 passes after the independent follow-up fixes above.

The highest residual technical risks are stale voice reuse, weak community sample
volume, OpenCLI platform-session dependency, and lack of formal academic quality
ranking.
