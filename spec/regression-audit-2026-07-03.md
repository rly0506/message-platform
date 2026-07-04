# Regression Audit - 2026-07-03

## Scope

This phase smoke-tested the user-visible paths most directly tied to the 14 feedback items.

## Commands

Backend targeted smoke:

- `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_project_topic_management.py tests/test_source_registry.py tests/test_cross_synthesis.py tests/test_sentiment_layer.py tests/test_academic_layer.py tests/test_deep_analysis.py -q`
- Result: `56 passed, 3 warnings`.

Frontend targeted smoke group A:

- `cd frontend; npm run test:e2e -- --workers=1 tests/e2e/project-management.spec.ts tests/e2e/contextual-drilldown.spec.ts tests/e2e/source-registry.spec.ts tests/e2e/cross-synthesis-reuse.spec.ts`
- Result: `14 passed`.

Frontend targeted smoke group B:

- `cd frontend; npm run test:e2e -- --workers=1 tests/e2e/source-matrix.spec.ts tests/e2e/academic-panel.spec.ts tests/e2e/sentiment-panel.spec.ts tests/e2e/discovery-cognition.spec.ts`
- Result: `40 passed`.

Independent follow-up smoke:

- `cd backend; ..\venv\Scripts\python.exe -m pytest tests/test_discovery.py -q`
- Result: `39 passed, 3 warnings`.
- `cd frontend; npm run test:e2e -- --project=desktop source-matrix.spec.ts job-topic-race.spec.ts`
- Result: `12 passed`.

Final full gates after follow-up:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q`
- Result: `198 passed, 3 warnings`.
- `cd frontend; npm run build`
- Result: passed.
- `cd frontend; npm run test:e2e -- --workers=1`
- Result: `62 passed`.

## User Paths Covered

- Project/topic create, edit, archive, delete.
- Contextual subtopic drilldown.
- Source registry list, pause, manual RSS add, bulk import.
- Cross-synthesis reuse mode by default.
- Source matrix filters and mobile layout.
- Event development network and inline selected event detail.
- Async job completion after switching topics for academic, sentiment, and cross-synthesis layers.
- LLM deep-analysis bundle starts academic, sentiment, and reuse-voices cross-synthesis.
- Academic priority-reading labels, DOI/OpenAlex links, readable literature network.
- Sentiment sample cards, platform coverage, opinion-change timeline, OpenCLI diagnostics.
- Cognition boundary cards with summary, report connection, suggested path, feedback marks, report archive, and local cross-day timeline tree.

## Result

Phase 4 passes.

No manual browser-only issue was found through automated desktop/mobile smoke coverage.
