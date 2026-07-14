# Backend Test Database Isolation Design

Status: **APPROVED**

Approved option: per-session SQLite temporary directory with explicit teardown.

## Problem

`backend/tests/conftest.py` currently assigns every pytest process the same
`tempfile.gettempdir()/dossier_test.db` path. Startup tries to remove the prior
file but suppresses `OSError`. A second fixed path exists in the DiscoveryStore
test fixture.

Read-only audit probes established four facts:

- two independent processes receive the same dossier test path;
- an occupied stale database survives startup while the child exits 0;
- the unchanged suite passes 327 tests but leaves a 462,848-byte database;
- returning a SQLite connection to SQLAlchemy's pool is insufficient on
  Windows: deletion raises `PermissionError` until `engine.dispose()` runs.

The detailed evidence is recorded in
`docs/operations/correctness-audit-test-db-isolation-2026-07-14.md`.

## Goals

- Give every backend pytest process a unique file-backed SQLite database.
- Preserve production-like SQLite file, locking, connection-pool, and migration
  behavior; do not replace it with an in-memory database.
- Dispose the shared application engine before deleting the session directory.
- Make teardown failure visible as a non-zero pytest result.
- Give every DiscoveryStore test its own pytest-managed directory.
- Keep the real `backend/dossier.db` and `backend/discovery.db` untouched.

## Non-Goals

- No product database, model, migration, API, collector, or UI change.
- No pytest-xdist dependency or test-runner redesign.
- No generalized temporary-resource framework.
- No suppression or retry loop for leaked file handles. A leak should fail the
  gate so its owner can be fixed.

## Approved Architecture

### Main application test database

At conftest import time, before any `app.*` import:

1. Create one `tempfile.TemporaryDirectory` with a descriptive prefix.
2. Set `DB_PATH` to `<unique-directory>/dossier_test.db`.
3. Replace `dotenv.load_dotenv` with a process-local no-op before any `app.*`
   import, so every supported python-dotenv version ignores `backend/.env` and
   cannot override the test path before the first engine write.
4. Keep the `TemporaryDirectory` owner alive for the pytest process.

This preserves the existing import-order invariant while removing the shared
global filename.

At `pytest_sessionfinish`:

1. Look up `app.db` in `sys.modules`; do not import the application merely to
   perform cleanup.
2. If it was loaded, call its shared `engine.dispose()` so pooled SQLite handles
   are closed.
3. Call `TemporaryDirectory.cleanup()` without an exception-swallowing wrapper.

On Windows, if a test leaks another file handle, cleanup raises and pytest exits
non-zero. POSIX permits unlinking an open file, so a deterministic cross-platform
call-order regression separately proves that engine disposal precedes cleanup.
Both behaviors are intentional: a green gate must prove isolation and teardown.

### DiscoveryStore fixture

Make the function-scoped `store` fixture depend on pytest's `tmp_path` and open
`tmp_path / "discovery_test.db"`. Continue closing the store after `yield`; let
pytest own directory cleanup. Remove only the obsolete `tempfile` import and
manual delete logic.

## Regression Strategy

Add a small infrastructure regression module that runs child pytest sessions.
Each child loads the repository conftest as a plugin and writes its effective
`DB_PATH` to a marker outside the database directory.

The child environment sets `TMPDIR`, `TEMP`, and `TMP` to the parent test's
`tmp_path`, replaces inherited `DB_PATH` with a safe fallback in that same root,
and asserts the effective path remains contained there. This keeps the RED run
isolated: the old implementation may collide inside the test-owned directory
but cannot remove or overwrite the parent's active test database.

Required RED/GREEN cases:

1. Two child sessions report different database paths.
2. A normal child session creates and uses `app.db.engine`, exits 0, and leaves
   neither its database nor its session directory.
3. A simulated local `.env DB_PATH` override cannot redirect the first engine
   write outside the test root. The probe uses a real test-owned dotenv file and
   removes version-specific disable flags before exercising the patched loader.
4. A deterministic cross-platform probe proves engine disposal occurs before
   directory cleanup.
5. On Windows, a child deliberately keeps the database file open through
   session finish; teardown must produce a non-zero result rather than silently
   succeeding. POSIX records this test as skipped.
6. The DiscoveryStore fixture's database parent equals that test's `tmp_path`.

The child probe is local and network-free. It creates only a trivial SQLite
table; it never imports or writes the real project databases.

## Verification

- Run each new regression individually and observe the intended RED before the
  implementation changes.
- Run the infrastructure regression module and Discovery tests to GREEN.
- Run the complete backend suite and account for the exact new test count.
- Confirm no process-level fixed `dossier_test.db`/`discovery_test.db` and no
  session-owned `dossier-pytest-*` directory remains after the full suite.
  Function-scoped Discovery databases may remain only inside pytest-owned,
  per-test directories governed by pytest's rotating debug-retention policy.
- Run diff hygiene, secret/database status, staged GitNexus detect-changes, and
  independent review before committing implementation.

## Alternatives Rejected

- PID-suffixed filenames reduce concurrent collisions but retain stale files
  and can collide after PID reuse.
- In-memory SQLite changes file-locking and connection behavior and therefore
  weakens production fidelity.
- Retrying or suppressing cleanup errors would preserve the original false-green
  failure mode.

## Delivery Boundary

The design document, implementation plan, repair, and closeout records remain
separate commits where practical. No push or merge to `master` is authorized.
