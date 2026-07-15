# RM-055 Coverage Observation Pipeline Task Report

Status: **IMPLEMENTED; OBSERVATION WINDOW NOT STARTED**

Branch: `feature/academic-reading-signals`

Implementation commit: `e4a0a35 feat(rm055): add coverage observation pipeline`

Test-isolation commit: `6c3e316 test(rm055): isolate observation evidence in pytest`

Push/merge policy: do not push; do not merge `master`.

## Goal And Boundary

This is the RM-055 evidence gate, not a source-expansion batch. It records
auditable, post-commit coverage observations so a later source decision can be
based on recurring gaps rather than a one-off impression. It does not add a
feed, enable a disabled source, persist article full text, make an LLM call, or
make a GO/NO-GO decision automatically.

## Delivered Contract

- The recorder runs only after collection has committed and its write session
  has closed. A recorder failure is isolated from the refresh result and
  `news_errors`.
- Each run writes an immutable, atomic filesystem manifest under the ignored
  `backend/coverage_observations/` root. The verifier checks file hashes,
  ownership, duplicate entries, and no-overwrite semantics.
- Counts preserve endpoint `unknown` values and unclassified metadata; they do
  not substitute zero or claim that an uncollected source did not report.
- `coverage-status` and `coverage-verify` inspect only filesystem evidence.
  `refresh-once` is HTTP-first and fails closed on an ambiguous transport
  failure instead of silently falling back to the local production database.
- The daily script order is discover, `refresh-once`, then email. The refresh
  API contract remains the exact existing nine-field payload.

## Review And Verification

- Specification review: `APPROVE`.
- Quality review: `APPROVE`.
- Independent test-isolation review: `APPROVE`, with no Critical, Important, or
  Minor finding. It confirmed that pytest sets `COVERAGE_OBSERVATIONS_DIR`
  inside its existing session `TemporaryDirectory` before any `app.*` import.
- Focused backend gate:
  `..\\venv\\Scripts\\python.exe -m pytest tests\\test_auto_refresh_observation.py tests\\test_coverage_observation.py -q`
  -> `14 passed`.
- Full backend gate after the isolation fix:
  `..\\venv\\Scripts\\python.exe -m pytest -q` -> `368 passed, 1 warning`.
- The implementation gate also passed frontend build (98 modules) and controlled
  desktop/mobile E2E (`184 passed`).
- The original staged GitNexus scope was 9 files, 22 symbols, 0 flows, `low`.
  The isolation commit's staged scope was 2 files, 2 symbols, 0 flows, `low`.
- Before the isolation commit, `git diff --check` passed. The focused test was
  run with `backend/coverage_observations/` empty before and after; its evidence
  root is now contained below the temporary test database root.

## Authorized Real-Run Result

The authorized command was attempted once:

```powershell
cd backend
..\venv\Scripts\python.exe cli.py refresh-once
```

It exited `1` with `{"error":"health transport failed: URLError"}`.
Read-only checks showed that `127.0.0.1:8000` timed out through
`Test-NetConnection`, `socket.create_connection`, and `urllib`. This is not an
explicit connection refusal, so the fail-closed path correctly did not fall
back to an in-process refresh or write the real local database.

After cleanup, filesystem evidence reports:

```json
{
  "review_state": "HOLD",
  "first_successful_date": null,
  "successful_date_count": 0,
  "window_end": null
}
```

## Current Decision And Next Action

The first successful observation date and 14-day window remain unset. Source
expansion is still `HOLD`; the 2026-07-27 review is not an automatic approval
and cannot proceed without the gate evidence in
`docs/operations/rm055-source-expansion-gate-2026-07-13.md`.

Do not start a temporary Uvicorn instance, call the refresh service directly,
or weaken the HTTP-first fallback rule merely to manufacture the first day.
Retry the real command only after port 8000 returns either a genuine backend
response or an explicit connection refusal.
