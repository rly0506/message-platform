# Correctness Audit: Test Database Isolation

Status: **COMPLETE**

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

## Implementation

Implementation commit: `f83f2f3 test: isolate backend sqlite sessions`.

- Every pytest process creates a unique file-backed SQLite database under a
  process-owned `TemporaryDirectory`.
- Before any `app.*` import, conftest replaces `dotenv.load_dotenv` with a
  process-local no-op. This is independent of the supported python-dotenv
  version and prevents a real `backend/.env` from redirecting the first write.
- Session finish disposes the already-loaded shared engine before removing the
  directory; cleanup errors remain visible.
- DiscoveryStore tests use function-scoped `tmp_path` directories instead of a
  shared global filename.

No product configuration, database model, migration, API, collector, or UI was
changed.

## TDD And Review Record

Initial RED (`4 failed`) proved shared child paths, normal-session residue,
silent cleanup behavior, and the global DiscoveryStore path. The first minimal
repair reached focused `4 passed`, Discovery `41 passed`, and two full gates at
`331 passed, 1 warning`.

Independent review round 1 requested stronger environment and lifecycle proof:

- inherited `TMPDIR` redirected a child outside the requested test root;
- dispose-before-cleanup order lacked a cross-platform deterministic test;
- the design-promised Windows leaked-handle case was absent;
- pytest-retained Discovery databases were incorrectly described as residue.

The TMPDIR regression naturally failed (`1 failed, 5 passed`). Reversing the
hook in a controlled mutation produced `['cleanup', 'dispose']` and failed the
new order test. After repair, isolation passed 6 tests, the combined boundary
passed 7, and full backend passed 334 tests.

Review round 2 found a Critical pre-write escape: `config.load_dotenv(...,
override=True)` could replace conftest's DB path from a legitimate local `.env`.
The safe test-owned simulation showed the child pytest passing before the parent
containment assertion failed; an 8,192-byte simulated user DB had already been
written. An initial environment-guard repair reached 335 passing tests.

Review round 3 found that guard was unsupported by the declared
`python-dotenv>=1.0` range and that the custom probe encoded newer behavior. The
probe was replaced with a real loader call against a test-owned dotenv file and
again failed naturally. The final version-independent process-local no-op then
passed targeted, focused, and full gates.

A fresh reviewer returned `APPROVE` with no Critical or Important findings. Its
only Minor was a stale `TMPDIR` omission in the plan wording, corrected before
commit.

## Final Evidence

- Targeted real-dotenv regression: `1 passed`.
- Isolation module: `7 passed`.
- Isolation plus Discovery boundary: `8 passed`.
- Full backend: `335 passed, 1 warning in 39.32s`.
- Real `backend/.env`, `backend/dossier.db`, and `backend/discovery.db`: hashes,
  timestamps, and git status unchanged in independent review.
- Filesystem: no process-level fixed database and no `dossier-pytest-*` session
  directory remained. Discovery DBs exist only in pytest-owned, rotating
  per-test debug directories.
- Final staged GitNexus: 5 files, 32 symbols, 0 affected flows, `low`.
- Cached diff hygiene passed; no push or merge to `master` occurred.

## Residuals

- The Starlette/httpx deprecation warning is unchanged and belongs to a separate
  dependency-maintenance audit.
- Pytest intentionally retains recent `tmp_path` directories for debugging;
  their Discovery databases are unique and cannot affect another session.
- No human product decision is required for this repair.
