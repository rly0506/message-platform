"""Shared term matching for local rule-based signals."""
from __future__ import annotations

import re

CJK_RE = re.compile(r"[\u3400-\u9fff]")


def term_hit(term: str, text: str) -> bool:
    needle = str(term or "").strip().lower()
    haystack = str(text or "").lower()
    if not needle or not haystack:
        return False
    if CJK_RE.search(needle) or not needle.isascii() or not needle.isalnum():
        return needle in haystack
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None
