"""Pytest 引导：路径 + 测试库隔离。

关键：必须在任何 `app.*` 被导入前设置 DB_PATH 环境变量。
config.py 在 import 时读取 DB_PATH，db.py 据此构建 engine；
pytest 会先加载 conftest 再加载测试模块，因此此处设置可彻底隔离真实库。
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 让测试使用独立的临时 SQLite，绝不触碰 backend/dossier.db。
_TEST_DB = os.path.join(tempfile.gettempdir(), "dossier_test.db")
os.environ["DB_PATH"] = _TEST_DB

# 每次测试会话开始时清掉上一轮的临时库，保证干净状态。
try:
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
except OSError:
    pass
