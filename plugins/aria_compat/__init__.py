"""Compatibility helpers and plugin entrypoint for aria-live integrations."""

from __future__ import annotations

import json
from typing import Any

from .cron_import import build_cron_import_plan, cron_import_summary, read_cron_history
from .discord_routing import (
    apply_routing_to_event,
    categories_summary,
    load_categories,
    sync_categories_plan,
)
from .event_adapter import ARIA_EVENT_MAP, adapt_event, aria_event_name
from .http_routes import (
    DEFAULT_DASHBOARD_STATUS_PATH,
    DEFAULT_WORKSPACE,
    append_cron_history_payload,
    dashboard_status_payload,
    health_payload,
    is_pc_route_authorized,
    refresh_command_payload,
)
from .live_ws import SUPPORTED_COMMANDS, LiveWSHub

_HUB = LiveWSHub()


def _format_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _handle_categories(raw_args: str = "") -> str:
    return categories_summary()


def _handle_sync_categories(raw_args: str = "") -> str:
    return _format_json(sync_categories_plan())


def _handle_aria_live(raw_args: str = "") -> str:
    command = (raw_args or "").strip()
    if not command or command in {"status", "help", "-h", "--help"}:
        return _format_json(
            {
                "host": _HUB.host,
                "port": _HUB.port,
                "clients": _HUB.client_count,
                "supported_commands": sorted(SUPPORTED_COMMANDS),
            }
        )
    parts = command.split(maxsplit=1)
    cmd = parts[0]
    data = {"raw_args": parts[1]} if len(parts) > 1 else {}
    return _format_json(_HUB.handle_command(cmd, **data))


def _handle_aria_cron_import(raw_args: str = "") -> str:
    mode = (raw_args or "").strip().lower()
    if mode == "json":
        return _format_json(build_cron_import_plan())
    if mode == "history":
        return _format_json(read_cron_history())
    return cron_import_summary()


def _pre_gateway_dispatch(event=None, **_: Any) -> dict[str, Any] | None:
    if event is None:
        return None
    return apply_routing_to_event(event, load_categories())


def register(ctx) -> None:
    """Register Aria compatibility commands and non-destructive routing hook."""

    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)
    ctx.register_command(
        "categories",
        handler=_handle_categories,
        description="Show Aria Discord category routing config.",
    )
    ctx.register_command(
        "sync_categories",
        handler=_handle_sync_categories,
        description="Dry-run Aria Discord category sync plan.",
    )
    ctx.register_command(
        "aria-live",
        handler=_handle_aria_live,
        description="Inspect or acknowledge aria-live compatibility commands.",
        args_hint="[status|command]",
    )
    ctx.register_command(
        "aria-cron-import",
        handler=_handle_aria_cron_import,
        description="Show dry-run Hermes cron import specs for Aria jobs.",
        args_hint="[json|history]",
    )


__all__ = [
    "ARIA_EVENT_MAP",
    "DEFAULT_DASHBOARD_STATUS_PATH",
    "DEFAULT_WORKSPACE",
    "LiveWSHub",
    "adapt_event",
    "append_cron_history_payload",
    "apply_routing_to_event",
    "aria_event_name",
    "build_cron_import_plan",
    "categories_summary",
    "cron_import_summary",
    "dashboard_status_payload",
    "health_payload",
    "is_pc_route_authorized",
    "load_categories",
    "read_cron_history",
    "refresh_command_payload",
    "register",
    "sync_categories_plan",
]
