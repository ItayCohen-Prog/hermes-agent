"""Aria workspace convenience tools.

These tools expose only safe, high-level workspace status and public memory/docs
content. They deliberately avoid credential files and secret-shaped filenames.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from hermes_constants import get_hermes_home
from tools.registry import registry, tool_result

ARIA_HOME = Path("/home/aria")
WORKSPACE_DIR = ARIA_HOME / "workspace"
VECTOR_MEMORY_DIR = WORKSPACE_DIR / "vector-memory"
ARIA_BRIDGE_DIR = ARIA_HOME / "aria-bridge"
PUBLIC_MEMORY_RELATIVE_PATHS = (Path("memory"), Path("docs"))
SAFE_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml"}
SECRET_NAME_PARTS = {
    ".env",
    "secret",
    "token",
    "key",
    "password",
    "credential",
    "private",
    "id_rsa",
    "id_ed25519",
}
MAX_PUBLIC_FILES = 25
MAX_PUBLIC_FILE_CHARS = 20_000
TRANSCRIPTS_DIR = WORKSPACE_DIR / "data" / "transcripts"
MAX_TRANSCRIPT_RESULTS = 20
MAX_TRANSCRIPT_SNIPPET_CHARS = 500
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b[A-Z0-9_-]*(?:api[_-]?key|token|secret|password|private[_-]?key)[A-Z0-9_-]*\b\s*[:=]\s*([^\s,;}]+)"
)


def _path_status(path: Path) -> dict:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
    }


def _has_secret_shaped_part(path: Path) -> bool:
    lower_name = path.name.lower()
    lower_parts = "/".join(part.lower() for part in path.parts)
    return any(part in lower_name or part in lower_parts for part in SECRET_NAME_PARTS)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_safe_public_file(path: Path, allowed_root: Path | None = None) -> bool:
    if path.is_symlink() or path.is_dir():
        return False
    if path.suffix.lower() not in SAFE_TEXT_SUFFIXES:
        return False
    if _has_secret_shaped_part(path):
        return False
    if allowed_root is not None:
        try:
            resolved_path = path.resolve(strict=True)
            resolved_root = allowed_root.resolve(strict=True)
        except OSError:
            return False
        if not _is_relative_to(resolved_path, resolved_root):
            return False
        if _has_secret_shaped_part(resolved_path):
            return False
    return True


def _iter_public_memory_files(home: Path) -> Iterable[Path]:
    for relative_root in PUBLIC_MEMORY_RELATIVE_PATHS:
        root = home / relative_root
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if _is_safe_public_file(path, root):
                yield path


def aria_workspace_paths() -> str:
    """Return key Aria/Hermes workspace paths as JSON."""
    return tool_result({
        "hermes_home": str(get_hermes_home()),
        "aria_home": str(ARIA_HOME),
        "workspace": str(WORKSPACE_DIR),
        "vector_memory": str(VECTOR_MEMORY_DIR),
        "aria_bridge": str(ARIA_BRIDGE_DIR),
    })


def aria_dashboard_status() -> str:
    """Return a compact status dashboard for Aria-specific local resources."""
    home = get_hermes_home()
    public_files = list(_iter_public_memory_files(home))[:MAX_PUBLIC_FILES]
    return tool_result({
        "paths": {
            "hermes_home": _path_status(home),
            "workspace": _path_status(WORKSPACE_DIR),
            "vector_memory": _path_status(VECTOR_MEMORY_DIR),
            "aria_bridge": _path_status(ARIA_BRIDGE_DIR),
        },
        "public_memory_file_count": len(public_files),
    })


def aria_read_public_memory() -> str:
    """Read safe public Hermes memory/docs files, excluding secrets."""
    home = get_hermes_home()
    files = []
    for path in list(_iter_public_memory_files(home))[:MAX_PUBLIC_FILES]:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            files.append({
                "relative_path": str(path.relative_to(home)),
                "error": str(exc),
            })
            continue
        truncated = len(content) > MAX_PUBLIC_FILE_CHARS
        files.append({
            "relative_path": str(path.relative_to(home)),
            "content": content[:MAX_PUBLIC_FILE_CHARS],
            "truncated": truncated,
        })
    return tool_result({"files": files, "max_files": MAX_PUBLIC_FILES})


def _redact_text(text: str) -> str:
    return _SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(0).split('=', 1)[0].split(':', 1)[0]}=[REDACTED]", text)


def _transcripts_root() -> Path:
    # Derive from WORKSPACE_DIR at call time so tests/profile overrides work.
    return WORKSPACE_DIR / "data" / "transcripts"


def _iter_transcript_files(root: Path) -> Iterable[Path]:
    if not root.exists() or not root.is_dir():
        return []
    return sorted((p for p in root.glob("*.jsonl") if p.is_file() and not p.is_symlink()), reverse=True)


def aria_transcript_search(query: str, max_results: int = MAX_TRANSCRIPT_RESULTS) -> str:
    """Search historical Aria transcript JSONL files with bounded, redacted snippets."""
    normalized_query = str(query or "").strip()
    if not normalized_query:
        return tool_result({"ok": False, "error": "empty_query", "matches": []})

    root = _transcripts_root()
    matches = []
    limit = max(1, min(int(max_results or MAX_TRANSCRIPT_RESULTS), MAX_TRANSCRIPT_RESULTS))
    needle = normalized_query.lower()
    for path in _iter_transcript_files(root):
        if len(matches) >= limit:
            break
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if len(matches) >= limit:
                break
            if needle not in line.lower():
                continue
            snippet = line[:MAX_TRANSCRIPT_SNIPPET_CHARS]
            try:
                parsed = json.loads(line)
                content = parsed.get("content") or parsed.get("text") or parsed.get("message")
                role = parsed.get("role") or parsed.get("speaker")
                if isinstance(content, str):
                    snippet = content[:MAX_TRANSCRIPT_SNIPPET_CHARS]
                match = {
                    "file": path.name,
                    "line": line_number,
                    "role": role if isinstance(role, str) else None,
                    "snippet": _redact_text(snippet),
                }
            except json.JSONDecodeError:
                match = {
                    "file": path.name,
                    "line": line_number,
                    "role": None,
                    "snippet": _redact_text(snippet),
                }
            matches.append(match)
    return tool_result({"ok": True, "query": normalized_query, "matches": matches, "max_results": limit})


ARIA_DASHBOARD_STATUS_SCHEMA = {
    "name": "aria_dashboard_status",
    "description": "Return a safe status dashboard for Aria workspace, vector memory, and bridge paths.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ARIA_WORKSPACE_PATHS_SCHEMA = {
    "name": "aria_workspace_paths",
    "description": "Return key Aria/Hermes workspace paths without exposing credentials.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ARIA_READ_PUBLIC_MEMORY_SCHEMA = {
    "name": "aria_read_public_memory",
    "description": "Read only safe public Hermes memory/docs files; secret-shaped files are excluded.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ARIA_TRANSCRIPT_SEARCH_SCHEMA = {
    "name": "aria_transcript_search",
    "description": "Search historical Aria transcript JSONL files with bounded, redacted snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Case-insensitive search text."},
            "max_results": {"type": "integer", "description": "Maximum matches to return, capped at 20."},
        },
        "required": ["query"],
    },
}

registry.register(
    name="aria_dashboard_status",
    toolset="aria_workspace",
    schema=ARIA_DASHBOARD_STATUS_SCHEMA,
    handler=lambda args, **kw: aria_dashboard_status(),
    emoji="🗂️",
)
registry.register(
    name="aria_workspace_paths",
    toolset="aria_workspace",
    schema=ARIA_WORKSPACE_PATHS_SCHEMA,
    handler=lambda args, **kw: aria_workspace_paths(),
    emoji="🗂️",
)
registry.register(
    name="aria_read_public_memory",
    toolset="aria_workspace",
    schema=ARIA_READ_PUBLIC_MEMORY_SCHEMA,
    handler=lambda args, **kw: aria_read_public_memory(),
    emoji="🧠",
)
registry.register(
    name="aria_transcript_search",
    toolset="aria_workspace",
    schema=ARIA_TRANSCRIPT_SEARCH_SCHEMA,
    handler=lambda args, **kw: aria_transcript_search(
        query=args.get("query", ""),
        max_results=args.get("max_results", MAX_TRANSCRIPT_RESULTS),
    ),
    emoji="🧾",
)
