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
    briefing = report_payload.get("briefing")
    if isinstance(briefing, dict):
        lines.extend(_render_briefing(briefing))
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
    completed = subprocess.run(_agently_cli_args(args), capture_output=True, text=True, encoding="utf-8")
    return SendResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _agently_cli_args(args: list[str]) -> list[str]:
    if not args:
        return args
    command = args[0]
    if os.name == "nt" and not command.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", *args]
    return args


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


def _render_briefing(briefing: dict) -> list[str]:
    items = [item for item in briefing.get("items") or [] if isinstance(item, dict)]
    lines = ["", "## 今日事实", ""]
    if items:
        for index, item in enumerate(items, start=1):
            lines.extend(_render_briefing_item(item, index))
    else:
        lines.extend(["近 14 天没有可用的持久化事实条目，不用旧材料填满早报。", ""])

    domain = briefing.get("domain_today")
    if isinstance(domain, dict):
        label = str(domain.get("domain_label") or domain.get("domain_key") or "未命名领域").strip()
        lines.extend([f"## 今日一个领域 · {label}", ""])
        for question in domain.get("questions") or []:
            text = str(question or "").strip()
            if text:
                lines.append(f"- {text}")
        note = str(domain.get("note") or "").strip()
        if note:
            lines.extend(["", f"> {note}"])
        lines.append("")
    return lines


def _render_briefing_item(item: dict, index: int) -> list[str]:
    title = str(item.get("title") or "未命名事实条目").strip()
    summary = str(item.get("fact_summary") or "").strip()
    source = str(item.get("source") or "来源未知").strip()
    published_at = str(item.get("published_at") or "时间未知").strip()
    evidence_url = str(item.get("evidence_url") or "").strip()
    deep_link = str(item.get("deep_link_url") or item.get("deep_link_path") or "").strip()
    coverage = item.get("coverage") if isinstance(item.get("coverage"), dict) else {}
    coverage_label = str(coverage.get("label") or "覆盖未知").strip()

    lines = [
        f"{index}. **{title}**",
        f"   - 事实摘要: {summary or '该条持久化记录目前只有标题；正文未落库。'}",
        f"   - 证据范围: {coverage_label}",
        f"   - 来源/时间: {source} · {published_at}",
        "   - 摘要依据: 单篇持久化标题与站点摘要；正文未落库",
    ]
    if evidence_url:
        lines.append(f"   - 原始证据: {evidence_url}")
    if deep_link:
        lines.append(f"   - 回到工作台: {deep_link}")
    lines.extend(["   - 覆盖边界: 未采集到不等于来源未报道。", ""])
    return lines
