"""Event-name adapter for aria-live compatibility.

The module intentionally stays dependency-free so it can be exercised without a
running Hermes server or websocket stack.
"""

from __future__ import annotations

from typing import Any, Mapping

ARIA_EVENT_MAP: dict[str, str] = {
    "tool.start": "before_tool_call",
    "tool.complete": "after_tool_call",
    "message.received": "message_received",
    "message.sending": "message_sending",
    "message.sent": "message_sent",
    "agent.complete": "agent_end",
    "compression.start": "before_compaction",
    "compression.complete": "after_compaction",
}


def aria_event_name(event_name: object) -> str:
    """Return the aria-live event name for a Hermes-ish event name.

    Unknown non-empty names pass through unchanged. Missing/empty names collapse
    to a stable ``"unknown"`` value instead of raising.
    """

    if event_name is None:
        return "unknown"
    name = str(event_name)
    if not name:
        return "unknown"
    return ARIA_EVENT_MAP.get(name, name)


def _extract_event_name(event: Any) -> object:
    if isinstance(event, Mapping):
        return event.get("type") or event.get("event") or event.get("name")
    return event


def adapt_event(event: Any) -> dict[str, Any]:
    """Wrap an event in a small aria-compatible envelope.

    The original event is preserved under ``payload`` so callers can retain any
    Hermes-specific fields while routing by the mapped ``type``/``aria_event``.
    """

    source_type = _extract_event_name(event)
    mapped = aria_event_name(source_type)
    return {
        "type": mapped,
        "aria_event": mapped,
        "source_type": "unknown" if source_type is None or str(source_type) == "" else str(source_type),
        "payload": event,
    }
