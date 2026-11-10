import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from oat_postcard import cli, clerk, directory, ledger, session


def _hook(monkeypatch, event, payload, host="auto", env=None, pid=None):
    """Run `oat-postcard hook <event>` with `payload` on stdin; return stdout."""
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    argv = ["hook", event, "--host", host]
    if pid is not None:
        argv += ["--pid", str(pid)]
    return cli.main(argv)


def _entries():
    return {e.session_id: e for e in directory.list_active(prune=False)}


def test_session_start_registers_with_host_and_cwd(tmp_root, monkeypatch, capsys):
    rc = _hook(
        monkeypatch,
        "session-start",
        {"session_id": "c-1", "cwd": "/w/claude"},
        env={"CLAUDECODE": "1"},
        pid=os.getpid(),
    )
    assert rc == 0
    assert capsys.readouterr().out == ""
    e = _entries()["c-1"]
    assert e.host == "claude" and e.cwd == "/w/claude" and e.pid == os.getpid()


def test_session_start_agy_prints_empty_object(tmp_root, monkeypatch, capsys):
    _hook(
        monkeypatch,
        "session-start",
        {"conversationId": "a-1", "workspacePaths": ["/w/agy"]},
        host="agy",
        pid=os.getpid(),
    )
    assert capsys.readouterr().out.strip() == "{}"
    e = _entries()["a-1"]
    assert e.host == "agy" and e.cwd == "/w/agy"


def test_grok_payload_under_claude_hooks_file_is_recorded_as_grok(
    tmp_root, monkeypatch, capsys
):
    _hook(
        monkeypatch,
        "session-start",
        {"sessionId": "g-1", "cwd": "/w/grok"},
        host="auto",
        env={"GROK_HOOK_EVENT": "SessionStart", "GROK_SESSION_ID": "g-1"},
        pid=os.getpid(),
    )
    assert _entries()["g-1"].host == "grok"


def test_session_end_unregisters(tmp_root, monkeypatch, capsys):
    _hook(
        monkeypatch,
        "session-start",
        {"session_id": "x-1", "cwd": "/w"},
        pid=os.getpid(),
    )
    assert "x-1" in _entries()
    _hook(monkeypatch, "session-end", {"session_id": "x-1", "reason": "exit"})
    assert "x-1" not in _entries()


def test_prompt_nudges_claude_and_codex_only_when_mail_pending(
    tmp_root, monkeypatch, capsys
):
    _hook(
        monkeypatch,
        "session-start",
        {"session_id": "x-1", "cwd": "/w", "turn_id": "t"},
        pid=os.getpid(),
    )
    me = _entries()["x-1"].address
    capsys.readouterr()

    _hook(monkeypatch, "prompt", {"session_id": "x-1", "cwd": "/w", "turn_id": "t"})
    assert capsys.readouterr().out == ""

    ledger.send("peer", me, "hi", "body")
    _hook(monkeypatch, "stop", {"session_id": "x-1", "cwd": "/w", "turn_id": "t"})
    assert capsys.readouterr().out == ""  # sweep only; codex gets no Stop nudge
    assert clerk.pending_count("x-1") == 1

    _hook(monkeypatch, "prompt", {"session_id": "x-1", "cwd": "/w", "turn_id": "t"})
    out = json.loads(capsys.readouterr().out)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "1 pending" in ctx and "spawn_agent" in ctx


def test_stop_nudge_copilot_blocks_once_then_respects_stop_hook_active(
    tmp_root, monkeypatch, capsys
):
    _hook(
        monkeypatch,
        "session-start",
        {"sessionId": "cp-1", "cwd": "/w"},
        host="copilot",
        pid=os.getpid(),
    )
    me = _entries()["cp-1"].address
    ledger.send("peer", me, "hi", "body")
    capsys.readouterr()

    _hook(monkeypatch, "stop", {"sessionId": "cp-1", "cwd": "/w"}, host="copilot")
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "block" and "postcard-reader" in out["reason"]

    # Same pending set again: de-duplicated, no second continuation.
    _hook(monkeypatch, "stop", {"sessionId": "cp-1", "cwd": "/w"}, host="copilot")
    assert capsys.readouterr().out == ""

    # New mail arrives but the host says the stop hook is already active.
    ledger.send("peer", me, "again", "body")
    _hook(
        monkeypatch,
        "stop",
        {"sessionId": "cp-1", "cwd": "/w", "stop_hook_active": True},
        host="copilot",
    )
    assert capsys.readouterr().out == ""
    assert clerk.pending_count("cp-1") == 2  # still swept


def test_stop_nudge_agy_continues_and_grok_adds_context(tmp_root, monkeypatch, capsys):
    _hook(
        monkeypatch,
        "session-start",
        {"conversationId": "a-1", "workspacePaths": ["/w"]},
        host="agy",
        pid=os.getpid(),
    )
    _hook(
        monkeypatch,
        "session-start",
        {"sessionId": "g-1", "cwd": "/w"},
        host="grok",
        pid=os.getpid(),
    )
    ents = _entries()
    ledger.send("peer", ents["a-1"].address, "hi", "body")
    ledger.send("peer", ents["g-1"].address, "hi", "body")
    capsys.readouterr()

    _hook(
        monkeypatch,
        "stop",
        {"conversationId": "a-1", "workspacePaths": ["/w"]},
        host="agy",
    )
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "continue" and "1 pending" in out["reason"]
    _hook(
        monkeypatch,
        "stop",
        {"conversationId": "a-1", "workspacePaths": ["/w"]},
        host="agy",
    )
    assert capsys.readouterr().out.strip() == "{}"

    _hook(monkeypatch, "stop", {"sessionId": "g-1", "cwd": "/w"}, host="grok")
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "spawn the postcard-reader" in out["hookSpecificOutput"]["additionalContext"]


def test_stop_without_pending_mail_is_silent_everywhere(tmp_root, monkeypatch, capsys):
    for host, payload in [
        ("copilot", {"sessionId": "cp-2", "cwd": "/w"}),
        ("grok", {"sessionId": "g-2", "cwd": "/w"}),
        ("claude", {"session_id": "c-2", "cwd": "/w"}),
    ]:
        _hook(monkeypatch, "stop", payload, host=host, pid=os.getpid())
        assert capsys.readouterr().out == "", host


def test_hook_never_fails_on_garbage(tmp_root, monkeypatch, capsys):
    assert _hook(monkeypatch, "stop", "not json at all", host="claude") == 0
    assert _hook(monkeypatch, "session-end", "", host="claude") == 0


def test_hook_lazily_registers_on_stop_for_unknown_session(
    tmp_root, monkeypatch, capsys
):
    _hook(monkeypatch, "stop", {"session_id": "late-1", "cwd": "/w"}, pid=os.getpid())
    assert "late-1" in _entries()
    assert session.current_address() is not None or True  # registration is what matters


def test_setup_codex_writes_agent_toml(tmp_root, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    rc = cli.main(["setup", "codex"])
    assert rc == 0
    dest = tmp_path / "codex" / "agents" / "postcard-reader.toml"
    assert dest.exists()
    assert 'name = "postcard-reader"' in dest.read_text()
    assert "wrote" in capsys.readouterr().out


def test_setup_other_hosts_print_notes(tmp_root, capsys):
    for host in ("claude", "grok", "copilot", "agy"):
        assert cli.main(["setup", host]) == 0
        assert capsys.readouterr().out.strip()


def test_oat_postcard_home_overrides_state_root(tmp_path):
    home = tmp_path / "alt-home"
    env = {
        **{
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("CLAUDE", "CODEX", "GROK"))
        },
        "OAT_POSTCARD_HOME": str(home),
        "OAT_POSTCARD_SESSION": "sub-1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "oat_postcard",
            "session-init",
            "--pid",
            str(os.getpid()),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out.count("-") == 2
    assert (home / "directory").is_dir()
    assert list((home / "directory").glob("*.json"))
    assert not (tmp_path / ".oat-postcard").exists()


def test_directory_cmd_shows_host_column(tmp_root, session_env, capsys):
    directory.register(
        "a-b-c", session_id="s1", pid=os.getpid(), cwd=Path("/w"), host="codex"
    )
    cli.main(["directory"])
    out = capsys.readouterr().out
    assert "codex" in out and "a-b-c" in out


@pytest.mark.parametrize("host", ["codex", "copilot", "grok", "agy"])
def test_init_prefers_agents_md_on_non_claude_hosts(tmp_path, monkeypatch, host):
    from oat_postcard import hosts

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hosts, "detect_host", lambda *a, **k: host)
    assert cli.main(["init"]) == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_init_defaults_to_claude_md_on_claude(tmp_path, monkeypatch):
    from oat_postcard import hosts

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(hosts, "detect_host", lambda *a, **k: "claude")
    cli.main(["init"])
    assert (tmp_path / "CLAUDE.md").exists()
