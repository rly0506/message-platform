# Final Audit Report - 2026-07-03

## Objective

Execute the whole-repository self-audit and debug roadmap for the current 14-point repair working tree.

## Deliverables

- `spec/self-audit-2026-07-03.md`
- `spec/debug-audit-2026-07-03.md`
- `spec/redundancy-audit-2026-07-03.md`
- `spec/regression-audit-2026-07-03.md`
- `spec/final-audit-2026-07-03.md`

## Phase Results

- Phase 0 baseline freeze: passed.
- Phase 1 requirement trace audit: passed with V1 residual risks documented.
- Phase 2 self-debug pass: passed after independent follow-up fixes for three missed issues.
- Phase 3 conservative redundancy reduction: passed as no-code refactor decision.
- Phase 4 regression/UX smoke: passed.
- Phase 5 final gate: passed with GitNexus risk explanation.

## Independent Follow-Up Fixes

Claude's independent code audit found two real bugs and one semantic UI risk that the
initial self-audit missed. Codex reproduced each with failing tests, then fixed them:

- Async topic race: academic, sentiment, and cross-synthesis job completion no longer
  reloads or writes the newly selected topic when the job was launched from an older
  topic.
- Discovery timeline tree: branches with more than five report days now keep the
  latest report run instead of the earliest five runs.
- Event network semantics: chronological edges remain directional; shared article,
  entity, and source edges render as symmetric local-evidence links.

## Final Verification

Commands:

- `cd backend; ..\venv\Scripts\python.exe -m pytest -q` -> `198 passed, 3 warnings`.
- `cd frontend; npm run build` -> `vue-tsc -b` and Vite build passed.
- `cd frontend; npm run test:e2e -- --workers=1` -> `62 passed`.
- `git diff --check` -> exit 0; LF/CRLF warnings only.
- `node .gitnexus/run.cjs status` -> up-to-date at commit `8731f0e`.
- `node .gitnexus/run.cjs detect-changes --repo message-platform --scope all` -> `47 files`, `261 symbols`, `75` affected processes, risk `critical`.
- `git check-ignore -v backend/.env backend/dossier.db` -> both ignored by `.gitignore`.
- `git status --short -- backend/.env backend/dossier.db` -> no output.

Additional targeted smoke:

- Backend targeted set for project/source/cross/sentiment/academic/deep analysis -> `56 passed, 3 warnings`.
- Frontend project/context/source/cross smoke -> `14 passed`.
- Frontend media/academic/sentiment/discovery smoke -> `40 passed`.
- Follow-up backend discovery smoke -> `39 passed, 3 warnings`.
- Follow-up frontend source-matrix/job-race smoke -> `12 passed`.

## GitNexus Risk Interpretation

The final GitNexus `critical` risk is expected and matches the baseline cumulative repair surface:

- 47 changed tracked files before audit documents were added.
- 261 changed symbols.
- 75 affected execution flows.
- Main affected flows include cross-synthesis jobs, academic analysis, sentiment loading, and frontend job runners.

This audit mostly added documentation under `spec/`; the independent follow-up applied
three targeted business-code fixes with regression tests. The `critical` result should
still be reviewed as the broader 14-point implementation risk, not as a new isolated
risk introduced by the follow-up fixes.

GitNexus keyword query was degraded because FTS indexes are unavailable, but `status` reports the index is up-to-date. Exact `context` and `impact` checks were still usable for key symbols.

## Residual Risks

- Source coverage has improved through registry/import and curated feeds, but it is not a full crawler and does not guarantee same-event G20 coverage.
- Event-development network is local-evidence V1, not a causal graph.
- Sentiment timeline is a platform-sample signal, not a robust public-opinion model.
- OpenCLI diagnostics and dev-launcher resolution are in place, but platform login/session failures remain external.
- Academic quality filtering is heuristic; formal journal ranking is deferred.
- Cross-synthesis voice reuse has no material-input invalidation hash yet.
- Large files remain: `style.css`, `App.vue`, `DiscoveryPanel.vue`, `MediaPanel.vue`, and `useJobRunner.ts`.

## Next Recommended Work

1. Commit or otherwise freeze the 14-point repair branch after human review, so future GitNexus risk baselines become meaningful again.
2. Do a CSS-only cleanup of project/source manager styles with targeted Playwright screenshots/tests.
3. Extract source registry state from `App.vue` into a dedicated composable.
4. Extract project manager state from `App.vue` into a dedicated composable.
5. Add stale-input detection for cross-synthesis voice reuse.
6. Improve OpenCLI platform-level diagnostics after command resolution succeeds.

## Conclusion

The audit route has been executed end to end. All automated gates passed. The initial
self-audit missed three issues; the independent follow-up reproduced and fixed them.
The current repository state is test-green but broad in scope, so the main delivery
risk is review size and cumulative cross-layer blast radius.
