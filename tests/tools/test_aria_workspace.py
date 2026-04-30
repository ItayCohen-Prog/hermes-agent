import json
from pathlib import Path

from tools import aria_workspace
from toolsets import get_toolset


def test_workspace_paths_returns_expected_safe_locations(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setattr(aria_workspace, "get_hermes_home", lambda: hermes_home)
    monkeypatch.setattr(aria_workspace, "ARIA_HOME", tmp_path / "aria")
    monkeypatch.setattr(aria_workspace, "WORKSPACE_DIR", tmp_path / "workspace")
    monkeypatch.setattr(aria_workspace, "VECTOR_MEMORY_DIR", tmp_path / "workspace" / "vector-memory")
    monkeypatch.setattr(aria_workspace, "ARIA_BRIDGE_DIR", tmp_path / "aria-bridge")

    data = json.loads(aria_workspace.aria_workspace_paths())

    assert data["hermes_home"] == str(hermes_home)
    assert data["workspace"] == str(tmp_path / "workspace")
    assert data["vector_memory"] == str(tmp_path / "workspace" / "vector-memory")
    assert data["aria_bridge"] == str(tmp_path / "aria-bridge")
    assert "private_key" not in json.dumps(data).lower()


def test_dashboard_status_reports_existence_without_shelling(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    workspace = tmp_path / "workspace"
    vector = workspace / "vector-memory"
    bridge = tmp_path / "aria-bridge"
    for path in (hermes_home, workspace, vector):
        path.mkdir(parents=True)

    monkeypatch.setattr(aria_workspace, "get_hermes_home", lambda: hermes_home)
    monkeypatch.setattr(aria_workspace, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(aria_workspace, "VECTOR_MEMORY_DIR", vector)
    monkeypatch.setattr(aria_workspace, "ARIA_BRIDGE_DIR", bridge)

    data = json.loads(aria_workspace.aria_dashboard_status())

    assert data["paths"]["hermes_home"]["exists"] is True
    assert data["paths"]["workspace"]["exists"] is True
    assert data["paths"]["vector_memory"]["exists"] is True
    assert data["paths"]["aria_bridge"]["exists"] is False


def test_read_public_memory_only_reads_safe_text_files(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    (hermes_home / "memory").mkdir(parents=True)
    (hermes_home / "memory" / "profile.md").write_text("public profile", encoding="utf-8")
    (hermes_home / "memory" / "token.env").write_text("SECRET=bad", encoding="utf-8")
    (hermes_home / ".env").write_text("API_KEY=bad", encoding="utf-8")

    monkeypatch.setattr(aria_workspace, "get_hermes_home", lambda: hermes_home)
    monkeypatch.setattr(aria_workspace, "PUBLIC_MEMORY_RELATIVE_PATHS", (Path("memory"), Path("docs")))

    data = json.loads(aria_workspace.aria_read_public_memory())

    assert [item["relative_path"] for item in data["files"]] == ["memory/profile.md"]
    assert data["files"][0]["content"] == "public profile"
    assert "SECRET" not in json.dumps(data)


def test_read_public_memory_rejects_symlinks(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("SECRET=bad", encoding="utf-8")
    (hermes_home / "memory").mkdir(parents=True)
    (hermes_home / "memory" / "profile.md").symlink_to(outside)

    monkeypatch.setattr(aria_workspace, "get_hermes_home", lambda: hermes_home)
    monkeypatch.setattr(aria_workspace, "PUBLIC_MEMORY_RELATIVE_PATHS", (Path("memory"),))

    data = json.loads(aria_workspace.aria_read_public_memory())

    assert data["files"] == []
    assert "SECRET" not in json.dumps(data)


def test_transcript_search_finds_bounded_redacted_matches(monkeypatch, tmp_path):
    transcripts = tmp_path / "workspace" / "data" / "transcripts"
    transcripts.mkdir(parents=True)
    (transcripts / "session.jsonl").write_text(
        '{"role":"user","content":"hello calendar SECRET_TOKEN=abc123"}\n'
        '{"role":"assistant","content":"calendar summary ready"}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(aria_workspace, "WORKSPACE_DIR", tmp_path / "workspace")

    data = json.loads(aria_workspace.aria_transcript_search("calendar", max_results=5))

    assert data["query"] == "calendar"
    assert len(data["matches"]) == 2
    dumped = json.dumps(data)
    assert "abc123" not in dumped
    assert "[REDACTED]" in dumped


def test_transcript_search_rejects_empty_query():
    data = json.loads(aria_workspace.aria_transcript_search(""))

    assert data["ok"] is False
    assert data["error"] == "empty_query"


def test_aria_workspace_toolset_exposes_tools():
    assert set(get_toolset("aria_workspace")["tools"]) >= {
        "aria_dashboard_status",
        "aria_workspace_paths",
        "aria_read_public_memory",
        "aria_transcript_search",
    }
