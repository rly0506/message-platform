"""RM-055 command-line contracts for the coverage observation pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient
from typer.testing import CliRunner

import cli as dossier_cli
from app import api
from app.services import coverage_observation


EXPECTED_AUTO_REFRESH_KEYS = {
    "enabled",
    "running",
    "last_started_at",
    "last_finished_at",
    "last_error",
    "news_refreshed",
    "news_errors",
    "frontier_refreshed",
    "skipped_active",
}


def _valid_refresh_result() -> dict[str, object]:
    return {
        "enabled": True,
        "running": False,
        "last_started_at": "2026-07-15T00:00:00",
        "last_finished_at": "2026-07-15T00:01:00",
        "last_error": "",
        "news_refreshed": 1,
        "news_errors": [],
        "frontier_refreshed": False,
        "skipped_active": 0,
    }


class _Response:
    def __init__(self, status: int, payload: object):
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _RawResponse(_Response):
    def __init__(self, status: int, raw: bytes):
        self.status = status
        self._raw = raw

    def read(self) -> bytes:
        return self._raw


def test_refresh_once_posts_once_after_valid_health_without_local_fallback(monkeypatch):
    calls = []

    def fake_urlopen(request, *, timeout):
        calls.append((request, timeout))
        if len(calls) == 1:
            return _Response(200, {"status": "ok"})
        return _Response(200, _valid_refresh_result())

    monkeypatch.setattr(dossier_cli, "urlopen", fake_urlopen)
    monkeypatch.setattr(dossier_cli, "init_db", lambda: (_ for _ in ()).throw(AssertionError("no local DB")))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 0
    assert len(calls) == 2
    assert calls[0][0] == dossier_cli.HEALTH_URL
    assert calls[1][0].full_url == dossier_cli.REFRESH_URL
    assert calls[1][0].method == "POST"
    assert json.loads(result.stdout) == _valid_refresh_result()


def test_refresh_once_accepts_a_valid_health_object_with_additional_fields(monkeypatch):
    calls = []

    def fake_urlopen(_request, *, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            return _Response(200, {"status": "ok", "version": "local"})
        return _Response(200, _valid_refresh_result())

    monkeypatch.setattr(dossier_cli, "urlopen", fake_urlopen)
    monkeypatch.setattr(dossier_cli, "init_db", lambda: (_ for _ in ()).throw(AssertionError("no local DB")))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 0
    assert len(calls) == 2


def test_refresh_once_uses_local_path_only_for_connection_refused(monkeypatch):
    calls = []
    local_calls = []

    def refused(_request, *, timeout):
        calls.append(timeout)
        raise URLError(ConnectionRefusedError("no listener"))

    monkeypatch.setattr(dossier_cli, "urlopen", refused)
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))
    monkeypatch.setattr(
        "app.services.auto_refresh.refresh_once",
        lambda: local_calls.append("refresh") or _valid_refresh_result(),
    )

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 0
    assert calls == [dossier_cli.HEALTH_TIMEOUT_SECONDS]
    assert local_calls == ["init", "refresh"]
    assert json.loads(result.stdout) == _valid_refresh_result()


def test_refresh_once_reachable_bad_health_fails_closed_without_local_fallback(monkeypatch):
    local_calls = []
    monkeypatch.setattr(
        dossier_cli,
        "urlopen",
        lambda _request, *, timeout: _Response(200, {"status": "unexpected"}),
    )
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 1
    assert local_calls == []
    assert "health" in result.stdout.lower()


def test_refresh_once_non_200_or_transport_health_failure_never_falls_back(monkeypatch):
    local_calls = []
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))

    monkeypatch.setattr(dossier_cli, "urlopen", lambda _request, *, timeout: _Response(503, {"status": "ok"}))
    non_200 = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    monkeypatch.setattr(
        dossier_cli,
        "urlopen",
        lambda _request, *, timeout: (_ for _ in ()).throw(URLError(OSError("network unreachable"))),
    )
    transport = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert non_200.exit_code == 1
    assert transport.exit_code == 1
    assert local_calls == []


def test_refresh_once_malformed_health_json_fails_closed_without_local_fallback(monkeypatch):
    local_calls = []
    monkeypatch.setattr(dossier_cli, "urlopen", lambda _request, *, timeout: _RawResponse(200, b"{"))
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 1
    assert local_calls == []


def test_refresh_once_timeout_fails_closed_without_local_fallback(monkeypatch):
    local_calls = []
    monkeypatch.setattr(
        dossier_cli,
        "urlopen",
        lambda _request, *, timeout: (_ for _ in ()).throw(TimeoutError("timed out")),
    )
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 1
    assert local_calls == []


def test_refresh_once_rejects_post_payload_with_missing_or_extra_keys(monkeypatch):
    calls = []

    def fake_urlopen(_request, *, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            return _Response(200, {"status": "ok"})
        payload = _valid_refresh_result()
        payload["unexpected"] = True
        return _Response(200, payload)

    monkeypatch.setattr(dossier_cli, "urlopen", fake_urlopen)
    monkeypatch.setattr(dossier_cli, "init_db", lambda: (_ for _ in ()).throw(AssertionError("no local DB")))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 1
    assert len(calls) == 2


def test_refresh_once_rejects_missing_key_or_malformed_post_json(monkeypatch):
    local_calls = []
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))

    calls = []
    def missing_key(_request, *, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            return _Response(200, {"status": "ok"})
        payload = _valid_refresh_result()
        payload.pop("news_errors")
        return _Response(200, payload)

    monkeypatch.setattr(dossier_cli, "urlopen", missing_key)
    missing = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    calls.clear()
    def malformed(_request, *, timeout):
        calls.append(timeout)
        return _Response(200, {"status": "ok"}) if len(calls) == 1 else _RawResponse(200, b"[")

    monkeypatch.setattr(dossier_cli, "urlopen", malformed)
    malformed_result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert missing.exit_code == 1
    assert malformed_result.exit_code == 1
    assert local_calls == []


def test_refresh_once_rejects_post_http_or_type_failure_without_a_second_run(monkeypatch):
    local_calls = []
    monkeypatch.setattr(dossier_cli, "init_db", lambda: local_calls.append("init"))

    calls = []
    def http_failure(_request, *, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            return _Response(200, {"status": "ok"})
        raise HTTPError(dossier_cli.REFRESH_URL, 503, "unavailable", hdrs=None, fp=None)

    monkeypatch.setattr(dossier_cli, "urlopen", http_failure)
    failed_http = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    calls.clear()
    def wrong_type(_request, *, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            return _Response(200, {"status": "ok"})
        payload = _valid_refresh_result()
        payload["news_refreshed"] = True
        return _Response(200, payload)

    monkeypatch.setattr(dossier_cli, "urlopen", wrong_type)
    failed_type = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert failed_http.exit_code == 1
    assert failed_type.exit_code == 1
    assert local_calls == []


def test_refresh_once_accepts_a_lock_busy_nine_field_response(monkeypatch):
    calls = []

    def fake_urlopen(_request, *, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            return _Response(200, {"status": "ok"})
        payload = _valid_refresh_result()
        payload["running"] = True
        return _Response(200, payload)

    monkeypatch.setattr(dossier_cli, "urlopen", fake_urlopen)
    monkeypatch.setattr(dossier_cli, "init_db", lambda: (_ for _ in ()).throw(AssertionError("no local DB")))

    result = CliRunner().invoke(dossier_cli.app, ["refresh-once"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["running"] is True


def test_auto_refresh_post_keeps_the_exact_nine_field_api_contract(monkeypatch):
    expected = _valid_refresh_result()
    monkeypatch.setattr(api.auto_refresh, "refresh_once", lambda: expected)

    response = TestClient(api.app).post("/api/auto-refresh/run")

    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_AUTO_REFRESH_KEYS
    assert response.json() == expected


def test_auto_refresh_status_get_keeps_the_exact_nine_field_api_contract():
    response = TestClient(api.app).get("/api/auto-refresh/status")

    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_AUTO_REFRESH_KEYS


def test_auto_refresh_post_lock_busy_path_keeps_the_exact_nine_field_contract(monkeypatch):
    class BusyLock:
        def acquire(self, *, blocking):
            assert blocking is False
            return False

    expected = _valid_refresh_result()
    expected["running"] = True
    monkeypatch.setattr(api.auto_refresh, "_lock", BusyLock())
    monkeypatch.setattr(api.auto_refresh, "_state", expected)

    response = TestClient(api.app).post("/api/auto-refresh/run")

    assert response.status_code == 200
    assert set(response.json()) == EXPECTED_AUTO_REFRESH_KEYS
    assert response.json() == expected


def _create_valid_run(monkeypatch, root, *, observed_at=None, run_id="cli-run", topic_id=4, errors=None):
    observed_at = observed_at or datetime(2026, 7, 15, 16, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(
        coverage_observation.coverage_snapshot,
        "build_coverage_snapshot",
        lambda _session, topic_id, event_id=None: {
            "topic_id": topic_id,
            "event_id": None,
            "sample": {"basis": "persisted_topic_articles", "article_count": 0, "article_ids": [], "note": "persisted metadata"},
            "independent_source_count": 0,
            "source_distribution": [],
            "collector_distribution": [],
            "language_distribution": [],
            "country_distribution": [],
            "url_decoding": {"eligible_count": 0, "decoded_count": 0, "rate": None, "decoded_article_ids": [], "not_decoded_article_ids": []},
            "fulltext": {"status": "unknown", "reason": "article_bodies_not_persisted"},
            "source_registry": {"type_distribution": [], "tier_distribution": [], "unclassified_article_ids": [topic_id]},
        },
    )
    recorder = coverage_observation.begin_observation_run(root=root, observed_at=observed_at, run_id=run_id)
    recorder.record_committed(topic_id=topic_id, collection_result={"requests": [], "errors": errors if errors is not None else ["feed unavailable"]})
    assert recorder.finalize()["status"] == "finalized"


def test_coverage_verify_and_status_are_filesystem_only_and_report_hold(monkeypatch, tmp_path):
    _create_valid_run(monkeypatch, tmp_path)
    monkeypatch.setattr(dossier_cli, "init_db", lambda: (_ for _ in ()).throw(AssertionError("must not open SQLite")))
    runner = CliRunner()

    verified = runner.invoke(
        dossier_cli.app,
        ["coverage-verify", "--start", "2026-07-16", "--end", "2026-07-16", "--root", str(tmp_path)],
    )
    status = runner.invoke(
        dossier_cli.app,
        ["coverage-status", "--start", "2026-07-16", "--end", "2026-07-16", "--root", str(tmp_path)],
    )

    assert verified.exit_code == 0
    assert json.loads(verified.stdout)["valid"] is True
    assert status.exit_code == 0
    payload = json.loads(status.stdout)
    assert payload["review_state"] == "HOLD"
    assert payload["successful_dates"] == ["2026-07-16"]
    assert payload["fulltext_metadata_debt"] == 1
    assert payload["unclassified_metadata_debt"] == 1
    assert "GO" not in status.stdout and "NO-GO" not in status.stdout


def test_coverage_commands_reject_corrupt_or_missing_evidence(monkeypatch, tmp_path):
    _create_valid_run(monkeypatch, tmp_path)
    topic = tmp_path / "2026-07-16" / "cli-run" / "topic-4.json"
    topic.write_text("{}", encoding="utf-8")
    runner = CliRunner()

    corrupt = runner.invoke(
        dossier_cli.app,
        ["coverage-verify", "--start", "2026-07-16", "--end", "2026-07-16", "--root", str(tmp_path)],
    )
    missing = runner.invoke(
        dossier_cli.app,
        ["coverage-status", "--start", "2026-07-17", "--end", "2026-07-17", "--root", str(tmp_path / "missing")],
    )

    assert corrupt.exit_code == 1
    assert json.loads(corrupt.stdout)["valid"] is False
    assert missing.exit_code == 1
    assert json.loads(missing.stdout)["valid"] is False


def test_coverage_status_anchors_to_all_retained_evidence_and_emits_topic_dates(monkeypatch, tmp_path):
    _create_valid_run(monkeypatch, tmp_path, run_id="first", topic_id=4)
    _create_valid_run(
        monkeypatch,
        tmp_path,
        observed_at=datetime(2026, 8, 20, 16, 30, tzinfo=timezone.utc),
        run_id="later",
        topic_id=4,
    )

    result = CliRunner().invoke(
        dossier_cli.app,
        ["coverage-status", "--start", "2026-08-20", "--end", "2026-08-20", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["first_successful_date"] == "2026-07-16"
    assert payload["successful_dates"] == ["2026-07-16"]
    assert payload["topic_distinct_shanghai_dates"] == {"4": ["2026-07-16"]}


def test_coverage_status_uses_the_latest_valid_same_topic_same_day_representative(monkeypatch, tmp_path):
    _create_valid_run(monkeypatch, tmp_path, run_id="early", topic_id=9, errors=["collector degraded"])
    _create_valid_run(
        monkeypatch,
        tmp_path,
        observed_at=datetime(2026, 7, 15, 17, 30, tzinfo=timezone.utc),
        run_id="late",
        topic_id=9,
        errors=[],
    )

    result = CliRunner().invoke(
        dossier_cli.app,
        ["coverage-status", "--start", "2026-07-16", "--end", "2026-07-16", "--root", str(tmp_path)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["successful_dates"] == ["2026-07-16"]
    assert payload["topic_distinct_shanghai_dates"] == {"9": ["2026-07-16"]}
    assert payload["collector_degraded_observations"] == 0
