"""Pytest 引导：路径 + 测试库隔离。

关键：必须在任何 `app.*` 被导入前设置 DB_PATH 环境变量。
config.py 在 import 时读取 DB_PATH，db.py 据此构建 engine；
pytest 会先加载 conftest 再加载测试模块，因此此处设置可彻底隔离真实库。
测试同时禁用 backend/.env，避免 override=True 在首次写入前改回用户路径。
"""
import os
import sys
import tempfile
from pathlib import Path

import dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 测试进程不读取用户 .env；必须早于 app.config 的 from-import。
def _ignore_dotenv(*args, **kwargs) -> bool:
    return False


dotenv.load_dotenv = _ignore_dotenv

# 每个 pytest 进程拥有独立的文件型 SQLite；保留真实锁与连接池语义。
_TEST_DB_DIR = tempfile.TemporaryDirectory(prefix="dossier-pytest-")
_TEST_ROOT = Path(_TEST_DB_DIR.name)
_TEST_DB = str(_TEST_ROOT / "dossier_test.db")
os.environ["DB_PATH"] = _TEST_DB
os.environ["COVERAGE_OBSERVATIONS_DIR"] = str(_TEST_ROOT / "coverage_observations")


def pytest_sessionfinish(session, exitstatus) -> None:
    """Release pooled SQLite handles, then remove this session's DB directory."""
    db_module = sys.modules.get("app.db")
    if db_module is not None:
        db_module.engine.dispose()
    _TEST_DB_DIR.cleanup()
