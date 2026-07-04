"""Read-only diagnostics for the local OpenCLI integration."""
from __future__ import annotations

import os
import shutil

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
    available = bool(resolved)
    return {
        "configured_command": command,
        "available": available,
        "resolved_path": resolved,
        "recommended_command": recommended,
        "browser_required_platforms": BROWSER_REQUIRED_PLATFORMS,
        "message": diagnostic_message(command, resolved, recommended),
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


def diagnostic_message(command: str, resolved: str, recommended: str) -> str:
    if resolved:
        return f"OpenCLI resolved at {resolved}. If a platform still fails, check Chrome and platform login state."
    if recommended:
        return f"OpenCLI is not available at '{command}'. Set OPENCLI_COMMAND to '{recommended}'."
    return f"OpenCLI is not available at '{command}'. Set OPENCLI_COMMAND to the full local path."
