import json
import subprocess
import sys

from tools import aria_pc
from toolsets import get_toolset


def test_pc_status_reports_script_presence(monkeypatch, tmp_path):
    script = tmp_path / "pc_access.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(aria_pc, "PC_ACCESS_SCRIPT", script)

    data = json.loads(aria_pc.aria_pc_status())

    assert data["script_exists"] is True
    assert data["script"] == str(script)
    assert "key" not in json.dumps(data).lower()


def test_pc_ensure_wraps_pc_access_without_shell(monkeypatch, tmp_path):
    script = tmp_path / "pc_access.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(aria_pc, "PC_ACCESS_SCRIPT", script)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}', stderr="")

    monkeypatch.setattr(aria_pc.subprocess, "run", fake_run)

    data = json.loads(aria_pc.aria_pc_ensure())

    assert data["ok"] is True
    assert data["result"] == {"ok": True}
    assert calls[0][0] == [sys.executable, str(script), "ensure"]
    assert calls[0][1]["shell"] is False


def test_pc_ssh_command_rejects_empty_command(monkeypatch, tmp_path):
    monkeypatch.setattr(aria_pc, "PC_ACCESS_SCRIPT", tmp_path / "pc_access.py")

    data = json.loads(aria_pc.aria_pc_ssh_command(""))

    assert data["ok"] is False
    assert "command" in data["error"].lower()


def test_pc_ssh_command_redacts_key_material(monkeypatch, tmp_path):
    script = tmp_path / "pc_access.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(aria_pc, "PC_ACCESS_SCRIPT", script)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="-----BEGIN OPENSSH PRIVATE KEY-----\nsecret\n-----END OPENSSH PRIVATE KEY-----\ndone",
            stderr="password=supersecret",
        )

    monkeypatch.setattr(aria_pc.subprocess, "run", fake_run)

    data = json.loads(aria_pc.aria_pc_ssh_command("uptime"))
    text = json.dumps(data)

    assert data["ok"] is True
    assert data["result"] == "[REDACTED PRIVATE KEY]\ndone"
    assert "BEGIN OPENSSH PRIVATE KEY" not in text
    assert "supersecret" not in text
    assert "[REDACTED" in text


def test_pc_ssh_command_uses_pc_access_separator(monkeypatch, tmp_path):
    script = tmp_path / "pc_access.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(aria_pc, "PC_ACCESS_SCRIPT", script)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}', stderr="")

    monkeypatch.setattr(aria_pc.subprocess, "run", fake_run)

    json.loads(aria_pc.aria_pc_ssh_command("powershell -NoProfile -Command Get-Location"))

    assert calls[0] == [
        sys.executable,
        str(script),
        "ssh",
        "--",
        "powershell -NoProfile -Command Get-Location",
    ]


def test_pc_json_output_redacts_secret_fields():
    parsed = aria_pc._parse_json_or_text(
        '{"ok": true, "token": "SENSITIVE_SENTINEL", "private_key_path": "/home/aria/.ssh/id_ed25519", "nested": {"password": "bad"}}'
    )

    text = json.dumps(parsed)
    assert "SENSITIVE_SENTINEL" not in text
    assert "/home/aria/.ssh/id_ed25519" not in text
    assert "bad" not in text
    assert parsed["ok"] is True


def test_pc_missing_script_returns_error(monkeypatch, tmp_path):
    monkeypatch.setattr(aria_pc, "PC_ACCESS_SCRIPT", tmp_path / "missing.py")

    data = json.loads(aria_pc.aria_pc_ensure())

    assert data["ok"] is False
    assert "pc access script not found" in data["error"].lower()


def test_aria_pc_toolset_exposes_tools():
    assert set(get_toolset("aria_pc")["tools"]) >= {
        "aria_pc_status",
        "aria_pc_ensure",
        "aria_pc_ssh_command",
    }
