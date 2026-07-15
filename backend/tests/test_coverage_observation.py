"""RM-055 immutable filesystem evidence tests."""
from __future__ import annotations

import json
import hashlib
from datetime import date, datetime, timezone

import pytest

from app.services import coverage_observation


@pytest.fixture
def captured_at() -> datetime:
    return datetime(2026, 7, 15, 16, 30, tzinfo=timezone.utc)


def _snapshot(topic_id: int) -> dict[str, object]:
    return {
        "topic_id": topic_id,
        "event_id": None,
        "sample": {"basis": "persisted_topic_articles", "article_count": 2, "article_ids": [10, 11], "note": "persisted metadata"},
        "independent_source_count": 1,
        "source_distribution": [],
        "collector_distribution": [],
        "language_distribution": [],
        "country_distribution": [],
        "url_decoding": {"eligible_count": 0, "decoded_count": 0, "rate": None, "decoded_article_ids": [], "not_decoded_article_ids": []},
        "fulltext": {"status": "unknown", "reason": "article_bodies_not_persisted"},
        "source_registry": {"type_distribution": [], "tier_distribution": [], "unclassified_article_ids": [11]},
    }


def test_finalized_run_writes_immutable_topic_evidence_after_fresh_session_closes(
    monkeypatch, tmp_path, captured_at
):
    events = []

    class FreshSession:
        def __init__(self, _engine):
            events.append("open")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            events.append("closed")

    original_write = coverage_observation._write_new_file

    def checked_write(path, payload):
        assert events[-1] == "closed"
        return original_write(path, payload)

    monkeypatch.setattr(coverage_observation, "Session", FreshSession)
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    monkeypatch.setattr(coverage_observation, "_write_new_file", checked_write)

    recorder = coverage_observation.begin_observation_run(
        root=tmp_path, observed_at=captured_at, run_id="run-a"
    )
    recorder.record_committed(
        topic_id=7,
        collection_result={
            "requests": [{"source": "wire"}],
            "errors": [
                "proxy=http://user:secret@example.test api_key=abc123 "
                "Authorization: Bearer xyz token=opaque OPENAI_API_KEY=sk-live "
                "AWS_SECRET_ACCESS_KEY=aws-value Authorization: \"Bearer quoted-token\""
            ],
        },
    )
    outcome = recorder.finalize()

    assert outcome["status"] == "finalized"
    run_dir = tmp_path / "2026-07-16" / "run-a"
    assert run_dir.is_dir()
    topic_path = run_dir / "topic-7.json"
    manifest_path = run_dir / "manifest.json"
    assert topic_path.exists() and manifest_path.exists()
    assert not list(run_dir.glob("*.tmp"))

    topic = json.loads(topic_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert topic["schema_version"] == coverage_observation.SCHEMA_VERSION
    assert topic["shanghai_date"] == "2026-07-16"
    assert topic["captured_at_utc"] == captured_at.isoformat()
    assert topic["provenance"] == {"commit": "successful", "trigger": "_refresh_due_news"}
    assert topic["collection_result"]["requests"] == [{"source": "wire"}]
    assert all(
        secret not in topic["collection_result"]["errors"][0]
        for secret in ("user:secret@", "abc123", "xyz", "opaque", "sk-live", "aws-value", "quoted-token")
    )
    assert manifest["status"] == "finalized"
    assert manifest["expected"] == [7]
    assert manifest["captured"] == [7]
    assert manifest["failed"] == []
    assert manifest["skipped"] == []
    assert manifest["observation_failed"] == []
    assert coverage_observation.verify_observations(
        root=tmp_path, start_date=date(2026, 7, 16), end_date=date(2026, 7, 16)
    )["valid"] is True


def test_capture_failure_is_manifest_visible_without_erasing_committed_expectation(
    monkeypatch, tmp_path, captured_at
):
    monkeypatch.setattr(
        coverage_observation.coverage_snapshot,
        "build_coverage_snapshot",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("snapshot unavailable")),
    )
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="run-failed")

    recorder.record_committed(topic_id=8, collection_result={"requests": [], "errors": []})
    outcome = recorder.finalize()

    manifest = json.loads((tmp_path / "2026-07-16" / "run-failed" / "manifest.json").read_text(encoding="utf-8"))
    assert outcome["status"] == "finalized"
    assert manifest["expected"] == [8]
    assert manifest["captured"] == []
    assert manifest["observation_failed"] == [8]
    assert manifest["capture_errors"]["8"].startswith("RuntimeError")


def test_failed_and_skipped_topics_are_disjoint_from_committed_observations(monkeypatch, tmp_path, captured_at):
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="run-sets")

    recorder.record_failed(topic_id=1, error="collect failed")
    recorder.record_skipped(topic_id=2, reason="topic lock held")
    recorder.record_committed(topic_id=3, collection_result={"requests": [], "errors": []})
    recorder.finalize()

    manifest = json.loads((tmp_path / "2026-07-16" / "run-sets" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["expected"] == [3]
    assert manifest["captured"] == [3]
    assert manifest["failed"] == [1]
    assert manifest["skipped"] == [2]
    assert manifest["observation_failed"] == []


def test_existing_run_directory_is_never_reused(tmp_path, captured_at):
    coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="once")

    with pytest.raises(FileExistsError):
        coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="once")


def test_verifier_rejects_corrupt_topic_file(monkeypatch, tmp_path, captured_at):
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="corrupt")
    recorder.record_committed(topic_id=9, collection_result={"requests": [], "errors": []})
    recorder.finalize()
    (tmp_path / "2026-07-16" / "corrupt" / "topic-9.json").write_text("{}", encoding="utf-8")

    result = coverage_observation.verify_observations(
        root=tmp_path, start_date=date(2026, 7, 16), end_date=date(2026, 7, 16)
    )

    assert result["valid"] is False
    assert any("checksum" in error for error in result["errors"])


def test_verifier_rejects_duplicate_topic_file_entries(monkeypatch, tmp_path, captured_at):
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="duplicate")
    recorder.record_committed(topic_id=11, collection_result={"requests": [], "errors": []})
    recorder.finalize()
    manifest_path = tmp_path / "2026-07-16" / "duplicate" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["topic_files"].append(dict(manifest["topic_files"][0]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = coverage_observation.verify_observations(
        root=tmp_path, start_date=date(2026, 7, 16), end_date=date(2026, 7, 16)
    )

    assert result["valid"] is False
    assert any("topic file" in error for error in result["errors"])


def test_verifier_rejects_a_snapshot_owned_by_another_topic(monkeypatch, tmp_path, captured_at):
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="wrong-owner")
    recorder.record_committed(topic_id=12, collection_result={"requests": [], "errors": []})
    recorder.finalize()
    run_dir = tmp_path / "2026-07-16" / "wrong-owner"
    topic_path = run_dir / "topic-12.json"
    payload = json.loads(topic_path.read_text(encoding="utf-8"))
    payload["coverage_snapshot"]["topic_id"] = 999
    topic_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    topic_path.write_bytes(topic_bytes)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["topic_files"][0]["sha256"] = hashlib.sha256(topic_bytes).hexdigest()
    manifest["topic_files"][0]["byte_length"] = len(topic_bytes)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = coverage_observation.verify_observations(
        root=tmp_path, start_date=date(2026, 7, 16), end_date=date(2026, 7, 16)
    )

    assert result["valid"] is False
    assert any("payload" in error for error in result["errors"])


def test_verifier_rejects_boolean_snapshot_topic_id(monkeypatch, tmp_path, captured_at):
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="boolean-owner")
    recorder.record_committed(topic_id=1, collection_result={"requests": [], "errors": []})
    recorder.finalize()
    run_dir = tmp_path / "2026-07-16" / "boolean-owner"
    topic_path = run_dir / "topic-1.json"
    payload = json.loads(topic_path.read_text(encoding="utf-8"))
    payload["coverage_snapshot"]["topic_id"] = True
    topic_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    topic_path.write_bytes(topic_bytes)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["topic_files"][0]["sha256"] = hashlib.sha256(topic_bytes).hexdigest()
    manifest["topic_files"][0]["byte_length"] = len(topic_bytes)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = coverage_observation.verify_observations(
        root=tmp_path, start_date=date(2026, 7, 16), end_date=date(2026, 7, 16)
    )

    assert result["valid"] is False


def test_verifier_rejects_tampered_fulltext_availability(monkeypatch, tmp_path, captured_at):
    monkeypatch.setattr(coverage_observation.coverage_snapshot, "build_coverage_snapshot", lambda _s, topic_id, event_id=None: _snapshot(topic_id))
    recorder = coverage_observation.begin_observation_run(root=tmp_path, observed_at=captured_at, run_id="tampered-fulltext")
    recorder.record_committed(topic_id=13, collection_result={"requests": [], "errors": []})
    recorder.finalize()
    run_dir = tmp_path / "2026-07-16" / "tampered-fulltext"
    topic_path = run_dir / "topic-13.json"
    payload = json.loads(topic_path.read_text(encoding="utf-8"))
    payload["coverage_snapshot"]["fulltext"] = {"status": "available", "reason": "tampered"}
    topic_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    topic_path.write_bytes(topic_bytes)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["topic_files"][0]["sha256"] = hashlib.sha256(topic_bytes).hexdigest()
    manifest["topic_files"][0]["byte_length"] = len(topic_bytes)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = coverage_observation.verify_observations(
        root=tmp_path, start_date=date(2026, 7, 16), end_date=date(2026, 7, 16)
    )

    assert result["valid"] is False


def test_unavailable_root_is_explicitly_unfinalized(tmp_path, captured_at):
    root_file = tmp_path / "not-a-directory"
    root_file.write_text("x", encoding="utf-8")

    recorder = coverage_observation.begin_observation_run(root=root_file, observed_at=captured_at, run_id="blocked")
    recorder.record_committed(topic_id=10, collection_result={"requests": [], "errors": []})

    outcome = recorder.finalize()

    assert outcome["status"] == "unfinalized"
    assert "root" in outcome["error"]
