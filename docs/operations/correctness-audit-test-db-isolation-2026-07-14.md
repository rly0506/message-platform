# Correctness Audit: Test Database Isolation

Status: **CONFIRMED FINDING - DESIGN APPROVED**

Date: 2026-07-14

Branch: `feature/academic-reading-signals`

## Audit Question

Can two backend pytest sessions run independently, and does a green session
leave no stale SQLite database that can affect the next gate?

## Confirmed Evidence

1. `backend/tests/conftest.py` assigns every process the same path:
   `C:\TEMP\dossier_test.db`.
2. Two independent Python processes loaded that conftest and reported the same
   path (`collision=True`).
3. In an isolated temporary directory, a pre-existing open
   `dossier_test.db` survived conftest startup. The child process still exited
   `0` because the `OSError` from deletion was swallowed.
4. The unchanged full backend gate passed (`327 passed, 1 warning`), but left a
   462,848-byte `C:\TEMP\dossier_test.db` after process exit.
5. `backend/tests/test_discovery.py` independently repeats the fixed shared-path
   pattern with `discovery_test.db` and also suppresses teardown deletion errors.

These observations prove that ordinary single-session green tests do not cover
parallel-session collision, stale-state startup, or teardown cleanup.

## Risk

- Concurrent agents or local test commands can write the same SQLite file.
- A crashed or still-running process can make the next session silently reuse a
  stale database instead of starting clean.
- A false failure wastes debugging time; a false green is worse because it
  weakens the release gate's evidentiary value.
- The real `backend/dossier.db` remains protected by `DB_PATH`; this finding is
  about test-session isolation, not evidence that the production database was
  touched.

## GitNexus Scope

- `_TEST_DB` in `backend/tests/conftest.py`: exact upstream impact LOW, 0 direct
  dependents, 0 processes.
- `store` fixture in `backend/tests/test_discovery.py`: exact upstream impact
  LOW, 0 direct dependents, 0 processes (tests included).
- Index was fresh at implementation HEAD `5a53e41` when impact was measured.

## Baseline

```text
..\venv\Scripts\python.exe -m pytest -q
327 passed, 1 warning in 65.18s
```

The existing Starlette/httpx deprecation warning is unrelated and remains a
separate dependency-maintenance concern.

## Decision Gate

The user approved per-session file-backed SQLite isolation with explicit
teardown (option 1). The authoritative design is
`docs/superpowers/specs/2026-07-14-test-database-isolation-design.md`.
No remediation code had been written when this status changed; implementation
must begin with the documented RED tests.
