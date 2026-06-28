"""全局配置：从 .env 读取，提供默认值。"""
import os

from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)

# override=True: 让 backend/.env 成为权威配置，避免被残留的系统环境变量
# (如旧的 ANTHROPIC_BASE_URL) 劫持，导致连错节点 / 模型名不匹配。
load_dotenv(os.path.join(_BACKEND, ".env"), override=True)

# 数据库
DB_PATH = os.getenv("DB_PATH") or os.path.join(_BACKEND, "dossier.db")

# LLM (Phase 1 步骤 4-5 才会用到)
# LLM_* 是新的通用配置；ANTHROPIC_* 保留兼容旧 .env。
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("ANTHROPIC_BASE_URL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")  # 自定义节点, 空则用官方
HAIKU_MODEL = os.getenv("HAIKU_MODEL", "claude-haiku-4-5-20251001")
SYNTH_MODEL = os.getenv("SYNTH_MODEL", "claude-sonnet-4-6")

# OpenAlex academic layer
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")
OPENCLI_COMMAND = os.getenv("OPENCLI_COMMAND", "opencli")

# 采集默认参数
GDELT_MAX_RECORDS = 250          # GDELT 单次上限
RSS_USER_AGENT = "Mozilla/5.0 (compatible; DossierBot/0.1; personal-research)"

# Google News RSS 的多语种 locale: (hl, gl, ceid)
# 用于跨语言围绕主题做检索式 RSS。
GNEWS_LOCALES = [
    ("en-US", "US", "US:en"),     # 英语
    ("zh-CN", "CN", "CN:zh-Hans"),  # 简体中文
]
