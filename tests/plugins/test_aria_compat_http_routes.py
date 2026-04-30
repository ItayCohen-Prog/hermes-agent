import json
from pathlib import Path

from plugins.aria_compat.http_routes import (
    append_cron_history_payload,
    dashboard_status_payload,
    health_payload,
    is_pc_route_authorized,
    refresh_command_payload,
)


def test_health_payload_is_stable():
    assert health_payload(sessions=2, ws_clients=1, uptime_s=7, profile="aria") == {
        "status": "ok",
        "sessions": 2,
        "ws_clients": 1,
        "uptime_s": 7,
        "runtime": "hermes",
        "profile": "aria",
    }


def test_cron_history_append_payload_normalizes_entry():
    payload = append_cron_history_payload({"job": "backup", "ok": True})

    assert payload["ok"] is True
    assert payload["entry"] == {"job": "backup", "ok": True}


def test_dashboard_status_reads_default_shape_from_status_json(tmp_path):
    status_path = tmp_path / "status.json"
    status_path.write_text(json.dumps({"state": "ready"}), encoding="utf-8")

    assert dashboard_status_payload(status_path=status_path) == {"ok": True, "status": {"state": "ready"}}


def test_dashboard_status_missing_file_returns_absent_payload(tmp_path):
    assert dashboard_status_payload(status_path=tmp_path / "missing.json") == {
        "ok": False,
        "error": "status_not_found",
        "status": None,
    }


def test_refresh_command_is_guarded_to_fixed_update_script(tmp_path):
    missing = refresh_command_payload(workspace=tmp_path)
    assert missing["ok"] is False
    assert missing["error"] == "update_script_not_found"

    script = tmp_path / "update.py"
    script.write_text("print('update')\n", encoding="utf-8")

    present = refresh_command_payload(workspace=tmp_path)
    assert present["ok"] is True
    assert present["command"] == ["python", str(script)]


def test_pc_route_auth_requires_configured_token():
    assert is_pc_route_authorized(None, None) is False
    assert is_pc_route_authorized("", "anything") is False
    assert is_pc_route_authorized("secret", "secret") is True
    assert is_pc_route_authorized("secret", "wrong") is False
