"""Load local analysis rule configuration from JSON."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "rule_config.json"


@lru_cache(maxsize=1)
def load_rule_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    _validate(data)
    return data


def _validate(data: dict[str, Any]) -> None:
    required = {
        "stopwords",
        "media_source_tiers",
        "media_tier_labels",
        "cjk_stop_terms",
        "entity_stopwords",
        "authority_sources",
        "entity_aliases",
        "entity_kind_labels",
        "entity_kind_order",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"rule_config.json missing keys: {', '.join(missing)}")

    for name in ("stopwords", "cjk_stop_terms", "entity_stopwords", "authority_sources", "entity_kind_order"):
        if not isinstance(data[name], list):
            raise ValueError(f"rule_config.json key {name} must be a list")

    for name in ("media_source_tiers", "media_tier_labels", "entity_aliases", "entity_kind_labels"):
        if not isinstance(data[name], dict):
            raise ValueError(f"rule_config.json key {name} must be an object")

    for term, spec in data["entity_aliases"].items():
        if not isinstance(term, str) or not isinstance(spec, dict):
            raise ValueError("entity_aliases entries must be objects")
        if not isinstance(spec.get("kind"), str) or not isinstance(spec.get("aliases"), list):
            raise ValueError(f"entity_aliases entry {term} must include kind and aliases")


def string_set(name: str) -> set[str]:
    return set(str(item) for item in load_rule_config()[name])


def string_dict(name: str) -> dict[str, str]:
    return {str(key): str(value) for key, value in load_rule_config()[name].items()}


def string_tuple_dict(name: str) -> dict[str, tuple[str, ...]]:
    return {
        str(key): tuple(str(item) for item in value)
        for key, value in load_rule_config()[name].items()
    }


def entity_aliases() -> dict[str, tuple[str, tuple[str, ...]]]:
    return {
        str(term): (str(spec["kind"]), tuple(str(alias) for alias in spec["aliases"]))
        for term, spec in load_rule_config()["entity_aliases"].items()
    }


def string_tuple(name: str) -> tuple[str, ...]:
    return tuple(str(item) for item in load_rule_config()[name])
