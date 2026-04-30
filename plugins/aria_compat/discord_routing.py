"""Discord/channel routing helpers for the Aria compatibility plugin.

The live Aria bridge keeps a small category config in the workspace.  These
helpers intentionally avoid Discord APIs: they normalize the config, match
incoming gateway session sources to Aria categories, and return safe metadata
that Hermes gateway hooks can attach to events.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

DEFAULT_CATEGORY_CONFIG = Path("/home/aria/workspace/memory/bridge-categories.json")
DEFAULT_CATEGORY = "General"


@dataclass(frozen=True)
class AriaCategory:
    """Normalized Aria Discord category routing entry."""

    name: str
    channel_prefix: str = "threads"
    channel_count: int = 5
    context: str = ""

    @property
    def skill_name(self) -> str:
        normalized = "-".join(self.name.lower().split()) or DEFAULT_CATEGORY.lower()
        return f"aria-category-{normalized}"


def _coerce_count(value: object) -> int:
    try:
        count = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1
    return max(1, count)


def normalize_category(raw: Mapping[str, Any] | None) -> AriaCategory:
    raw = raw or {}
    name = str(raw.get("name") or DEFAULT_CATEGORY).strip() or DEFAULT_CATEGORY
    prefix = str(raw.get("channelPrefix") or raw.get("channel_prefix") or "threads").strip() or "threads"
    context = str(raw.get("context") or "")
    return AriaCategory(
        name=name,
        channel_prefix=prefix,
        channel_count=_coerce_count(raw.get("channelCount") or raw.get("channel_count") or 1),
        context=context,
    )


def load_categories(config_path: str | Path = DEFAULT_CATEGORY_CONFIG) -> list[AriaCategory]:
    """Load normalized category routing config.

    Missing or invalid config falls back to the historical General/threads
    default instead of raising during gateway startup.
    """

    path = Path(config_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [normalize_category({})]

    raw_categories = data.get("categories") if isinstance(data, Mapping) else None
    if not isinstance(raw_categories, list) or not raw_categories:
        return [normalize_category({})]
    return [normalize_category(c if isinstance(c, Mapping) else {}) for c in raw_categories]


def category_for_channel(
    chat_name: str | None,
    categories: list[AriaCategory] | None = None,
) -> AriaCategory:
    """Return the first category whose prefix matches a Discord channel name."""

    categories = categories or [normalize_category({})]
    channel = (chat_name or "").strip().lower()
    for category in categories:
        prefix = category.channel_prefix.lower()
        if channel == prefix or channel.startswith(f"{prefix}-") or channel.startswith(prefix):
            return category
    return categories[0]


def routing_context_for_source(
    source: Any,
    categories: list[AriaCategory] | None = None,
) -> dict[str, Any]:
    """Build Aria routing metadata for a gateway SessionSource-like object."""

    chat_name = getattr(source, "chat_name", None)
    if chat_name is None:
        chat_name = getattr(source, "chat_id", None)
    category = category_for_channel(chat_name, categories)
    return {
        "category": category.name,
        "channel_prefix": category.channel_prefix,
        "skill": category.skill_name,
        "context": category.context,
    }


def apply_routing_to_event(event: Any, categories: list[AriaCategory] | None = None) -> dict[str, Any]:
    """Attach non-destructive Aria routing hints to a MessageEvent-like object.

    The hook never rewrites text or blocks messages; it only fills
    ``auto_skill``/``channel_prompt`` when empty and returns a hook result for
    diagnostics/tests.
    """

    routing = routing_context_for_source(getattr(event, "source", None), categories)
    skill = routing["skill"]
    context = routing["context"]
    if getattr(event, "auto_skill", None) in (None, ""):
        try:
            event.auto_skill = skill
        except Exception:
            pass
    if context and getattr(event, "channel_prompt", None) in (None, ""):
        try:
            event.channel_prompt = context
        except Exception:
            pass
    return {"action": "allow", "aria_routing": routing}


def categories_summary(config_path: str | Path = DEFAULT_CATEGORY_CONFIG) -> str:
    """Human-readable `/categories` compatibility output."""

    categories = load_categories(config_path)
    lines = ["Aria categories:"]
    for c in categories:
        lines.append(
            f"- {c.name}: prefix={c.channel_prefix!r}, channels={c.channel_count}, skill={c.skill_name}"
        )
    return "\n".join(lines)


def sync_categories_plan(config_path: str | Path = DEFAULT_CATEGORY_CONFIG) -> dict[str, Any]:
    """Dry-run plan for `/sync_categories`.

    Real Discord mutations stay out of the plugin until cutover.  This preserves
    command parity while making the side-effect boundary explicit.
    """

    categories = load_categories(config_path)
    return {
        "ok": True,
        "dry_run": True,
        "categories": [
            {
                "name": c.name,
                "channel_prefix": c.channel_prefix,
                "channel_count": c.channel_count,
                "skill": c.skill_name,
            }
            for c in categories
        ],
        "message": "Dry-run only: no Discord channels were created, renamed, or deleted.",
    }
