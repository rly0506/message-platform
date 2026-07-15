"""Immutable, post-commit RM-055 Coverage observation evidence."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app import config
from app.db import engine
from app.services import coverage_snapshot


LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = "rm055-coverage-observation-v1"
SHANGHAI = ZoneInfo("Asia/Shanghai")
_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|authorization|credential|password|proxy|secret|token)", re.I)
_CREDENTIAL_URL = re.compile(r"://[^\s/@:]+:[^\s/@]+@")
_PROXY_VALUE = re.compile(r"(?i)(proxy\s*[=:]\s*)(\S+)")
_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(?P<key>api[_-]?key|authorization|credential|password|proxy|secret|token)\s*[=:]\s*(?:Bearer\s+)?\S+"
)
_ENV_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(?P<key>[a-z][a-z0-9_]*(?:key|token|secret|password|credential|proxy)[a-z0-9_]*)\s*=\s*(?:['\"])?[^\s'\"]+(?:['\"])?"
)
_QUOTED_AUTHORIZATION = re.compile(r"(?i)\b(?P<key>authorization)\s*:\s*['\"]?Bearer\s+[^\s'\"]+['\"]?")
_SNAPSHOT_KEYS = {
    "topic_id", "event_id", "sample", "independent_source_count", "source_distribution",
    "collector_distribution", "language_distribution", "country_distribution", "url_decoding",
    "source_registry", "fulltext",
}
_FULLTEXT_UNKNOWN = {"status": "unknown", "reason": "article_bodies_not_persisted"}


def begin_observation_run(
    *, root: Path | None = None, observed_at: datetime | None = None, run_id: str | None = None
) -> "CoverageObservationRun":
    """Create one evidence ledger for a single auto-refresh cycle.

    Creation errors are retained on the ledger instead of blocking the refresh
    transaction.  The caller must still call ``finalize`` so the invalid state is
    reported through normal logs.
    """
    return CoverageObservationRun(
        root=Path(root or config.COVERAGE_OBSERVATIONS_DIR),
        observed_at=_as_utc(observed_at or datetime.now(timezone.utc)),
        run_id=run_id or uuid.uuid4().hex,
    )


@dataclass
class CoverageObservationRun:
    root: Path
    observed_at: datetime
    run_id: str
    expected: set[int] = field(default_factory=set)
    captured: set[int] = field(default_factory=set)
    failed: set[int] = field(default_factory=set)
    skipped: set[int] = field(default_factory=set)
    observation_failed: set[int] = field(default_factory=set)
    capture_errors: dict[int, str] = field(default_factory=dict)
    topic_files: dict[int, dict[str, Any]] = field(default_factory=dict)
    init_error: str = ""
    run_dir: Path | None = None

    def __post_init__(self) -> None:
        self.observed_at = _as_utc(self.observed_at)
        try:
            run_dir = self.root / self.shanghai_date.isoformat() / self.run_id
            run_dir.mkdir(parents=True, exist_ok=False)
            self.run_dir = run_dir
        except FileExistsError:
            if run_dir.exists():
                raise
            self.init_error = "observation root unavailable: FileExistsError"
            LOGGER.error("RM-055 %s run_id=%s", self.init_error, self.run_id)
        except Exception as exc:
            self.init_error = f"observation root unavailable: {type(exc).__name__}: {exc}"
            LOGGER.error("RM-055 %s run_id=%s", self.init_error, self.run_id)

    @property
    def shanghai_date(self) -> date:
        return self.observed_at.astimezone(SHANGHAI).date()

    def record_failed(self, *, topic_id: int, error: str) -> None:
        self._claim_terminal(topic_id, "failed")
        self.failed.add(topic_id)
        self.capture_errors[topic_id] = _sanitize(error)

    def record_skipped(self, *, topic_id: int, reason: str) -> None:
        self._claim_terminal(topic_id, "skipped")
        self.skipped.add(topic_id)
        self.capture_errors[topic_id] = _sanitize(reason)

    def record_committed(self, *, topic_id: int, collection_result: dict[str, Any]) -> None:
        self._claim_terminal(topic_id, "expected")
        self.expected.add(topic_id)
        if self.init_error or self.run_dir is None:
            LOGGER.error(
                "RM-055 observation unfinalized after committed topic_id=%s run_id=%s: %s",
                topic_id,
                self.run_id,
                self.init_error,
            )
            return

        try:
            with Session(engine) as session:
                snapshot = coverage_snapshot.build_coverage_snapshot(session, topic_id, event_id=None)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "run_id": self.run_id,
                "captured_at_utc": self.observed_at.isoformat(),
                "shanghai_date": self.shanghai_date.isoformat(),
                "topic_id": topic_id,
                "provenance": {"trigger": "_refresh_due_news", "commit": "successful"},
                "collection_result": _sanitize(collection_result),
                "coverage_snapshot": snapshot,
            }
            payload_bytes = _canonical_bytes(payload)
            topic_path = self.run_dir / f"topic-{topic_id}.json"
            _write_new_file(topic_path, payload_bytes)
            self.captured.add(topic_id)
            self.topic_files[topic_id] = {
                "topic_id": topic_id,
                "path": topic_path.name,
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
                "byte_length": len(payload_bytes),
            }
        except Exception as exc:
            self.observation_failed.add(topic_id)
            self.capture_errors[topic_id] = f"{type(exc).__name__}: {_sanitize(str(exc))}"
            LOGGER.error(
                "RM-055 observation capture failed after committed topic_id=%s run_id=%s: %s",
                topic_id,
                self.run_id,
                self.capture_errors[topic_id],
            )

    def finalize(self) -> dict[str, str]:
        """Seal the manifest last. A failure is explicitly an unfinalized run."""
        if self.init_error or self.run_dir is None:
            return {"status": "unfinalized", "error": self.init_error}
        if not self._has_valid_terminal_sets():
            error = "terminal topic outcome sets are not disjoint"
            LOGGER.error("RM-055 run_id=%s unfinalized: %s", self.run_id, error)
            return {"status": "unfinalized", "error": error}

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "captured_at_utc": self.observed_at.isoformat(),
            "shanghai_date": self.shanghai_date.isoformat(),
            "status": "finalized",
            "expected": sorted(self.expected),
            "captured": sorted(self.captured),
            "failed": sorted(self.failed),
            "skipped": sorted(self.skipped),
            "observation_failed": sorted(self.observation_failed),
            "capture_errors": {str(key): self.capture_errors[key] for key in sorted(self.capture_errors)},
            "topic_files": [self.topic_files[key] for key in sorted(self.topic_files)],
        }
        try:
            _write_new_file(self.run_dir / "manifest.json", _canonical_bytes(manifest))
        except Exception as exc:
            error = f"manifest finalization failed: {type(exc).__name__}: {exc}"
            LOGGER.error(
                "RM-055 %s run_id=%s expected=%s",
                error,
                self.run_id,
                sorted(self.expected),
            )
            return {"status": "unfinalized", "error": error}
        return {"status": "finalized", "manifest_path": str(self.run_dir / "manifest.json")}

    def _claim_terminal(self, topic_id: int, outcome: str) -> None:
        all_ids = self.expected | self.failed | self.skipped | self.observation_failed
        if topic_id in all_ids:
            raise ValueError(f"topic_id={topic_id} already has an observation outcome; cannot mark {outcome}")

    def _has_valid_terminal_sets(self) -> bool:
        terminal_sets = (self.captured, self.observation_failed, self.failed, self.skipped)
        if any(left & right for index, left in enumerate(terminal_sets) for right in terminal_sets[index + 1:]):
            return False
        return self.expected == self.captured | self.observation_failed and not (self.failed & self.expected) and not (
            self.skipped & (self.expected | self.failed)
        )


def verify_observations(*, root: Path, start_date: date, end_date: date) -> dict[str, Any]:
    """Validate retained evidence only; never opens SQLite or repairs files."""
    errors: list[str] = []
    valid_runs: list[dict[str, Any]] = []
    if end_date < start_date:
        return {"valid": False, "errors": ["end date precedes start date"], "runs": []}
    if not root.exists() or not root.is_dir():
        return {"valid": False, "errors": [f"observation root is unavailable: {root}"], "runs": []}
    try:
        date_dirs = sorted(root.iterdir())
    except Exception as exc:
        return {"valid": False, "errors": [f"observation root is unreadable: {type(exc).__name__}"], "runs": []}
    for date_dir in date_dirs:
        if not date_dir.is_dir():
            errors.append(f"unexpected root entry: {date_dir.name}")
            continue
        try:
            run_date = date.fromisoformat(date_dir.name)
        except ValueError:
            errors.append(f"invalid observation date directory: {date_dir.name}")
            continue
        if not start_date <= run_date <= end_date:
            continue
        try:
            children = sorted(date_dir.iterdir())
        except Exception as exc:
            errors.append(f"unreadable observation date directory {date_dir.name}: {type(exc).__name__}")
            continue
        if not children:
            errors.append(f"empty observation date directory: {date_dir.name}")
        for run_dir in children:
            if not run_dir.is_dir():
                errors.append(f"unexpected date entry: {date_dir.name}/{run_dir.name}")
                continue
            run, run_errors = _verify_run(run_dir=run_dir, run_date=run_date)
            errors.extend(run_errors)
            if run is not None:
                valid_runs.append(run)
    return {
        "valid": not errors,
        "errors": errors,
        "runs": valid_runs,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def _verify_run(*, run_dir: Path, run_date: date) -> tuple[dict[str, Any] | None, list[str]]:
    prefix = str(run_dir)
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return None, [f"unfinalized run (missing manifest): {prefix}"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"unreadable manifest {prefix}: {type(exc).__name__}"]
    if not isinstance(manifest, dict):
        return None, [f"manifest is not an object: {prefix}"]
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("status") != "finalized"
        or manifest.get("run_id") != run_dir.name
        or manifest.get("shanghai_date") != run_date.isoformat()
        or not _is_utc_timestamp(manifest.get("captured_at_utc"))
        or not isinstance(manifest.get("capture_errors"), dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in manifest["capture_errors"].items())
    ):
        return None, [f"invalid manifest identity or finalization marker: {prefix}"]

    named_sets: dict[str, set[int]] = {}
    errors: list[str] = []
    for name in ("expected", "captured", "failed", "skipped", "observation_failed"):
        values = manifest.get(name)
        if not isinstance(values, list) or any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            errors.append(f"invalid {name} set: {prefix}")
            continue
        named_sets[name] = set(values)
        if len(values) != len(named_sets[name]):
            errors.append(f"duplicate topic in {name}: {prefix}")
    if errors:
        return None, errors
    expected, captured = named_sets["expected"], named_sets["captured"]
    failed, skipped = named_sets["failed"], named_sets["skipped"]
    observation_failed = named_sets["observation_failed"]
    if expected != captured | observation_failed:
        errors.append(f"expected set does not match terminal capture sets: {prefix}")
    terminal_sets = (captured, observation_failed, failed, skipped)
    if any(left & right for index, left in enumerate(terminal_sets) for right in terminal_sets[index + 1:]):
        errors.append(f"terminal topic sets overlap: {prefix}")
    if errors:
        return None, errors

    entries = manifest.get("topic_files")
    if not isinstance(entries, list) or len(entries) != len(captured):
        return None, [f"topic file membership does not match captured set: {prefix}"]
    entry_by_topic: dict[int, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            return None, [f"invalid topic file entry: {prefix}"]
        topic_id = entry.get("topic_id")
        if not isinstance(topic_id, int) or isinstance(topic_id, bool) or topic_id in entry_by_topic:
            return None, [f"duplicate or invalid topic file entry: {prefix}"]
        entry_by_topic[topic_id] = entry
    if set(entry_by_topic) != captured:
        return None, [f"topic file membership does not match captured set: {prefix}"]
    expected_names = {"manifest.json"}
    for topic_id, entry in entry_by_topic.items():
        path = entry.get("path")
        if (
            path != f"topic-{topic_id}.json"
            or not isinstance(entry.get("sha256"), str)
            or not isinstance(entry.get("byte_length"), int)
            or isinstance(entry.get("byte_length"), bool)
        ):
            return None, [f"invalid topic file path: {prefix}"]
        expected_names.add(path)
        topic_path = run_dir / path
        if not topic_path.is_file():
            return None, [f"missing topic file: {prefix}/{path}"]
        try:
            payload = topic_path.read_bytes()
        except Exception as exc:
            return None, [f"unreadable topic file {prefix}/{path}: {type(exc).__name__}"]
        if entry.get("byte_length") != len(payload) or entry.get("sha256") != hashlib.sha256(payload).hexdigest():
            return None, [f"checksum or byte length mismatch: {prefix}/{path}"]
        try:
            topic = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            return None, [f"unreadable topic file {prefix}/{path}: {type(exc).__name__}"]
        if not isinstance(topic, dict) or (
            topic.get("schema_version") != SCHEMA_VERSION
            or topic.get("run_id") != run_dir.name
            or topic.get("shanghai_date") != run_date.isoformat()
            or topic.get("topic_id") != topic_id
            or topic.get("provenance") != {"trigger": "_refresh_due_news", "commit": "successful"}
            or not _is_utc_timestamp(topic.get("captured_at_utc"))
            or not isinstance(topic.get("collection_result"), dict)
            or not isinstance(topic["collection_result"].get("requests"), list)
            or not isinstance(topic["collection_result"].get("errors"), list)
            or not _is_valid_coverage_snapshot(topic.get("coverage_snapshot"), topic_id)
        ):
            return None, [f"invalid topic payload identity: {prefix}/{path}"]
    try:
        actual_names = {item.name for item in run_dir.iterdir()}
    except Exception as exc:
        return None, [f"unreadable run directory {prefix}: {type(exc).__name__}"]
    if actual_names != expected_names:
        return None, [f"unlisted, partial, or temporary file in run: {prefix}"]
    return {
        "date": run_date.isoformat(),
        "run_id": run_dir.name,
        "manifest": manifest,
    }, []


def _write_new_file(path: Path, payload: bytes) -> None:
    """Flush a sibling temp file then atomically install it without replacement."""
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _is_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _is_valid_coverage_snapshot(value: Any, topic_id: int) -> bool:
    if not isinstance(value, dict) or set(value) != _SNAPSHOT_KEYS:
        return False
    sample = value.get("sample")
    decoding = value.get("url_decoding")
    registry = value.get("source_registry")
    fulltext = value.get("fulltext")
    if (
        not _is_non_bool_int(value.get("topic_id"))
        or value["topic_id"] != topic_id
        or value.get("event_id") is not None
        or not isinstance(value.get("independent_source_count"), int)
        or isinstance(value.get("independent_source_count"), bool)
        or not isinstance(sample, dict)
        or set(sample) != {"basis", "article_count", "article_ids", "note"}
        or not isinstance(sample.get("basis"), str)
        or not _is_non_bool_int(sample.get("article_count"))
        or not _is_int_list(sample.get("article_ids"))
        or sample["article_count"] != len(sample["article_ids"])
        or not isinstance(sample.get("note"), str)
        or not all(_is_bucket_list(value.get(name)) for name in (
            "source_distribution", "collector_distribution", "language_distribution", "country_distribution"
        ))
        or not isinstance(decoding, dict)
        or set(decoding) != {"eligible_count", "decoded_count", "rate", "decoded_article_ids", "not_decoded_article_ids"}
        or not _is_non_bool_int(decoding.get("eligible_count"))
        or not _is_non_bool_int(decoding.get("decoded_count"))
        or decoding["decoded_count"] > decoding["eligible_count"]
        or not (decoding.get("rate") is None or isinstance(decoding.get("rate"), float))
        or not _is_int_list(decoding.get("decoded_article_ids"))
        or not _is_int_list(decoding.get("not_decoded_article_ids"))
        or not isinstance(registry, dict)
        or set(registry) != {"type_distribution", "tier_distribution", "unclassified_article_ids"}
        or not _is_bucket_list(registry.get("type_distribution"))
        or not _is_bucket_list(registry.get("tier_distribution"))
        or not _is_int_list(registry.get("unclassified_article_ids"))
        or fulltext != _FULLTEXT_UNKNOWN
    ):
        return False
    return True


def _is_non_bool_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_int_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_non_bool_int(item) for item in value)


def _is_bucket_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict)
        and set(item) == {"key", "count", "article_ids"}
        and isinstance(item.get("key"), str)
        and _is_non_bool_int(item.get("count"))
        and _is_int_list(item.get("article_ids"))
        and item["count"] == len(item["article_ids"])
        for item in value
    )


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): "[redacted]" if _SENSITIVE_KEY.search(str(key)) else _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        value = _CREDENTIAL_URL.sub("://[redacted]@", value)
        value = _PROXY_VALUE.sub(r"\1[redacted]", value)
        value = _QUOTED_AUTHORIZATION.sub(lambda match: f"{match.group('key')}=[redacted]", value)
        value = _SENSITIVE_VALUE.sub(lambda match: f"{match.group('key')}=[redacted]", value)
        value = _ENV_SENSITIVE_VALUE.sub(lambda match: f"{match.group('key')}=[redacted]", value)
        return value
    return value
