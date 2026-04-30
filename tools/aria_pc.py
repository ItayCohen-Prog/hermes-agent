"""Aria PC access tools.

Safe wrappers around ``/home/aria/aria-bridge/pc_access.py``. These tools never
return key paths or key material and invoke the wrapper with argv lists only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.registry import registry, tool_error, tool_result

ARIA_BRIDGE_DIR = Path("/home/aria/aria-bridge")
PC_ACCESS_SCRIPT = ARIA_BRIDGE_DIR / "pc_access.py"
TIMEOUT_SECONDS = 60

_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passphrase|token|secret|private_key)\s*=\s*[^\s]+"
)
_SECRET_JSON_KEY_PARTS = ("password", "passphrase", "token", "secret", "private", "private_key", "ssh_key", "key_path")
_SSH_PATH_RE = re.compile(r"/home/[^\s\"']*/\.ssh/[^\s\"']+")


def _redact(text: str) -> str:
    text = _PRIVATE_KEY_RE.sub("[REDACTED PRIVATE KEY]", text or "")
    text = _SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    return _SSH_PATH_RE.sub("[REDACTED SSH PATH]", text)


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in _SECRET_JSON_KEY_PARTS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_json(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        return _redact(value)
    return value


def _parse_json_or_text(text: str) -> Any:
    redacted = _redact(text)
    stripped = redacted.strip()
    if not stripped:
        return {}
    try:
        return _sanitize_json(json.loads(stripped))
    except json.JSONDecodeError:
        return stripped


def _run_pc_access(args: list[str], timeout: int = TIMEOUT_SECONDS) -> str:
    if not PC_ACCESS_SCRIPT.exists():
        return tool_error(f"PC access script not found: {PC_ACCESS_SCRIPT}", ok=False)

    cmd = [sys.executable, str(PC_ACCESS_SCRIPT)] + args
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            cwd=str(PC_ACCESS_SCRIPT.parent),
        )
    except Exception as exc:
        return tool_error(str(exc), ok=False)

    payload = {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "result": _parse_json_or_text(completed.stdout),
        "stderr": _redact(completed.stderr)[-4000:],
    }
    return tool_result(payload)


def aria_pc_status() -> str:
    """Return safe status for the Aria PC bridge wrapper."""
    return tool_result({
        "script": str(PC_ACCESS_SCRIPT),
        "script_exists": PC_ACCESS_SCRIPT.exists(),
        "bridge_dir_exists": PC_ACCESS_SCRIPT.parent.exists(),
    })


def aria_pc_ensure() -> str:
    """Ensure Aria PC access is available via pc_access.py."""
    return _run_pc_access(["ensure"], timeout=TIMEOUT_SECONDS)


def aria_pc_ssh_command(command: str, timeout: int = TIMEOUT_SECONDS) -> str:
    """Run a command on Aria's PC through pc_access.py without exposing keys."""
    if not isinstance(command, str) or not command.strip():
        return tool_error("command must be a non-empty string", ok=False)
    try:
        timeout_value = int(timeout)
    except (TypeError, ValueError):
        return tool_error("timeout must be an integer", ok=False)
    timeout_value = max(1, min(timeout_value, 300))
    return _run_pc_access(["ssh", "--", command], timeout=timeout_value)


ARIA_PC_STATUS_SCHEMA = {
    "name": "aria_pc_status",
    "description": "Return safe status for Aria's PC access bridge wrapper without exposing keys.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ARIA_PC_ENSURE_SCHEMA = {
    "name": "aria_pc_ensure",
    "description": "Ensure Aria PC access is set up via /home/aria/aria-bridge/pc_access.py.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ARIA_PC_SSH_COMMAND_SCHEMA = {
    "name": "aria_pc_ssh_command",
    "description": "Run a command on Aria's PC through pc_access.py; output is redacted for secret/key material.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Remote shell command to run."},
            "timeout": {"type": "integer", "default": TIMEOUT_SECONDS, "minimum": 1, "maximum": 300},
        },
        "required": ["command"],
    },
}

registry.register(
    name="aria_pc_status",
    toolset="aria_pc",
    schema=ARIA_PC_STATUS_SCHEMA,
    handler=lambda args, **kw: aria_pc_status(),
    emoji="🖥️",
)
registry.register(
    name="aria_pc_ensure",
    toolset="aria_pc",
    schema=ARIA_PC_ENSURE_SCHEMA,
    handler=lambda args, **kw: aria_pc_ensure(),
    emoji="🖥️",
)
registry.register(
    name="aria_pc_ssh_command",
    toolset="aria_pc",
    schema=ARIA_PC_SSH_COMMAND_SCHEMA,
    handler=lambda args, **kw: aria_pc_ssh_command(args.get("command", ""), args.get("timeout", TIMEOUT_SECONDS)),
    emoji="🖥️",
)
