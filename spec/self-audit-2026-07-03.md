# Self Audit - 2026-07-03

## Scope

This audit covers the full working tree after the 14-point frontend feedback repair round. It treats the current uncommitted implementation as the product baseline to review, not as unrelated noise to revert.

Audit strategy:

- Scope: whole repository.
- Redundancy strategy: conservative convergence.
- Code-change policy: no business-code edits during this pass unless a reproduced bug or clear behavior-preserving refactor has enough evidence.

## Phase 0 Baseline

Commands run from `D:\意向项目` unless noted:

- `git status --short`: large dirty tree with 47 modified tracked files and multiple untracked repair files under backend, frontend e2e, and `spec/`.
- `git diff --stat`: baseline was `45 files changed, 3891 insertions(+), 546 deletions(-)` before the independent follow-up fixes.
- `node .gitnexus/run.cjs status`: index up-to-date, indexed commit `8731f0e`, current commit `8731f0e`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all`: latest follow-up result is `47 files, 261 symbols`, `75` affected processes, risk `critical`.
- `git diff --check`: exit 0; only LF/CRLF warnings.
- `git check-ignore -v backend/.env backend/dossier.db`: both ignored by `.gitignore`.
- `git status --short -- backend/.env backend/dossier.db`: no output.
- Backend full gate: `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `198 passed, 3 warnings`.
- Frontend build: `cd frontend; npm run build` -> `vue-tsc -b` and Vite build exit 0.
- Frontend e2e: `cd frontend; npm run test:e2e -- --workers=1` -> `62 passed`.

Risk interpretation:

- GitNexus `critical` is caused by the cumulative 14-point repair surface, not by this audit document.
- GitNexus keyword query is degraded because FTS indexes are unavailable; `status` is still up-to-date.

## Requirement Trace

| # | Feedback | Current Behavior | Evidence | Status | Remaining Risk |
|---|---|---|---|---|---|
| 1 | Existing projects need real management, not a simple presentation. | Project/topic CRUD exists: create, edit, archive, delete, topic-in-project, existing-topic backfill into default projects, delete protection for non-empty projects. | `backend/app/db.py` `Project`/`Topic`; `backend/app/api.py` `/api/projects`, `/api/topics`; `frontend/src/App.vue` project manager; `backend/tests/test_project_topic_management.py`; `frontend/tests/e2e/project-management.spec.ts`. | Pass. | UI is still embedded in `App.vue`, which is large; deletion is guarded but duplicate/fork/search filters are not implemented. |
| 2 | Deep-dive chips must preserve context, e.g. `俄乌战争 + 前线态势`. | Subtopic clicks prepend the selected topic name unless already included. | `frontend/src/composables/useJobRunner.ts` `contextualSubtopicQuery`; `frontend/tests/e2e/contextual-drilldown.spec.ts`. | Pass. | Only frontend query composition is covered; structured parent/subtopic payload is not implemented. |
| 3 | Need broader and higher-quality news/intelligence sources and local pre-analysis before LLM. | Source registry exists with curated feeds, user RSS creation, bulk import, status tracking, disabled-source skipping, video-source list entries, evidence package for local source/article/event context before LLM. | `backend/config/feeds.json`; `backend/app/feed_registry.py`; `backend/app/services/source_registry.py`; `backend/app/services/evidence_package.py`; `backend/tests/test_source_registry.py`; `frontend/tests/e2e/source-registry.spec.ts`; `backend/tests/test_deep_analysis.py`; `backend/tests/test_synthesize_pipeline.py`. | Partial pass. | This is still RSS/registry-first, not a full crawler. Some newsletter feeds are intentionally disabled until verified. Full same-event global coverage is not solved. |
| 4 | Refreshing one panel after LLM deep analysis should not force rerunning all LLM analysis. | Cross-synthesis defaults to `refresh_voices=false`, reusing existing media/academic/sentiment voices; explicit refresh can pass `true`. Async academic/sentiment/cross jobs no longer reload a different topic if the user switches before completion. | `backend/app/schemas/search.py`; `backend/app/services/search_service.py` `enqueue_cross_synthesis_job` and `run_cross_synthesis_job`; `backend/tests/test_cross_synthesis.py`; `frontend/tests/e2e/cross-synthesis-reuse.spec.ts`; `frontend/tests/e2e/job-topic-race.spec.ts`; full e2e source-matrix deep-analysis test. | Pass. | Reuse depends on persisted voices being present and current; no material-input invalidation hash yet. |
| 5 | OpenCLI errors persist even though Chrome is open/logged in. | Read-only diagnostics endpoint reports configured command, resolved path, recommended path, and browser-required platforms. Dev launcher resolves `opencli`, `D:\npm-global\opencli.cmd`, or `%APPDATA%\npm\opencli.cmd` and injects `OPENCLI_COMMAND` into backend. Sentiment UI shows actionable diagnostics. | `backend/app/services/opencli_diagnostics.py`; `backend/tests/test_opencli_diagnostics.py`; `run_dev.ps1`; `frontend/src/components/SentimentPanel.vue`; `frontend/tests/e2e/sentiment-panel.spec.ts`; `backend/tests/test_reddit_sentiment_collector.py`. | Pass for diagnosis/dev launch. | It does not guarantee platform session access. If OpenCLI is found but Bilibili/XHS/Xueqiu fail, the user still needs platform-specific browser/login diagnostics. |
| 6 | “Attitude over time” is unusable and should become opinion shift or be removed. | Media stance timeline was relabeled as media stance, with warning that it is not public opinion. Sentiment panel has a separate platform-frame opinion timeline with representative samples and confidence. | `frontend/src/components/MediaPanel.vue`; `backend/app/pipeline/sentiment.py` `sentiment_timeline`; `frontend/src/components/SentimentPanel.vue`; `backend/tests/test_sentiment_layer.py`; `frontend/tests/e2e/sentiment-panel.spec.ts`. | Pass as boundary fix and V1 sentiment timeline. | Sample volume can be low; timeline remains a weak signal, not a robust public-opinion model. |
| 7 | Event structure tree should represent developmental networks/trees, not flat slices. | Media panel shows an event development network with local evidence edges and explicitly avoids LLM causal hypotheses. Chronological edges are directional; shared evidence edges are rendered as symmetric. | `frontend/src/components/MediaPanel.vue`; `frontend/tests/e2e/source-matrix.spec.ts`. | Partial pass. | Local evidence edges are V1; causal/influence hypotheses and richer historical chains are intentionally not implemented. |
| 8 | Event structure tree and event development flow may be merged. | The UI uses a single `事件发展网络` direction and source-matrix/timeline inline details rather than separate competing conceptual sections. | `frontend/src/components/MediaPanel.vue`; `frontend/tests/e2e/source-matrix.spec.ts`. | Partial pass. | There is still more than one media subsection; the merge is semantic and presentation-level, not a full graph-workbench redesign. |
| 9 | Selected node detail should appear under the clicked event and support sources/comparison. | Timeline selected detail appears inline under the clicked node; includes event articles and country/source comparison action. No bottom `Selected Node` card remains. | `frontend/src/components/MediaPanel.vue`; `frontend/tests/e2e/source-matrix.spec.ts` `shows selected event detail inline below the clicked timeline node`; `/api/topics/{id}/country-compare`. | Pass. | Country comparison depends on available articles and does not promise G20 coverage. |
| 10 | Academic layer needs source hygiene, DOI/authors/journal, high-quality filtering, and academic review norms. | Academic layer stores authors, venue, DOI, OpenAlex URL, citation key/string, cited-by count; prompt requires “学界综述”, cited claims, references, DOI/OpenAlex, and OpenAlex sample limitation. UI shows priority-reading signals and paper links. | `backend/app/db.py` `Paper`; `backend/app/pipeline/academic.py`; `backend/tests/test_academic_layer.py`; `frontend/src/components/AcademicPanel.vue`; `frontend/tests/e2e/academic-panel.spec.ts`. | Pass for metadata and prompt contract. | Quality filtering is heuristic, not JCR/CAS/peer-review ranking. LLM output format cannot be fully guaranteed without post-validation. |
| 11 | Academic citation graph is unreadable; prefer media-like tree/network. | Academic panel renders a readable literature network with nodes and edges, citation keys, titles, venue/year/citation counts. | `backend/app/pipeline/academic.py` `literature_network`; `frontend/src/components/AcademicPanel.vue`; `backend/tests/test_academic_layer.py`; `frontend/tests/e2e/academic-panel.spec.ts`. | Pass V1. | Still a compact text/list network, not a canvas. It is intentionally limited to sample-internal citation relationships. |
| 12 | Cognition expansion cards lack summaries and motivation, disconnected from daily report. | Boundary cards include summary, report connection, deep reason, profile evidence, workflow prompt; rest seeds collapse to avoid duplication; archive and cross-day local timeline tree connect reports. | `frontend/src/components/DiscoveryPanel.vue`; `frontend/tests/e2e/discovery-cognition.spec.ts`; `backend/app/discovery/run.py`; `backend/tests/test_discovery.py`; `backend/tests/test_cognition_marks.py`. | Pass V1. | Recommendations are local evidence heuristics; long-term calibration and archive search remain future work. |
| 13 | Bilibili video information-collection method should inform sources. | Conversation/source list is captured; curated feeds include TLDR, The Rundown AI, Morning Brew, Stratechery, Lenny's Newsletter, OpenAI Research, with blocked/unverified sources disabled and notes retained. | `spec/2026-07-03-frontend-feedback.md`; `backend/config/feeds.json`; `backend/tests/test_source_registry.py`. | Partial pass. | No full transcript review was done; Filo Mail and Google Alerts workflow are captured as source-ingestion leads, not fully integrated product workflows. |
| 14 | Write the conversation into the workspace. | Feedback is preserved in `spec/2026-07-03-frontend-feedback.md`; this audit adds a second trace document. | `spec/2026-07-03-frontend-feedback.md`; this file. | Pass. | Some terminal output displays mojibake under the current PowerShell code page, but source files are UTF-8. |

## Requirement Coverage Summary

- Fully covered in current implementation: 1, 2, 4, 5 diagnostics/dev-launch, 6 boundary correction, 9, 10 metadata/prompt, 11 V1, 12 V1, 14.
- Partially covered by V1 and intentionally scoped: 3, 7, 8, 13.
- No feedback item is currently “implemented but unreachable” based on the tested desktop/mobile e2e paths.

## Test Evidence

Backend tests covering this audit:

- `backend/tests/test_project_topic_management.py`
- `backend/tests/test_source_registry.py`
- `backend/tests/test_cross_synthesis.py`
- `backend/tests/test_sentiment_layer.py`
- `backend/tests/test_opencli_diagnostics.py`
- `backend/tests/test_academic_layer.py`
- `backend/tests/test_deep_analysis.py`
- `backend/tests/test_synthesize_pipeline.py`
- `backend/tests/test_discovery.py`
- `backend/tests/test_cognition_marks.py`

Frontend e2e tests covering this audit:

- `frontend/tests/e2e/project-management.spec.ts`
- `frontend/tests/e2e/contextual-drilldown.spec.ts`
- `frontend/tests/e2e/source-registry.spec.ts`
- `frontend/tests/e2e/cross-synthesis-reuse.spec.ts`
- `frontend/tests/e2e/job-topic-race.spec.ts`
- `frontend/tests/e2e/sentiment-panel.spec.ts`
- `frontend/tests/e2e/source-matrix.spec.ts`
- `frontend/tests/e2e/academic-panel.spec.ts`
- `frontend/tests/e2e/discovery-cognition.spec.ts`

## Phase 1 Pass/Fail

Phase 1 passes with residual V1 risks documented above. The remaining risks are product-scope limitations, not failing or unreachable implementations.
