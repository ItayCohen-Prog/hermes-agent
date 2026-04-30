"""Cron migration helpers for Hermes-as-Aria.

These helpers translate the current Aria cron inventory into importable Hermes
cron specs without creating jobs.  Live cron migration is a cutover step and must
remain explicit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_CRON_HISTORY = Path("/home/aria/aria-bridge/cron-history.json")

# Snapshot of the known Aria cron/watchdog jobs captured during migration.
KNOWN_ARIA_CRON_JOBS: tuple[dict[str, str], ...] = (
    {"name": "meet-recordings", "schedule": "30 4 * * *", "risk": "low"},
    {"name": "security-audit", "schedule": "0 4 * * *", "risk": "medium"},
    {"name": "vector-reindex", "schedule": "0 */3 * * *", "risk": "low"},
    {"name": "health-check", "schedule": "15 4 * * *", "risk": "low"},
    {"name": "weekly-audit", "schedule": "0 10 * * 0", "risk": "medium"},
    {"name": "dashboard-update", "schedule": "0 */3 * * *", "risk": "low"},
    {"name": "ai-feed-digest", "schedule": "0 7 * * *", "risk": "low"},
    {"name": "youtube-feed", "schedule": "0 7 * * *", "risk": "low"},
    {"name": "bridge-watchdog", "schedule": "* * * * *", "risk": "cutover"},
)


def hermes_cron_prompt(job_name: str) -> str:
    """Return a self-contained safe prompt for a migrated cron job."""

    return (
        f"Run the Aria workspace automation job `{job_name}` from /home/aria/workspace. "
        "Load Aria safety/google guardrail skills where relevant, do not expose secrets, "
        "summarize results, and report failures without modifying production routing."
    )


def build_cron_import_plan(
    jobs: Iterable[Mapping[str, Any]] = KNOWN_ARIA_CRON_JOBS,
) -> list[dict[str, Any]]:
    """Build dry-run Hermes cron creation specs for Aria jobs."""

    plan: list[dict[str, Any]] = []
    for job in jobs:
        name = str(job.get("name") or "").strip()
        schedule = str(job.get("schedule") or "").strip()
        if not name or not schedule:
            continue
        plan.append(
            {
                "name": f"aria-{name}",
                "source_name": name,
                "schedule": schedule,
                "prompt": hermes_cron_prompt(name),
                "profile": "aria",
                "dry_run": True,
                "risk": str(job.get("risk") or "unknown"),
            }
        )
    return plan


def cron_import_summary(plan: list[dict[str, Any]] | None = None) -> str:
    """Human-readable dry-run summary for `/aria-cron-import`."""

    plan = plan if plan is not None else build_cron_import_plan()
    lines = ["Aria cron import dry-run:"]
    for item in plan:
        lines.append(f"- {item['name']}: {item['schedule']} (risk={item['risk']})")
    lines.append("No Hermes cron jobs were created by this command.")
    return "\n".join(lines)


def read_cron_history(path: str | Path = DEFAULT_CRON_HISTORY, limit: int = 50) -> dict[str, Any]:
    """Read Aria cron history safely with bounded output."""

    history_path = Path(path)
    if not history_path.exists():
        return {"ok": False, "error": "history_not_found", "entries": []}
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": "invalid_history_json", "detail": str(exc), "entries": []}
    except OSError as exc:
        return {"ok": False, "error": "history_read_failed", "detail": str(exc), "entries": []}

    entries = data if isinstance(data, list) else data.get("entries", []) if isinstance(data, Mapping) else []
    if not isinstance(entries, list):
        entries = []
    return {"ok": True, "entries": entries[-max(1, int(limit)):]}
