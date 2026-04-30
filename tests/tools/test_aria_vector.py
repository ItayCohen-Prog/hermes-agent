import json
import subprocess

from tools import aria_vector
from toolsets import get_toolset


def test_vector_search_invokes_search_script_without_shell(monkeypatch, tmp_path):
    script = tmp_path / "search.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(aria_vector, "SEARCH_SCRIPT", script)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout='[{"text":"hit"}]', stderr="")

    monkeypatch.setattr(aria_vector.subprocess, "run", fake_run)

    data = json.loads(aria_vector.aria_vector_search("hello", top_k=3, filters={"type": "note"}))

    assert data["ok"] is True
    assert data["results"] == [{"text": "hit"}]
    assert calls[0][0] == [str(script), "hello", "--top-k", "3", "--filter", "type=note"]
    assert calls[0][1]["shell"] is False


def test_vector_search_validates_query_and_top_k():
    assert "error" in json.loads(aria_vector.aria_vector_search(""))
    assert "error" in json.loads(aria_vector.aria_vector_search("x", top_k=0))
    assert "error" in json.loads(aria_vector.aria_vector_search("x", top_k=101))


def test_vector_search_missing_script_returns_error(monkeypatch, tmp_path):
    monkeypatch.setattr(aria_vector, "SEARCH_SCRIPT", tmp_path / "missing.sh")

    data = json.loads(aria_vector.aria_vector_search("hello"))

    assert data["ok"] is False
    assert "search script not found" in data["error"].lower()


def test_vector_reindex_dry_run_does_not_call_subprocess(monkeypatch, tmp_path):
    script = tmp_path / "reindex.sh"
    monkeypatch.setattr(aria_vector, "REINDEX_SCRIPT", script)

    def fail_run(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("subprocess.run should not be called for dry-run")

    monkeypatch.setattr(aria_vector.subprocess, "run", fail_run)

    data = json.loads(aria_vector.aria_vector_reindex())

    assert data["ok"] is True
    assert data["dry_run"] is True
    assert data["would_run"] == [str(script)]


def test_vector_reindex_runs_only_when_explicit(monkeypatch, tmp_path):
    script = tmp_path / "reindex.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(aria_vector, "REINDEX_SCRIPT", script)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="indexed", stderr="")

    monkeypatch.setattr(aria_vector.subprocess, "run", fake_run)

    data = json.loads(aria_vector.aria_vector_reindex(dry_run=False))

    assert data["ok"] is True
    assert data["dry_run"] is False
    assert data["stdout"] == "indexed"
    assert calls[0][0] == [str(script)]
    assert calls[0][1]["shell"] is False


def test_aria_vector_toolset_exposes_tools():
    assert set(get_toolset("aria_vector")["tools"]) >= {"aria_vector_search", "aria_vector_reindex"}
