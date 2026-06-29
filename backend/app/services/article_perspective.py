"""On-demand sentence perspective for one article."""
from __future__ import annotations

from typing import Any

from app import config, llm
from app.db import Article
from app.pipeline import fulltext

_SYSTEM = "你是新闻陪读助手。只输出 JSON 数组，不输出 markdown。"


def analyze_article(article: Article) -> dict[str, Any]:
    extracted = fulltext.extract_url(article.url)
    if extracted.ok and extracted.full_text.strip():
        mode = "fulltext"
        source_text = extracted.full_text
        source_error = ""
    else:
        mode = "summary"
        source_text = "\n".join(part for part in [article.title_zh or article.title, article.snippet_zh or article.snippet] if part)
        source_error = extracted.error

    if not source_text.strip():
        return {"article_id": article.id, "mode": mode, "items": [], "error": "empty article text", "source_error": source_error}

    try:
        raw = llm.chat(config.HAIKU_MODEL, _prompt(source_text[:3500]), max_tokens=1200, system=_SYSTEM)
        data = llm.extract_json(raw)
    except Exception as exc:
        return {"article_id": article.id, "mode": mode, "items": [], "error": str(exc), "source_error": source_error}

    return {
        "article_id": article.id,
        "mode": mode,
        "items": _items(data),
        "error": "",
        "source_error": source_error,
    }


def _prompt(text: str) -> str:
    return f"""请逐句找出这篇报道里真正值得读的句子。

只标两类:
- substance: 可核查/可证伪的事实、数字、时间、地点、具名说法
- emotion: 情绪化、带节奏、口号化、暗示但不可核查的说法

每类最多 5 句。中性铺垫不要输出。

返回 JSON 数组，每项字段:
- sentence: 原句或尽量贴近原句的短句
- kind: substance 或 emotion
- reason: 中文说明，20 字以内

文本:
{text}
"""


def _items(data: object) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        sentence = str(item.get("sentence") or "").strip()
        if kind not in {"substance", "emotion"} or not sentence:
            continue
        out.append({
            "sentence": sentence[:500],
            "kind": kind,
            "reason": str(item.get("reason") or "")[:80],
        })
    return out[:10]
