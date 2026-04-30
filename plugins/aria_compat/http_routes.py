"""Framework-light HTTP route helpers for aria compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_WORKSPACE = Path("/home/aria/workspace")
DEFAULT_DASHBOARD_STATUS_PATH = DEFAULT_WORKSPACE / "dashboard" / "status.json"


def health_payload(
    sessions: int = 0,
    ws_clients: int = 0,
    uptime_s: int = 0,
    profile: str = "aria",
) -> dict[str, Any]:
    """Return an Aria-compatible health response with Hermes metadata.

    The old Aria bridge clients expect ``status``, ``sessions``,
    ``ws_clients``, and ``uptime_s``. Hermes adds ``runtime`` and ``profile``
    for clarity.
    """

    return {
        "status": "ok",
        "sessions": int(sessions),
        "ws_clients": int(ws_clients),
        "uptime_s": int(uptime_s),
        "runtime": "hermes",
        "profile": profile,
    }


def append_cron_history_payload(entry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the normalized payload for appending a cron-history entry.

    Persistence is intentionally left to a framework/storage layer; keeping this
    pure makes route behavior easy to test and reuse.
    """

    return {"ok": True, "entry": dict(entry or {})}


def dashboard_status_payload(
    status_path: str | Path = DEFAULT_DASHBOARD_STATUS_PATH,
) -> dict[str, Any]:
    path = Path(status_path)
    if not path.exists():
        return {"ok": False, "error": "status_not_found", "status": None}

    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": "invalid_status_json", "detail": str(exc), "status": None}
    except OSError as exc:
        return {"ok": False, "error": "status_read_failed", "detail": str(exc), "status": None}

    return {"ok": True, "status": status}


def refresh_command_payload(workspace: str | Path = DEFAULT_WORKSPACE) -> dict[str, Any]:
    """Build a guarded refresh command for the fixed ``update.py`` script.

    The command is only exposed when ``<workspace>/update.py`` exists. Callers
    can execute the returned command if desired; this helper does not spawn
    processes by itself.
    """

    script = Path(workspace) / "update.py"
    if not script.is_file():
        return {"ok": False, "error": "update_script_not_found", "command": None}
    return {"ok": True, "command": ["python", str(script)]}


def is_pc_route_authorized(configured_token: str | None, provided_token: str | None) -> bool:
    """PC route auth helper; route is disabled when no token is configured."""

    if not configured_token:
        return False
    return provided_token == configured_token
