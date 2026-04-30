"""Aria vector-memory tools.

Thin, safe wrappers around Aria's local vector-memory scripts. Commands are
constructed as argv lists with ``shell=False`` and validated inputs.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tools.registry import registry, tool_error, tool_result

VECTOR_MEMORY_DIR = Path("/home/aria/workspace/vector-memory")
SEARCH_SCRIPT = VECTOR_MEMORY_DIR / "search.sh"
REINDEX_SCRIPT = VECTOR_MEMORY_DIR / "reindex.sh"
MAX_TOP_K = 50
TIMEOUT_SECONDS = 60


def _parse_json_or_text(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _validate_top_k(top_k: int) -> int:
    try:
        value = int(top_k)
    except (TypeError, ValueError) as exc:
        raise ValueError("top_k must be an integer") from exc
    if value < 1 or value > MAX_TOP_K:
        raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}")
    return value


def _filter_args(filters: dict[str, Any] | None) -> list[str]:
    if not filters:
        return []
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    args: list[str] = []
    for key, value in sorted(filters.items()):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("filter keys must be non-empty strings")
        if any(ch in key for ch in "=\x00"):
            raise ValueError("filter keys may not contain '=' or NUL")
        if isinstance(value, (dict, list, tuple)):
            raise ValueError("filter values must be scalar")
        args.extend(["--filter", f"{key}={value}"])
    return args


def aria_vector_search(query: str, top_k: int = 5, filters: dict[str, Any] | None = None) -> str:
    """Search Aria vector memory via ``search.sh``."""
    if not isinstance(query, str) or not query.strip():
        return tool_error("query must be a non-empty string", ok=False)
    try:
        top_k_value = _validate_top_k(top_k)
        cmd = [str(SEARCH_SCRIPT), query, "--top-k", str(top_k_value)] + _filter_args(filters)
    except ValueError as exc:
        return tool_error(str(exc), ok=False)

    if not SEARCH_SCRIPT.exists():
        return tool_error(f"search script not found: {SEARCH_SCRIPT}", ok=False)

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            shell=False,
            cwd=str(SEARCH_SCRIPT.parent),
        )
    except Exception as exc:
        return tool_error(str(exc), ok=False)

    if completed.returncode != 0:
        return tool_error(
            "vector search failed",
            ok=False,
            returncode=completed.returncode,
            stderr=completed.stderr[-4000:],
        )

    return tool_result({
        "ok": True,
        "query": query,
        "top_k": top_k_value,
        "results": _parse_json_or_text(completed.stdout),
        "stderr": completed.stderr[-4000:] if completed.stderr else "",
    })


def aria_vector_reindex(dry_run: bool = True) -> str:
    """Reindex vector memory. Defaults to dry-run and does not execute."""
    cmd = [str(REINDEX_SCRIPT)]
    if dry_run:
        return tool_result({"ok": True, "dry_run": True, "would_run": cmd})

    if not REINDEX_SCRIPT.exists():
        return tool_error(f"reindex script not found: {REINDEX_SCRIPT}", ok=False)

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS * 5,
            shell=False,
            cwd=str(REINDEX_SCRIPT.parent),
        )
    except Exception as exc:
        return tool_error(str(exc), ok=False)

    return tool_result({
        "ok": completed.returncode == 0,
        "dry_run": False,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-4000:],
    })


ARIA_VECTOR_SEARCH_SCHEMA = {
    "name": "aria_vector_search",
    "description": "Search Aria vector memory using the local vector-memory/search.sh script.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": MAX_TOP_K},
            "filters": {"type": "object", "description": "Optional scalar key/value filters."},
        },
        "required": ["query"],
    },
}

ARIA_VECTOR_REINDEX_SCHEMA = {
    "name": "aria_vector_reindex",
    "description": "Reindex Aria vector memory. Defaults to dry_run=true for safety.",
    "parameters": {
        "type": "object",
        "properties": {
            "dry_run": {"type": "boolean", "default": True, "description": "When true, only show the command."},
        },
        "required": [],
    },
}

registry.register(
    name="aria_vector_search",
    toolset="aria_vector",
    schema=ARIA_VECTOR_SEARCH_SCHEMA,
    handler=lambda args, **kw: aria_vector_search(args.get("query", ""), args.get("top_k", 5), args.get("filters")),
    emoji="🔎",
)
registry.register(
    name="aria_vector_reindex",
    toolset="aria_vector",
    schema=ARIA_VECTOR_REINDEX_SCHEMA,
    handler=lambda args, **kw: aria_vector_reindex(args.get("dry_run", True)),
    emoji="🧭",
)
