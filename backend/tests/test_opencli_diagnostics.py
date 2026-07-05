from fastapi.testclient import TestClient

from app import api


def test_opencli_diagnostics_recommends_known_windows_global_path(monkeypatch, tmp_path):
    from app.services import opencli_diagnostics

    candidate = tmp_path / "opencli.cmd"
    candidate.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(opencli_diagnostics.config, "OPENCLI_COMMAND", "opencli")
    monkeypatch.setattr(opencli_diagnostics.shutil, "which", lambda command: None)
    monkeypatch.setattr(opencli_diagnostics, "COMMON_WINDOWS_COMMANDS", [str(candidate)])

    payload = opencli_diagnostics.diagnose_opencli()

    assert payload["configured_command"] == "opencli"
    assert payload["available"] is False
    assert payload["resolved_path"] == ""
    assert payload["recommended_command"] == str(candidate)
    assert "OPENCLI_COMMAND" in payload["message"]


def test_opencli_diagnostics_endpoint_returns_resolved_command(monkeypatch, tmp_path):
    from app.services import opencli_diagnostics

    command = tmp_path / "opencli.cmd"
    command.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(opencli_diagnostics.config, "OPENCLI_COMMAND", str(command))
    monkeypatch.setattr(opencli_diagnostics.shutil, "which", lambda value: str(command) if value == str(command) else None)

    response = TestClient(api.app).get("/api/integrations/opencli/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured_command"] == str(command)
    assert payload["available"] is True
    assert payload["resolved_path"] == str(command)
    assert "bilibili" in payload["browser_required_platforms"]


def test_opencli_diagnostics_reports_structured_start_error(monkeypatch, tmp_path):
    from app.services import opencli_diagnostics

    command = tmp_path / "opencli.exe"
    command.write_text("not really executable", encoding="utf-8")
    monkeypatch.setattr(opencli_diagnostics.config, "OPENCLI_COMMAND", str(command))
    monkeypatch.setattr(opencli_diagnostics.shutil, "which", lambda value: str(command) if value == str(command) else None)

    def cannot_start(*args, **kwargs):
        raise OSError(193, "%1 is not a valid Win32 application")

    monkeypatch.setattr(opencli_diagnostics.subprocess, "run", cannot_start)

    payload = opencli_diagnostics.diagnose_opencli()

    assert payload["available"] is False
    assert payload["resolved_path"] == str(command)
    assert payload["start_error"]["kind"] == "cannot_start"
    assert payload["start_error"]["errno"] == 193
    assert "OPENCLI_COMMAND" in payload["message"]
