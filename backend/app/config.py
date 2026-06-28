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

# Reddit 官方 API (无浏览器路线)。配齐则 Reddit 走官方 API, 否则回退 OpenCLI(需 Chrome+登录)。
# 在 https://www.reddit.com/prefs/apps 注册 "script" 类型应用拿 client_id/secret。
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "dossier-tool/0.1 (personal research)")

# 采集默认参数
GDELT_MAX_RECORDS = 250          # GDELT 单次上限
RSS_USER_AGENT = "Mozilla/5.0 (compatible; DossierBot/0.1; personal-research)"

# RSS/gnews 抓取的网络健壮性参数。
# 快速失败: 连不上的源 (如国内直连不上的 Google News) 几秒内失败, 不卡死整批采集。
# 代理: 两条路都支持 ——
#   1) 显式 RSS_PROXY (推荐): 如 socks5://127.0.0.1:10808 (v2rayN) 或 http://127.0.0.1:7890 (Clash)。
#      SOCKS5 需 httpx[socks] (已装 socksio)。
#   2) trust_env=True 自动读 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY 环境变量 (RSS_PROXY 留空时回退到此)。
#   本机有 VPN 时设上, gnews 即可经代理出去 (Google 从国内可达)。
RSS_FETCH_TIMEOUT = float(os.getenv("RSS_FETCH_TIMEOUT", "12"))  # 单次连接/读取超时 (秒)
RSS_FETCH_RETRIES = int(os.getenv("RSS_FETCH_RETRIES", "1"))     # 失败后额外重试次数 (轻重试)
RSS_PROXY = os.getenv("RSS_PROXY", "").strip()                   # 显式代理 URL, 空则回退到环境变量

# Google News RSS 的多语种 locale: (hl, gl, ceid)
# 用于跨语言围绕主题做检索式 RSS。
GNEWS_LOCALES = [
    ("en-US", "US", "US:en"),     # 英语
    ("zh-CN", "CN", "CN:zh-Hans"),  # 简体中文
]
