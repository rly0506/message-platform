"""Read-only diagnostics for the local OpenCLI integration."""
from __future__ import annotations

import os
import shutil
import subprocess

from app import config

COMMON_WINDOWS_COMMANDS = [
    r"D:\npm-global\opencli.cmd",
    r"C:\Users\任锂帅\AppData\Roaming\npm\opencli.cmd",
]

BROWSER_REQUIRED_PLATFORMS = ["reddit", "bilibili", "xiaohongshu", "xueqiu"]


def diagnose_opencli() -> dict[str, object]:
    command = (config.OPENCLI_COMMAND or "opencli").strip() or "opencli"
    resolved = resolve_command(command)
    recommended = "" if resolved else recommended_command()
    start_error = start_error_for(command, resolved)
    available = bool(resolved) and not start_error
    return {
        "configured_command": command,
        "available": available,
        "resolved_path": resolved,
        "recommended_command": recommended,
        "browser_required_platforms": BROWSER_REQUIRED_PLATFORMS,
        "start_error": start_error,
        "message": diagnostic_message(command, resolved, recommended, start_error),
    }


def resolve_command(command: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(command))
    if os.path.isabs(expanded) and os.path.exists(expanded):
        return expanded
    found = shutil.which(expanded)
    return found or ""


def recommended_command() -> str:
    for candidate in COMMON_WINDOWS_COMMANDS:
        expanded = os.path.expandvars(os.path.expanduser(candidate))
        if os.path.exists(expanded):
            return expanded
    return ""


def start_error_for(command: str, resolved: str) -> dict[str, object] | None:
    if not resolved:
        return {"kind": "not_found", "errno": None, "detail": f"OpenCLI command '{command}' was not found."}
    try:
        subprocess.run(
            opencli_args(resolved, ["--help"]),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except OSError as exc:
        return {"kind": "cannot_start", "errno": getattr(exc, "errno", None), "detail": str(exc).strip() or exc.__class__.__name__}
    except subprocess.TimeoutExpired as exc:
        return {"kind": "startup_timeout", "errno": None, "detail": f"OpenCLI startup probe timed out after {exc.timeout}s."}
    return None


def opencli_args(command: str, args: list[str]) -> list[str]:
    if os.name == "nt" and command.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", command, *args]
    return [command, *args]


def diagnostic_message(command: str, resolved: str, recommended: str, start_error: dict[str, object] | None = None) -> str:
    if start_error and start_error.get("kind") == "cannot_start":
        return (
            f"OpenCLI was found at '{resolved}' but could not start: {start_error.get('detail')}. "
            "Set OPENCLI_COMMAND to a runnable opencli/opencli.cmd path before checking Chrome or platform login state."
        )
    if resolved:
        return f"OpenCLI resolved at {resolved}. If a platform still fails, check Chrome and platform login state."
    if recommended:
        return f"OpenCLI is not available at '{command}'. Set OPENCLI_COMMAND to '{recommended}'."
    return f"OpenCLI is not available at '{command}'. Set OPENCLI_COMMAND to the full local path."
