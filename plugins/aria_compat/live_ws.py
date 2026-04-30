"""Lightweight websocket-command compatibility surface.

This is deliberately network-free: tests and callers can exercise connection
accounting and command handling without opening sockets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

SUPPORTED_COMMANDS = frozenset(
    {
        "interrupt",
        "queue_cancel",
        "queue_clear",
        "queue_promote",
        "queue_steer",
    }
)


@dataclass
class LiveWSHub:
    """Small in-memory model of aria-live websocket behavior."""

    host: str = "127.0.0.1"
    port: int = 18790
    _clients: set[str] = field(default_factory=set, init=False, repr=False)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def connect(self, client_id: str | None = None) -> dict[str, Any]:
        client_id = client_id or uuid4().hex
        self._clients.add(client_id)
        return {
            "type": "connected",
            "client_id": client_id,
            "client_count": self.client_count,
            "host": self.host,
            "port": self.port,
        }

    def disconnect(self, client_id: str) -> dict[str, Any]:
        self._clients.discard(client_id)
        return {
            "type": "disconnected",
            "client_id": client_id,
            "client_count": self.client_count,
        }

    def handle_command(self, command: str, **data: Any) -> dict[str, Any]:
        if command not in SUPPORTED_COMMANDS:
            return {
                "ok": False,
                "type": "error",
                "error": "unsupported_command",
                "command": command,
                "supported_commands": sorted(SUPPORTED_COMMANDS),
            }
        return {
            "ok": True,
            "type": "command_ack",
            "command": command,
            "data": data,
        }
