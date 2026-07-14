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

- [ ] **Step 1: Add child-pytest probe regressions**

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
) -> tuple[subprocess.CompletedProcess[str], Path]:
    run_dir.mkdir()
    temp_root.mkdir(exist_ok=True)
    marker = run_dir / "db-path.txt"
    probe = run_dir / "test_probe.py"
    probe.write_text(source, encoding="utf-8")

    env = os.environ.copy()
    pythonpath = [str(TESTS_ROOT), str(BACKEND_ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env.update({
        "PYTHONPATH": os.pathsep.join(pythonpath),
        "PROBE_MARKER": str(marker),
        "CLEANUP_SENTINEL": "audit-cleanup-sentinel",
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
    })
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
    return result, Path(marker.read_text(encoding="utf-8"))


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

The `TEMP` and `TMP` override is mandatory: it confines the old shared path to
the parent test's temporary directory during RED.

- [ ] **Step 2: Add the DiscoveryStore fixture-boundary regression**

In `backend/tests/test_discovery.py`, import `Path` and add immediately after the
current `store` fixture:

```python
def test_store_fixture_uses_per_test_database(store, tmp_path):
    assert Path(store.db_path).parent == tmp_path
```

Do not change the fixture yet.

- [ ] **Step 3: Run the four regressions and verify RED**

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

### Task 2: Implement Per-Session And Per-Test Isolation

**Files:**

- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_discovery.py`

- [ ] **Step 1: Replace the shared dossier path**

In `backend/tests/conftest.py`, replace the fixed path and startup delete block
with:

```python
# 每个 pytest 进程拥有独立的文件型 SQLite；保留真实锁与连接池语义。
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

- [ ] **Step 2: Move DiscoveryStore under `tmp_path`**

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

- [ ] **Step 3: Run focused GREEN**

Run the same four-test command from Task 1. Expected: `4 passed`.

- [ ] **Step 4: Run the complete DiscoveryStore test module**

Run:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest tests/test_discovery.py -q
```

Expected: all Discovery tests pass and no fixed `discovery_test.db` is created.

### Task 3: Full Gate, Review, And Delivery

**Files:**

- Modify: `docs/operations/correctness-audit-test-db-isolation-2026-07-14.md`
- Modify locally only: `.agent-bridge/BOARD.md`
- Modify locally only: `.agent-bridge/TO_CLAUDE.md`

- [ ] **Step 1: Run the full backend gate**

Run:

```powershell
cd backend
..\venv\Scripts\python.exe -m pytest -q
```

Expected: `331 passed, 1 warning` (327 baseline plus four regressions). Explain
any different count instead of updating the expectation silently.

- [ ] **Step 2: Verify filesystem and repository safety**

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

- [ ] **Step 3: Stage only the implementation scope and run GitNexus**

Stage:

```text
backend/tests/conftest.py
backend/tests/test_test_database_isolation.py
backend/tests/test_discovery.py
docs/superpowers/plans/2026-07-14-test-database-isolation.md
```

Run cached diff hygiene and staged `detect-changes`; explain any HIGH or
CRITICAL result before proceeding.

- [ ] **Step 4: Obtain independent review**

Require findings first, exact file/line references, and an APPROVE/REQUEST
CHANGES conclusion. Fix every Critical/Important finding with a new RED test;
assess Minor findings explicitly. Re-run the full backend gate after any code or
test repair.

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
