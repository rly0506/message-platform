# Backend Test Database Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every backend pytest process and DiscoveryStore fixture use a
unique file-backed SQLite database, with explicit and visible session cleanup.

**Architecture:** Keep `DB_PATH` assignment at conftest import time, but point it
inside a process-owned `TemporaryDirectory`. At session finish, dispose the
already-loaded shared engine and clean the directory without swallowing errors.
Use pytest `tmp_path` for the function-scoped DiscoveryStore fixture.

**Tech Stack:** Python stdlib, pytest, SQLModel/SQLAlchemy, SQLite. No new
dependency and no product-code change.

---

## File Map

- Create `backend/tests/test_test_database_isolation.py`: child-pytest
  regressions for unique paths, successful cleanup, and visible cleanup failure.
- Modify `backend/tests/conftest.py`: process-owned DB directory and session-end
  engine disposal/cleanup.
- Modify `backend/tests/test_discovery.py`: function-owned DiscoveryStore path
  and direct fixture-boundary regression.
- Modify `docs/operations/correctness-audit-test-db-isolation-2026-07-14.md`:
  append RED/GREEN, review, commit, and residual evidence during closeout.

### Task 1: Prove The Isolation Failures

**Files:**

- Create: `backend/tests/test_test_database_isolation.py`
- Modify: `backend/tests/test_discovery.py`

- [x] **Step 1: Add child-pytest probe regressions**

Create `backend/tests/test_test_database_isolation.py` with this structure:

```python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = Path(__file__).resolve().parent

NORMAL_PROBE = """
import os
from pathlib import Path

from app.db import engine


def test_probe_database():
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE cleanup_probe (id INTEGER PRIMARY KEY)"
        )
    Path(os.environ["PROBE_MARKER"]).write_text(
        os.environ["DB_PATH"], encoding="utf-8"
    )
"""

FAILING_CLEANUP_PROBE = """
import os
from pathlib import Path

import conftest
from app.db import engine


def test_install_cleanup_failure():
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE cleanup_probe (id INTEGER PRIMARY KEY)"
        )
    Path(os.environ["PROBE_MARKER"]).write_text(
        os.environ["DB_PATH"], encoding="utf-8"
    )

    def fail_cleanup():
        raise OSError(os.environ["CLEANUP_SENTINEL"])

    conftest._TEST_DB_DIR.cleanup = fail_cleanup
"""


def _run_probe(
    run_dir: Path,
    temp_root: Path,
    source: str = NORMAL_PROBE,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    run_dir.mkdir()
    temp_root.mkdir(exist_ok=True)
    marker = run_dir / "db-path.txt"
    probe = run_dir / "test_probe.py"
    probe.write_text(source, encoding="utf-8")

    env = os.environ.copy()
    env.pop("PYTHON_DOTENV_DISABLED", None)
    pythonpath = [str(TESTS_ROOT), str(BACKEND_ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env.update({
        "PYTHONPATH": os.pathsep.join(pythonpath),
        "PROBE_MARKER": str(marker),
        "CLEANUP_SENTINEL": "audit-cleanup-sentinel",
        "DB_PATH": str(temp_root / "probe-fallback.db"),
        "TMPDIR": str(temp_root),
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
    })
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "conftest",
            str(probe),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    output = result.stdout + result.stderr
    assert marker.exists(), output
    db_path = Path(marker.read_text(encoding="utf-8"))
    assert db_path.resolve().is_relative_to(temp_root.resolve()), output
    return result, db_path


def test_backend_pytest_sessions_use_unique_database_paths(tmp_path):
    temp_root = tmp_path / "shared-temp"
    first, first_path = _run_probe(tmp_path / "first", temp_root)
    second, second_path = _run_probe(tmp_path / "second", temp_root)

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first_path != second_path


def test_backend_pytest_session_removes_its_database_directory(tmp_path):
    result, db_path = _run_probe(
        tmp_path / "normal-cleanup", tmp_path / "normal-temp"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not db_path.exists()
    assert not db_path.parent.exists()


def test_backend_pytest_cleanup_failure_is_visible(tmp_path):
    result, _ = _run_probe(
        tmp_path / "failed-cleanup",
        tmp_path / "failed-temp",
        FAILING_CLEANUP_PROBE,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "audit-cleanup-sentinel" in output
```

The `TMPDIR`, `TEMP`, and `TMP` overrides are mandatory: they confine the old
shared path to the parent test's temporary directory during RED.

- [x] **Step 2: Add the DiscoveryStore fixture-boundary regression**

In `backend/tests/test_discovery.py`, import `Path` and add immediately after the
current `store` fixture:

```python
def test_store_fixture_uses_per_test_database(store, tmp_path):
    assert Path(store.db_path).parent == tmp_path
```

Do not change the fixture yet.

- [x] **Step 3: Run the four regressions and verify RED**

Run:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest `
  tests/test_test_database_isolation.py `
  tests/test_discovery.py::test_store_fixture_uses_per_test_database -q
```

Expected: 4 failures for the intended reasons:

- child session paths are equal;
- the normal child leaves its DB/directory;
- the old conftest does not surface `audit-cleanup-sentinel` from session
  cleanup;
- DiscoveryStore is under the process temp root, not the test's `tmp_path`.

Stop if a test errors before its intended assertion or touches the parent's
active DB path.

Observed RED: `4 failed in 6.75s`. The failures were exactly the shared child
path, residual child database, missing cleanup sentinel, and DiscoveryStore's
global temp parent.

### Task 2: Implement Per-Session And Per-Test Isolation

**Files:**

- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_discovery.py`

- [x] **Step 1: Replace the shared dossier path**

In `backend/tests/conftest.py`, replace the fixed path and startup delete block
with:

```python
import dotenv


# 每个 pytest 进程拥有独立的文件型 SQLite；保留真实锁与连接池语义。
def _ignore_dotenv(*args, **kwargs) -> bool:
    return False


dotenv.load_dotenv = _ignore_dotenv
_TEST_DB_DIR = tempfile.TemporaryDirectory(prefix="dossier-pytest-")
_TEST_DB = str(Path(_TEST_DB_DIR.name) / "dossier_test.db")
os.environ["DB_PATH"] = _TEST_DB


def pytest_sessionfinish(session, exitstatus) -> None:
    """Release pooled SQLite handles, then remove this session's DB directory."""
    db_module = sys.modules.get("app.db")
    if db_module is not None:
        db_module.engine.dispose()
    _TEST_DB_DIR.cleanup()
```

Do not import `app.db` from the hook and do not catch cleanup exceptions.

- [x] **Step 2: Move DiscoveryStore under `tmp_path`**

Replace its fixture with:

```python
@pytest.fixture()
def store(tmp_path):
    path = tmp_path / "discovery_test.db"
    instance = DiscoveryStore(db_path=str(path))
    yield instance
    instance.close()
```

Remove the now-unused `tempfile` import. Retain `os`, which the report helper
still uses.

- [x] **Step 3: Run focused GREEN**

Run the same four-test command from Task 1. Expected: `4 passed`.

Observed: `4 passed in 6.66s`.

- [x] **Step 4: Run the complete DiscoveryStore test module**

Run:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_discovery.py -q
```

Expected: all Discovery tests pass and no fixed `discovery_test.db` is created.

Observed: `41 passed, 1 warning in 3.74s`.

### Task 3: Full Gate, Review, And Delivery

**Files:**

- Modify: `docs/operations/correctness-audit-test-db-isolation-2026-07-14.md`
- Modify locally only: `.agent-bridge/BOARD.md`
- Modify locally only: `.agent-bridge/TO_CLAUDE.md`

- [x] **Step 1: Run the full backend gate**

Run:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest -q
```

Expected before review repairs: `331 passed, 1 warning` (327 baseline plus four
regressions). Explain
any different count instead of updating the expectation silently.

Observed twice: `331 passed, 1 warning` in 86.60s and 76.25s.
After review added three regressions, the fresh full gate passed at
`334 passed, 1 warning in 103.19s`.
After the round-2 Critical repair added the dotenv pre-write regression, the
fresh full gate passed at `335 passed, 1 warning in 38.69s`.

- [x] **Step 2: Verify filesystem and repository safety**

After confirming no pytest process is running, verify the legacy shared file is
the audit-created `C:\TEMP\dossier_test.db`, remove that one file explicitly,
and confirm a second full run does not recreate it. Do not add legacy global
deletion to conftest.

Then run:

```powershell
git diff --check
git status --short -- backend/.env backend/dossier.db backend/discovery.db
git check-ignore -v backend/.env backend/dossier.db backend/discovery.db
```

The real environment and databases must remain unchanged and ignored.

The legacy shared file had already been removed by the final old-conftest RED
session, so no manual deletion was needed. Both new full runs finished with no
top-level `dossier-pytest-*`, fixed `dossier_test.db`, or fixed
`discovery_test.db` under the process temp root. Discovery databases remain only
inside pytest-owned per-test directories retained by pytest's normal debugging
policy; those paths are isolated and rotate with pytest's retention window.
The post-review check found zero session/fixed-path residue and 15 isolated
Discovery DBs in the current pytest retention window.

- [x] **Step 3: Stage only the implementation scope and run GitNexus**

Stage:

```text
backend/tests/conftest.py
backend/tests/test_test_database_isolation.py
backend/tests/test_discovery.py
docs/superpowers/plans/2026-07-14-test-database-isolation.md
docs/superpowers/specs/2026-07-14-test-database-isolation-design.md
```

Run cached diff hygiene and staged `detect-changes`; explain any HIGH or
CRITICAL result before proceeding.

Final pre-review scope: exactly 5 files, 32 symbols, 0 affected flows, `low`;
cached diff check passed.

- [x] **Step 4: Obtain independent review**

Require findings first, exact file/line references, and an APPROVE/REQUEST
CHANGES conclusion. Fix every Critical/Important finding with a new RED test;
assess Minor findings explicitly. Re-run the full backend gate after any code or
test repair.

Review round 1 returned `REQUEST CHANGES`:

- [x] Override inherited `TMPDIR` and `DB_PATH` in child probes, and assert the
  effective database path stays under the requested temp root.
- [x] Add a cross-platform deterministic regression for
  `engine.dispose()` before directory cleanup, then mutation-test it by removing
  or reordering dispose.
- [x] Add the design-promised Windows leaked-handle regression.
- [x] Correct the residue claim: pytest intentionally retains per-test
  DiscoveryStore databases in its rotating debug directories; isolation, not
  immediate deletion, is the fixture contract.
- [x] Re-run focused and full gates, refresh staged GitNexus, and obtain final
  approval.

Review-repair evidence:

- Natural RED: the isolation module reported `1 failed, 5 passed`; the child DB
  followed inherited `TMPDIR` instead of the requested root.
- Cross-platform order mutation RED: temporarily reversing the hook produced
  `['cleanup', 'dispose']` and the order regression failed. The production order
  was immediately restored.
- Repair GREEN: isolation module `6 passed`; isolation plus Discovery boundary
  `7 passed`. The final full-suite expectation is now `334 passed, 1 warning`.

Review round 2 returned `REQUEST CHANGES` with one Critical pre-write escape:
`config.load_dotenv(..., override=True)` can replace conftest's `DB_PATH` from a
legitimate local `.env` before the engine is created.

- [x] Add a safe simulated-dotenv RED proving no first engine write can escape
  the child test root.
- [x] Initially set python-dotenv's `PYTHON_DOTENV_DISABLED=1` guard before any
  `app.*` import; review round 3 later proved this was insufficient for the
  declared dependency range and superseded it.
- [x] Synchronize the authoritative helper snippet and environment contract.
- [x] Document leaked-handle failure as Windows-specific and deterministic
  dispose-before-cleanup order as cross-platform.
- [x] Re-run focused/full gates and obtain final APPROVE. Final expected count:
  Windows `335 passed, 1 warning`; POSIX `334 passed, 1 skipped, 1 warning`.

Round-2 repair evidence:

- Critical RED: the child pytest itself passed, then containment failed because
  simulated dotenv redirected `DB_PATH`; the test-owned simulated user database
  had already been written (8,192 bytes).
- Critical GREEN: targeted `1 passed`; isolation module `7 passed`; isolation
  plus Discovery boundary `8 passed`; full backend `335 passed, 1 warning`.

Review round 3 returned `REQUEST CHANGES`: requirements allow
`python-dotenv>=1.0`, while `PYTHON_DOTENV_DISABLED` support begins only in 1.2,
and the custom simulated loader had encoded the new-version behavior.

- [x] Replace the custom simulation with a real loader call against a
  test-owned dotenv file, explicitly removing inherited disable flags.
- [x] Replace the version-specific environment guard with a process-local
  `dotenv.load_dotenv` no-op before any `app.*` import.
- [x] Verify natural RED again: child pytest wrote the test-owned simulated user
  DB before containment rejected it.
- [x] Verify GREEN: targeted `1 passed`, isolation `7 passed`, and full backend
  `335 passed, 1 warning in 39.32s`.
- [x] Obtain final independent APPROVE on the exact refreshed staged diff.

Final fresh reviewer result: `APPROVE`, with no Critical or Important findings.
Its only Minor was this plan's stale omission of `TMPDIR`; the wording was
corrected before commit. Reviewer verification independently reproduced focused
`8 passed`, full backend `335 passed, 1 warning`, unchanged real database/config
files, zero fixed/session residue, cached diff hygiene, and GitNexus LOW.

- [ ] **Step 5: Commit implementation independently**

After final approval:

```powershell
git commit -m "test: isolate backend sqlite sessions"
```

Do not push or merge `master`.

- [ ] **Step 6: Close audit records and Claude handoff**

Append exact RED/GREEN output, final test count, GitNexus scope, review result,
commit ID, and residual risks to the operation report. Update BOARD and prepend
TO_CLAUDE without deleting prior messages. Stage tracked documentation only,
run the documentation gate, and commit closeout separately.
