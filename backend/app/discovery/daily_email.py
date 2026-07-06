"""Daily discovery digest helpers.

This module deliberately keeps email rendering separate from the CLI command so
tests can exercise the digest without touching the real Agent Mail account.
"""
from __future__ import annotations

import os
import smtplib
import subprocess
import tempfile
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable, Sequence


DEFAULT_RECIPIENT_ENV = "DAILY_DIGEST_TO"
DEFAULT_COMMAND = "agently-cli"
SMTP_HOST_ENV = "DAILY_DIGEST_SMTP_HOST"
SMTP_PORT_ENV = "DAILY_DIGEST_SMTP_PORT"
SMTP_USER_ENV = "DAILY_DIGEST_SMTP_USER"
SMTP_PASSWORD_ENV = "DAILY_DIGEST_SMTP_PASSWORD"
SMTP_FROM_ENV = "DAILY_DIGEST_FROM"
SMTP_TLS_ENV = "DAILY_DIGEST_SMTP_TLS"
MAX_HEADLINE_SEEDS = 5


class DailyEmailError(RuntimeError):
    """Raised when the daily digest cannot be prepared or sent."""


@dataclass(frozen=True)
class SendResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[list[str]], SendResult]
BodyWriter = Callable[[str], str]
SmtpFactory = Callable[..., object]


def build_daily_digest_body(report_payload: dict, *, headline_limit: int = MAX_HEADLINE_SEEDS) -> str:
    """Render a phone-friendly Markdown digest from an archived discovery report."""
    run_id = str(report_payload.get("run_id") or "")
    path = str(report_payload.get("path") or "")
    seeds = [seed for seed in report_payload.get("seeds") or [] if isinstance(seed, dict)]
    headline_seeds = _top_seeds(seeds, limit=headline_limit)
    markdown = str(report_payload.get("markdown") or "").strip()

    lines = [
        "# 今日前沿早报",
        "",
        f"- 报告时间: {run_id or '未知'}",
    ]
    if path:
        lines.append(f"- 本地归档: {path}")
    lines.extend(["", f"## 今日最值得看的 {len(headline_seeds)} 条", ""])

    if headline_seeds:
        for index, seed in enumerate(headline_seeds, start=1):
            lines.extend(_render_seed(seed, index))
    else:
        lines.append("今天没有结构化种子；这通常意味着首次基线、样本不足，或本轮没有明显加速信号。")
        lines.append("")

    lines.extend(["## 完整日报", "", markdown or "暂无完整日报正文。", ""])
    return "\n".join(lines)


def subject_for_report(report_payload: dict) -> str:
    run_id = str(report_payload.get("run_id") or "").strip()
    return f"今日前沿早报 {run_id}".strip()


def recipient_from_env(env: dict[str, str] | None = None) -> str:
    values = env if env is not None else os.environ
    return values.get(DEFAULT_RECIPIENT_ENV, "").strip()


def send_daily_digest(
    report_payload: dict,
    *,
    to: str = "",
    command: str = DEFAULT_COMMAND,
    confirmation_token: str = "",
    runner: Runner | None = None,
    write_body: BodyWriter | None = None,
) -> SendResult:
    """Start or complete the Agent Mail two-phase send flow."""
    recipient = to.strip()
    if not recipient:
        raise DailyEmailError(f"Set {DEFAULT_RECIPIENT_ENV} or pass --to before sending the daily digest.")

    body = build_daily_digest_body(report_payload)
    body_file = (write_body or write_body_file)(body)
    args = [
        command,
        "message",
        "+send",
        "--to",
        recipient,
        "--subject",
        subject_for_report(report_payload),
        "--body-file",
        body_file,
    ]
    if confirmation_token.strip():
        args.extend(["--confirmation-token", confirmation_token.strip()])
    return (runner or run_agently_cli)(args)


def send_daily_digest_smtp(
    report_payload: dict,
    *,
    to: str = "",
    env: dict[str, str] | None = None,
    smtp_factory: SmtpFactory | None = None,
) -> SendResult:
    """Send the latest digest through SMTP for unattended scheduled jobs."""
    values = env if env is not None else os.environ
    recipient = (to or values.get(DEFAULT_RECIPIENT_ENV, "")).strip()
    if not recipient:
        raise DailyEmailError(f"Set {DEFAULT_RECIPIENT_ENV} or pass --to before sending the daily digest.")

    host = values.get(SMTP_HOST_ENV, "").strip()
    if not host:
        raise DailyEmailError(f"Set {SMTP_HOST_ENV} before using --send-smtp.")

    port = _smtp_port(values.get(SMTP_PORT_ENV, "587"))
    user = values.get(SMTP_USER_ENV, "").strip()
    password = values.get(SMTP_PASSWORD_ENV, "")
    sender = values.get(SMTP_FROM_ENV, "").strip() or user
    if not sender:
        raise DailyEmailError(f"Set {SMTP_FROM_ENV} or {SMTP_USER_ENV} before using --send-smtp.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject_for_report(report_payload)
    message.set_content(build_daily_digest_body(report_payload), subtype="plain", charset="utf-8")

    factory = smtp_factory or smtplib.SMTP
    try:
        with factory(host, port, timeout=30) as smtp:
            if _smtp_tls_enabled(values.get(SMTP_TLS_ENV, "1")):
                smtp.starttls()
            if user or password:
                smtp.login(user, password)
            smtp.send_message(message)
    except OSError as exc:
        raise DailyEmailError(f"SMTP send failed: {type(exc).__name__}: {exc}") from exc
    except smtplib.SMTPException as exc:
        raise DailyEmailError(f"SMTP send failed: {type(exc).__name__}: {exc}") from exc

    return SendResult(returncode=0, stdout=f"Sent daily digest to {recipient} via SMTP.", stderr="")


def write_body_file(body: str) -> str:
    fd, path = tempfile.mkstemp(prefix="frontier-digest-", suffix=".md", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(body)
    return path


def run_agently_cli(args: list[str]) -> SendResult:
    completed = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    return SendResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _smtp_port(raw: str) -> int:
    try:
        port = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise DailyEmailError(f"{SMTP_PORT_ENV} must be a number.") from exc
    if port <= 0 or port > 65535:
        raise DailyEmailError(f"{SMTP_PORT_ENV} must be between 1 and 65535.")
    return port


def _smtp_tls_enabled(raw: str) -> bool:
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _top_seeds(seeds: Sequence[dict], *, limit: int) -> list[dict]:
    def score(seed: dict) -> tuple[float, float]:
        return (float(seed.get("signal") or 0), float(seed.get("delta") or 0))

    return sorted(seeds, key=score, reverse=True)[:limit]


def _render_seed(seed: dict, index: int) -> list[str]:
    title = str(seed.get("title") or "Untitled").strip()
    url = str(seed.get("url") or "").strip()
    domain = str(seed.get("domain_label") or seed.get("domain") or "").strip()
    what = str(seed.get("what") or "").strip()
    why = str(seed.get("why") or "").strip()
    signal = seed.get("signal") or 0
    delta = seed.get("delta") or 0

    lines = [f"{index}. {title}"]
    meta = " / ".join(part for part in [domain, f"signal {signal}", f"delta {delta}"] if part)
    if meta:
        lines.append(f"   - 信号: {meta}")
    if what:
        lines.append(f"   - 摘要: {what}")
    if why:
        lines.append(f"   - 为什么值得看: {why}")
    if url:
        lines.append(f"   - 原文: {url}")
    lines.append("")
    return lines
