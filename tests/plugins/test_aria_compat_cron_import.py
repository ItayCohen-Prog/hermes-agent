import json

from plugins.aria_compat.cron_import import (
    build_cron_import_plan,
    cron_import_summary,
    read_cron_history,
)


def test_build_cron_import_plan_is_dry_run_and_profile_scoped():
    plan = build_cron_import_plan([{"name": "vector-reindex", "schedule": "0 */3 * * *", "risk": "low"}])

    assert plan == [
        {
            "name": "aria-vector-reindex",
            "source_name": "vector-reindex",
            "schedule": "0 */3 * * *",
            "prompt": plan[0]["prompt"],
            "profile": "aria",
            "dry_run": True,
            "risk": "low",
        }
    ]
    assert "vector-reindex" in plan[0]["prompt"]
    assert "do not expose secrets" in plan[0]["prompt"]


def test_cron_import_summary_makes_side_effect_boundary_explicit():
    summary = cron_import_summary(
        [
            {
                "name": "aria-health-check",
                "schedule": "15 4 * * *",
                "risk": "low",
            }
        ]
    )

    assert "Aria cron import dry-run:" in summary
    assert "aria-health-check" in summary
    assert "No Hermes cron jobs were created" in summary


def test_read_cron_history_bounds_entries(tmp_path):
    history = tmp_path / "cron-history.json"
    history.write_text(json.dumps([{"i": 1}, {"i": 2}, {"i": 3}]), encoding="utf-8")

    result = read_cron_history(history, limit=2)

    assert result == {"ok": True, "entries": [{"i": 2}, {"i": 3}]}


def test_read_cron_history_handles_missing_file(tmp_path):
    result = read_cron_history(tmp_path / "missing.json")

    assert result["ok"] is False
    assert result["error"] == "history_not_found"
    assert result["entries"] == []
