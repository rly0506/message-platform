"""全文抓取 —— 从标题级分析迈向正文级。

现状: 分析只基于标题+摘要 (RSS/News 给的)。这是所有下游分析的天花板:
事实核查、矛盾检测、实体抽取都受限于"只看了标题"。抓正文能整体抬高质量。

版权原则 (见 docs/future-directions.md): 项目只存"标题+链接", 不囤全文。
因此本模块: **临时抓取正文供即时分析, 默认只返回摘录 (excerpt), 由调用方决定是否落库,
落库也应只存摘录而非全文。** 不做整站镜像、不绕反爬。

依赖 trafilatura (业界正文抽取库)。不可用时优雅降级: 返回 None, 不崩。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# 单篇抓取的摘录上限 (字符)。只存摘录, 不囤全文。
EXCERPT_CHARS = 1500
_FETCH_TIMEOUT = 20


@dataclass
class Extracted:
    """一篇正文抽取结果。full_text 仅供即时分析, 落库请只用 excerpt。"""
    url: str
    title: str = ""
    excerpt: str = ""           # 截断摘录, 安全落库
    full_text: str = ""         # 完整正文, 仅即时分析用, 不建议落库
    word_count: int = 0
    ok: bool = False
    error: str = ""


def _trafilatura():
    """惰性导入 trafilatura; 不可用返回 None (优雅降级)。"""
    try:
        import trafilatura
        return trafilatura
    except Exception:
        return None


def extract_url(url: str) -> Extracted:
    """抓取单个 URL 的正文。失败/不可用 -> ok=False, 不抛异常。"""
    if not url:
        return Extracted(url=url, ok=False, error="empty url")
    traf = _trafilatura()
    if traf is None:
        return Extracted(url=url, ok=False, error="trafilatura unavailable")
    try:
        downloaded = traf.fetch_url(url)
        if not downloaded:
            return Extracted(url=url, ok=False, error="fetch failed")
        text = traf.extract(downloaded, include_comments=False, include_tables=False) or ""
        meta_title = ""
        try:
            md = traf.extract_metadata(downloaded)
            meta_title = (getattr(md, "title", "") or "") if md else ""
        except Exception:
            meta_title = ""
        text = text.strip()
        return Extracted(
            url=url,
            title=meta_title,
            excerpt=text[:EXCERPT_CHARS],
            full_text=text,
            word_count=len(text.split()),
            ok=bool(text),
            error="" if text else "empty extraction",
        )
    except Exception as exc:
        return Extracted(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")


def extract_from_html(html: str, url: str = "") -> Extracted:
    """从已有 HTML 字符串抽取正文 (供测试 / 已下载内容复用, 不发网络请求)。"""
    traf = _trafilatura()
    if traf is None:
        return Extracted(url=url, ok=False, error="trafilatura unavailable")
    try:
        text = (traf.extract(html, include_comments=False, include_tables=False) or "").strip()
        return Extracted(
            url=url,
            excerpt=text[:EXCERPT_CHARS],
            full_text=text,
            word_count=len(text.split()),
            ok=bool(text),
            error="" if text else "empty extraction",
        )
    except Exception as exc:
        return Extracted(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")
