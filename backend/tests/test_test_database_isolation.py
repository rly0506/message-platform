from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


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

LEAKED_HANDLE_PROBE = """
import os
from pathlib import Path

from app.db import engine


_open_handle = None


def test_leave_database_handle_open():
    global _open_handle
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE cleanup_probe (id INTEGER PRIMARY KEY)"
        )
    Path(os.environ["PROBE_MARKER"]).write_text(
        os.environ["DB_PATH"], encoding="utf-8"
    )
    _open_handle = open(os.environ["DB_PATH"], "rb")
"""

DOTENV_OVERRIDE_PROBE = """
import os
from pathlib import Path

import dotenv

os.environ.pop("PYTHON_DOTENV_DISABLED", None)
dotenv.load_dotenv(os.environ["SIMULATED_DOTENV"], override=True)
dotenv.load_dotenv = lambda *args, **kwargs: False

from app import config
from app.db import engine


def test_dotenv_cannot_redirect_database():
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE cleanup_probe (id INTEGER PRIMARY KEY)"
        )
    Path(os.environ["PROBE_MARKER"]).write_text(
        config.DB_PATH, encoding="utf-8"
    )
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


def test_child_probe_overrides_inherited_tmpdir(tmp_path, monkeypatch):
    inherited_temp = tmp_path / "inherited-temp"
    inherited_temp.mkdir()
    monkeypatch.setenv("TMPDIR", str(inherited_temp))
    requested_temp = tmp_path / "requested-temp"

    result, db_path = _run_probe(tmp_path / "confined", requested_temp)

    assert result.returncode == 0, result.stdout + result.stderr
    assert db_path.resolve().is_relative_to(requested_temp.resolve())


def test_dotenv_cannot_override_backend_test_database(tmp_path):
    simulated_user_db = tmp_path / "simulated-user.db"
    simulated_dotenv = tmp_path / "simulated.env"
    simulated_dotenv.write_text(
        f"DB_PATH={simulated_user_db.as_posix()}\n", encoding="utf-8"
    )

    result, _ = _run_probe(
        tmp_path / "dotenv-override",
        tmp_path / "dotenv-temp",
        DOTENV_OVERRIDE_PROBE,
        {"SIMULATED_DOTENV": str(simulated_dotenv)},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not simulated_user_db.exists()


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


def test_session_finish_disposes_engine_before_cleanup(monkeypatch):
    import conftest

    calls = []
    db_module = SimpleNamespace(
        engine=SimpleNamespace(dispose=lambda: calls.append("dispose"))
    )
    temp_owner = SimpleNamespace(cleanup=lambda: calls.append("cleanup"))
    monkeypatch.setitem(sys.modules, "app.db", db_module)
    monkeypatch.setattr(conftest, "_TEST_DB_DIR", temp_owner)

    conftest.pytest_sessionfinish(None, 0)

    assert calls == ["dispose", "cleanup"]


@pytest.mark.skipif(os.name != "nt", reason="Windows file-lock regression")
def test_backend_pytest_leaked_database_handle_fails_cleanup(tmp_path):
    result, _ = _run_probe(
        tmp_path / "leaked-handle",
        tmp_path / "leaked-temp",
        LEAKED_HANDLE_PROBE,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "PermissionError" in output
