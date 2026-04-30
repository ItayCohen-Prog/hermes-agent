import json
from types import SimpleNamespace

from plugins.aria_compat.discord_routing import (
    apply_routing_to_event,
    category_for_channel,
    categories_summary,
    load_categories,
    sync_categories_plan,
)


def test_load_categories_normalizes_bridge_config(tmp_path):
    config = tmp_path / "bridge-categories.json"
    config.write_text(
        json.dumps(
            {
                "categories": [
                    {
                        "name": "Bram HQ",
                        "channelPrefix": "bram",
                        "channelCount": "3",
                        "context": "Prefer concise Discord replies.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    categories = load_categories(config)

    assert len(categories) == 1
    assert categories[0].name == "Bram HQ"
    assert categories[0].channel_prefix == "bram"
    assert categories[0].channel_count == 3
    assert categories[0].skill_name == "aria-category-bram-hq"


def test_missing_category_config_falls_back_to_general(tmp_path):
    categories = load_categories(tmp_path / "missing.json")

    assert categories[0].name == "General"
    assert categories[0].channel_prefix == "threads"


def test_category_for_channel_matches_prefix():
    categories = load_categories_from_dicts(
        [
            {"name": "General", "channelPrefix": "threads"},
            {"name": "Bram", "channelPrefix": "bram"},
        ]
    )

    assert category_for_channel("bram-ops", categories).name == "Bram"
    assert category_for_channel("unknown", categories).name == "General"


def test_apply_routing_to_event_sets_skill_and_prompt_without_rewriting_text():
    categories = load_categories_from_dicts(
        [{"name": "Bram HQ", "channelPrefix": "bram", "context": "Bram context"}]
    )
    event = SimpleNamespace(
        text="hello",
        source=SimpleNamespace(chat_name="bram-main"),
        auto_skill=None,
        channel_prompt=None,
    )

    result = apply_routing_to_event(event, categories)

    assert result["action"] == "allow"
    assert result["aria_routing"]["category"] == "Bram HQ"
    assert event.text == "hello"
    assert event.auto_skill == "aria-category-bram-hq"
    assert event.channel_prompt == "Bram context"


def test_categories_summary_and_sync_plan_are_non_destructive(tmp_path):
    config = tmp_path / "bridge-categories.json"
    config.write_text(json.dumps({"categories": [{"name": "General"}]}), encoding="utf-8")

    assert "Aria categories:" in categories_summary(config)
    plan = sync_categories_plan(config)
    assert plan["dry_run"] is True
    assert "no Discord channels" in plan["message"]


def load_categories_from_dicts(items):
    from plugins.aria_compat.discord_routing import normalize_category

    return [normalize_category(item) for item in items]
