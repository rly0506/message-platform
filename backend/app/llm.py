"""LLM API 封装 + 稳健的 JSON 解析。

支持 Anthropic-compatible 与 OpenAI-compatible API 网关。
"""
from __future__ import annotations

import json
import re
from typing import Optional

import httpx
from anthropic import Anthropic

from app import config

_client: Optional[Anthropic] = None


def client() -> Anthropic:
    global _client
    if _client is None:
        if not config.LLM_API_KEY:
            raise RuntimeError("未配置 LLM_API_KEY / ANTHROPIC_API_KEY (请填 backend/.env)")
        kwargs = {"api_key": config.LLM_API_KEY}
        if config.LLM_BASE_URL:
            kwargs["base_url"] = config.LLM_BASE_URL
        _client = Anthropic(**kwargs)
    return _client


def chat(model: str, prompt: str, max_tokens: int = 2048, system: str = "") -> str:
    """单轮对话，返回纯文本。

    使用流式 (streaming): 长生成经代理/网关时，非流式请求常因空闲超时返回空响应，
    流式保持连接存活可避免该问题。
    """
    if _provider() == "openai":
        return _openai_chat(model, prompt, max_tokens=max_tokens, system=system)

    text_parts: list[str] = []
    with client().messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system or "你是严谨的国际新闻分析助手，输出务必客观、可核查。",
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            text_parts.append(chunk)
    return "".join(text_parts)


def _provider() -> str:
    if config.LLM_PROVIDER in {"anthropic", "openai"}:
        return config.LLM_PROVIDER
    if config.LLM_BASE_URL and "ai-pixel.online" in config.LLM_BASE_URL:
        return "openai"
    return "anthropic"


def _openai_chat(model: str, prompt: str, max_tokens: int = 2048, system: str = "") -> str:
    if not config.LLM_API_KEY:
        raise RuntimeError("未配置 LLM_API_KEY / ANTHROPIC_API_KEY (请填 backend/.env)")
    base_url = (config.LLM_BASE_URL or "https://api.openai.com").rstrip("/")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system or "你是严谨的国际新闻分析助手，输出务必客观、可核查。",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=90) as http:
        response = http.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"LLM 返回空 choices: {str(data)[:200]}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "")


def extract_json(text: str):
    """从模型输出中稳健提取 JSON (容忍 ```json 围栏和前后噪声)。"""
    text = text.strip()
    # 去掉 markdown 围栏
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 兜底: 截取第一个 [ ... ] 或 { ... }
    for open_c, close_c in (("[", "]"), ("{", "}")):
        i, j = text.find(open_c), text.rfind(close_c)
        if i != -1 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except json.JSONDecodeError:
                continue
    # 最终兜底: json-repair 修复 (未转义引号/截断/多余逗号等 LLM 常见问题)
    try:
        from json_repair import repair_json
        repaired = repair_json(text, return_objects=True)
        if repaired not in ("", None, [], {}):
            return repaired
    except Exception:
        pass
    raise ValueError(f"无法解析为 JSON: {text[:200]}...")
