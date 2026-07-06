import pytest
from typer.testing import CliRunner

from app.discovery import daily_email
import cli as dossier_cli


def _report_payload():
    return {
        "run_id": "20260705T090000Z",
        "path": r"D:\project\backend\discovery_reports\frontier-20260705T090000Z.md",
        "markdown": "## Full report\n\nLonger archive body.",
        "seeds": [
            {
                "title": "New nuclear battery moves from lab to pilot",
                "url": "https://example.com/energy",
                "domain": "energy",
                "domain_label": "Energy",
                "signal": 88,
                "delta": 32,
                "is_new": True,
                "what": "Small nuclear storage enters pilot.",
                "why": "Energy storage is outside the current cognition boundary.",
                "still_niche": True,
            },
            {
                "title": "GPU cluster financing shifts to private credit",
                "url": "https://example.com/finance",
                "domain": "finance",
                "domain_label": "Finance",
                "signal": 65,
                "delta": 12,
                "is_new": False,
                "what": "Compute center financing changes.",
                "why": "Connects finance background with AI infrastructure.",
                "still_niche": True,
            },
        ],
    }


def test_build_daily_digest_body_puts_top_seeds_before_full_report():
    body = daily_email.build_daily_digest_body(_report_payload())

    assert body.startswith("# 今日前沿早报")
    assert "20260705T090000Z" in body
    assert "## 今日最值得看的 2 条" in body
    assert "1. New nuclear battery moves from lab to pilot" in body
    assert "Small nuclear storage enters pilot." in body
    assert "Energy storage is outside the current cognition boundary." in body
    assert "https://example.com/energy" in body
    assert body.index("## 今日最值得看的 2 条") < body.index("## 完整日报")
    assert "Longer archive body." in body


def test_build_daily_digest_body_handles_report_without_seeds():
    body = daily_email.build_daily_digest_body({
        "run_id": "20260705T090000Z",
        "markdown": "## Baseline only",
        "seeds": [],
    })

    assert "## 今日最值得看的 0 条" in body
    assert "今天没有结构化种子" in body
    assert "## Baseline only" in body


def test_send_daily_digest_requires_recipient_before_cli_call():
    called = False

    def fake_runner(_args):
        nonlocal called
        called = True
        raise AssertionError("runner should not be called without a recipient")

    with pytest.raises(daily_email.DailyEmailError, match="DAILY_DIGEST_TO"):
        daily_email.send_daily_digest(
            _report_payload(),
            to="",
            runner=fake_runner,
            write_body=lambda _body: "unused.md",
        )

    assert called is False


def test_send_daily_digest_invokes_agently_cli_with_body_file():
    captured = {}

    def fake_runner(args):
        captured["args"] = args
        return daily_email.SendResult(returncode=0, stdout='{"confirmation_token":"ctk_1"}', stderr="")

    def fake_write_body(body):
        captured["body"] = body
        return "digest.md"

    result = daily_email.send_daily_digest(
        _report_payload(),
        to="reader@example.com",
        runner=fake_runner,
        write_body=fake_write_body,
    )

    assert result.returncode == 0
    assert captured["args"] == [
        "agently-cli",
        "message",
        "+send",
        "--to",
        "reader@example.com",
        "--subject",
        "今日前沿早报 20260705T090000Z",
        "--body-file",
        "digest.md",
    ]
    assert "New nuclear battery" in captured["body"]


def test_send_daily_digest_smtp_requires_recipient_and_host_before_connection():
    called = False

    def fake_smtp_factory(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("SMTP should not be opened without required config")

    with pytest.raises(daily_email.DailyEmailError, match="DAILY_DIGEST_TO"):
        daily_email.send_daily_digest_smtp(
            _report_payload(),
            to="",
            env={},
            smtp_factory=fake_smtp_factory,
        )

    with pytest.raises(daily_email.DailyEmailError, match="DAILY_DIGEST_SMTP_HOST"):
        daily_email.send_daily_digest_smtp(
            _report_payload(),
            to="reader@example.com",
            env={"DAILY_DIGEST_TO": "reader@example.com"},
            smtp_factory=fake_smtp_factory,
        )

    assert called is False


def test_send_daily_digest_smtp_sends_markdown_email_with_configured_account():
    events = []
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            events.append(("close",))

        def starttls(self):
            events.append(("starttls",))

        def login(self, user, password):
            events.append(("login", user, password))

        def send_message(self, message):
            sent["message"] = message
            events.append(("send", message["To"], message["Subject"]))

    result = daily_email.send_daily_digest_smtp(
        _report_payload(),
        env={
            "DAILY_DIGEST_TO": "reader@example.com",
            "DAILY_DIGEST_SMTP_HOST": "smtp.example.com",
            "DAILY_DIGEST_SMTP_PORT": "587",
            "DAILY_DIGEST_SMTP_USER": "sender@example.com",
            "DAILY_DIGEST_SMTP_PASSWORD": "secret",
            "DAILY_DIGEST_FROM": "Digest Bot <sender@example.com>",
        },
        smtp_factory=FakeSMTP,
    )

    assert result.returncode == 0
    assert events == [
        ("connect", "smtp.example.com", 587, 30),
        ("starttls",),
        ("login", "sender@example.com", "secret"),
        ("send", "reader@example.com", "今日前沿早报 20260705T090000Z"),
        ("close",),
    ]
    message = sent["message"]
    assert message["From"] == "Digest Bot <sender@example.com>"
    assert "New nuclear battery moves from lab to pilot" in message.get_content()


def test_daily_email_cli_send_smtp_uses_smtp_path(monkeypatch):
    from app.discovery import run as discovery_run

    captured = {}

    def fake_send_smtp(report, to=""):
        captured["report"] = report
        captured["to"] = to
        return daily_email.SendResult(returncode=0, stdout="smtp sent", stderr="")

    monkeypatch.setattr(discovery_run, "latest_report", lambda: _report_payload())
    monkeypatch.setattr(daily_email, "send_daily_digest_smtp", fake_send_smtp)

    result = CliRunner().invoke(
        dossier_cli.app,
        ["daily-email", "--send-smtp", "--to", "reader@example.com"],
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "smtp sent"
    assert captured["report"]["run_id"] == "20260705T090000Z"
    assert captured["to"] == "reader@example.com"
