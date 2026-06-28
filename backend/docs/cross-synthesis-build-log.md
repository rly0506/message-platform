# Cross Synthesis Build Log

## Baseline
- Real DB MD5 before work: `AFC549F58A930714AC68AE7261E437E1`
- Scope: build cross-voice synthesis from existing media, academic, and sentiment layers.
- Network/LLM/real DB writes: forbidden during tests; all LLM calls mocked.

## CP1 - Voice Gathering
- Started: add tests for `gather_voices(session, topic)` using synthetic database rows.
- Expected first failure: `app.pipeline.cross_synthesis` does not exist yet.
- Implemented `app/pipeline/cross_synthesis.py` read-only voice aggregation.
- Local CP1 tests: `2 passed`.
- Gate: `python -m pytest backend/tests -q` -> `68 passed, 3 warnings`.
- Real DB MD5 after CP1: `AFC549F58A930714AC68AE7261E437E1`
- Deviations: none.

## CP2 - LLM Cross Synthesis
- Started: add mocked LLM tests for five-section cross-synthesis prompt.
- Implemented `cross_synthesize(topic, voices)` with a mocked-LLM test ensuring five required sections:
  `三方共识` / `三方矛盾` / `各自盲区` / `机制重建` / `批判提示`.
- Prompt explicitly includes `分析机制与因果，不做道德归责` and marks public sentiment as `非事实源`.
- Local CP2 tests: `4 passed`.
- Gate: `python -m pytest backend/tests -q` -> `70 passed, 3 warnings`.
- Deviation: Real DB MD5 check initially failed because `backend/dossier.db` was locked by another process. Retry returned
  `68EC05AE5DE6AC62D531039436F20020`, different from baseline `AFC549F58A930714AC68AE7261E437E1`.
- Read-only audit found latest real DB write is a real `sentiment:美伊战争` SearchJob:
  id `6dab6b21595f4d8eb4615381e985167d`, status `done`, updated at `2026-06-27 05:53:40.169143`,
  with `sentimentpost` count now `15`.
- This appears to be an external running backend/frontend action, not pytest, because tests use `DB_PATH` from `backend/tests/conftest.py`.
- Action taken: stopped before CP3 per checkpoint rule; no rollback performed.
- User confirmed the real sentiment job was run concurrently outside this task.
- Resuming from new real DB baseline MD5: `68EC05AE5DE6AC62D531039436F20020`.

## CP3 - Table, Background Job, API
- Started after user confirmation.
- Impact note: `init_db` reports CRITICAL because all API/CLI paths pass through it; CP3 only appends a new SQLModel table and does not alter existing migrations.
- `enqueue_sentiment_analysis_job` was not found in current GitNexus index, likely stale from previous task additions.
- Added `CrossSynthesis` table, `cross_synthesis.run_cross_synthesis(...)`, background SearchJob wiring, and
  `GET/POST /api/topics/{id}/cross-synthesis`.
- Red test observed: `ImportError: cannot import name 'CrossSynthesis' from 'app.db'`.
- Local CP3 tests: `8 passed, 3 warnings`.
- Gate: `python -m pytest backend/tests -q` using `venv\Scripts\python.exe` -> `74 passed, 3 warnings`.
- Real DB MD5 after CP3: `68EC05AE5DE6AC62D531039436F20020`.
- Deviations: shell `python` points to `C:\Users\...\agent-reach-venv` without pytest, so gates use the project `venv\Scripts\python.exe`.

## CP4 - Frontend Integration
- Added `CrossSynthesis` frontend type plus `fetchCrossSynthesis(...)` and `createCrossSynthesisJob(...)`.
- Added a prominent `三方对照` action in the topic summary and a wide `三方对照` panel before the voice-specific layers.
- Rendering uses existing `marked` + `DOMPurify` sanitized markdown path.
- Empty state: `请先运行媒体/学界/民间分析，再生成三方对照。`
- Voice badges show which voices were used; missing voices do not crash the view.
- Gate: `npx vue-tsc --noEmit` -> exit `0`.
- Gate: `python -m pytest backend/tests -q` using `venv\Scripts\python.exe` -> `74 passed, 3 warnings`.
- Real DB MD5 after CP4: `68EC05AE5DE6AC62D531039436F20020`.
- Deviations: none.

## CP5 - Final Verification
- Started final full verification.
- Final backend gate: `python -m pytest backend/tests -q` using `venv\Scripts\python.exe` -> `74 passed, 3 warnings`.
- Final frontend gate: `npx vue-tsc --noEmit` -> exit `0`.
- Real DB MD5 after final verification: `68EC05AE5DE6AC62D531039436F20020`.
- GitNexus `detect-changes` output: `No changes detected.`
- Git caveat: `git ls-files` returns `0`, so the repository currently has no tracked files; `detect-changes`/`git diff`
  cannot map untracked workspace files to an affected-flow diff. Explicit touched-file audit:
  `backend/app/db.py`, `backend/app/pipeline/cross_synthesis.py`, `backend/app/services/search_service.py`,
  `backend/app/api.py`, `backend/tests/test_cross_synthesis.py`, `frontend/src/types/dossier.ts`,
  `frontend/src/api/dossierApi.ts`, `frontend/src/App.vue`, `frontend/src/style.css`,
  `backend/docs/cross-synthesis-build-log.md`.
- Deviations: no real network or LLM calls; no intentional real database writes. The real DB MD5 remained unchanged from
  the user-confirmed resumed baseline.
