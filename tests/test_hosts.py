import json
from pathlib import Path

import pytest

from oat_postcard import hosts

# Representative stdin payloads, per host, as documented by each CLI.
CLAUDE_PAYLOAD = {
    "session_id": "c-1",
    "cwd": "/w/claude",
    "transcript_path": "/home/u/.claude/projects/x/abc.jsonl",
    "hook_event_name": "SessionStart",
}
CODEX_PAYLOAD = {
    "session_id": "x-1",
    "cwd": "/w/codex",
    "transcript_path": "/home/u/.codex/sessions/2026/11/10/rollout-2026-11-10T00-00-00-abc.jsonl",
    "hook_event_name": "SessionStart",
    "turn_id": "t-1",
}
COPILOT_PAYLOAD = {"sessionId": "cp-1", "cwd": "/w/copilot", "timestamp": 1}
GROK_PAYLOAD = {"sessionId": "g-1", "cwd": "/w/grok", "hookEventName": "stop"}
AGY_PAYLOAD = {
    "conversationId": "a-1",
    "workspacePaths": ["/w/agy", "/w/agy2"],
    "transcriptPath": "/x/transcript_full.jsonl",
}


def test_session_id_from_env_prefers_manual_override():
    env = {"OAT_POSTCARD_SESSION": "manual", "CLAUDE_SESSION_ID": "claude"}
    assert hosts.session_id_from_env(env) == "manual"


@pytest.mark.parametrize(
    "env,expected",
    [
        ({"CLAUDE_SESSION_ID": "a"}, "a"),
        ({"CODEX_SESSION_ID": "root", "CODEX_THREAD_ID": "sub"}, "root"),
        ({"CODEX_THREAD_ID": "sub"}, "sub"),
        ({"GROK_SESSION_ID": "g"}, "g"),
        ({}, None),
    ],
)
def test_session_id_from_env_per_host(env, expected):
    assert hosts.session_id_from_env(env) == expected


def test_detect_host_explicit_hint_wins():
    assert hosts.detect_host(env={"GROK_HOOK_EVENT": "Stop"}, hint="claude") == "claude"


def test_detect_host_rejects_unknown_hint():
    with pytest.raises(ValueError):
        hosts.detect_host(hint="emacs")


@pytest.mark.parametrize(
    "env,payload,expected",
    [
        ({"GROK_HOOK_EVENT": "SessionStart"}, CLAUDE_PAYLOAD, "grok"),
        ({"GROK_SESSION_ID": "g"}, {}, "grok"),
        ({"COPILOT_HOOK_DEPTH": "1"}, {}, "copilot"),
        ({"CODEX_SESSION_ID": "x"}, {}, "codex"),
        ({}, AGY_PAYLOAD, "agy"),
        ({}, CODEX_PAYLOAD, "codex"),
        ({}, COPILOT_PAYLOAD, "copilot"),
        ({"CLAUDECODE": "1"}, {}, "claude"),
        ({}, CLAUDE_PAYLOAD, "claude"),
        ({}, {}, "shell"),
    ],
)
def test_detect_host(env, payload, expected):
    assert hosts.detect_host(env=env, payload=payload) == expected


@pytest.mark.parametrize(
    "payload,host,sid,cwd",
    [
        (CLAUDE_PAYLOAD, "claude", "c-1", "/w/claude"),
        (CODEX_PAYLOAD, "codex", "x-1", "/w/codex"),
        (COPILOT_PAYLOAD, "copilot", "cp-1", "/w/copilot"),
        (AGY_PAYLOAD, "agy", "a-1", "/w/agy"),
    ],
)
def test_parse_hook_input_normalizes(payload, host, sid, cwd):
    hi = hosts.parse_hook_input(json.dumps(payload), env={})
    assert hi.host == host
    assert hi.session_id == sid
    assert hi.cwd == cwd


def test_parse_hook_input_grok_under_claude_hooks_file():
    hi = hosts.parse_hook_input(
        json.dumps(GROK_PAYLOAD),
        host_hint="auto",
        env={"GROK_HOOK_EVENT": "Stop", "CLAUDE_PLUGIN_ROOT": "/p"},
    )
    assert hi.host == "grok"
    assert hi.session_id == "g-1"


def test_parse_hook_input_tolerates_garbage_and_empty():
    assert hosts.parse_hook_input("not json", env={}).session_id is None
    assert hosts.parse_hook_input("", env={}).host == "shell"
    assert hosts.parse_hook_input("[1,2]", env={}).raw == {}


def test_stop_hook_active_accepts_both_spellings():
    assert hosts.parse_hook_input('{"stop_hook_active": true}', env={}).stop_hook_active
    assert hosts.parse_hook_input('{"stopHookActive": true}', env={}).stop_hook_active
    assert not hosts.parse_hook_input("{}", env={}).stop_hook_active


def test_pending_notice_mentions_fallback_cli_for_non_claude_hosts():
    claude = hosts.pending_notice("claude", 2)
    codex = hosts.pending_notice("codex", 2, cli="/p/bin/oat-postcard")
    assert "2 pending" in claude
    assert "clerk-pending" not in claude
    assert "/p/bin/oat-postcard clerk-pending --json" in codex
    assert "postcard:postcard-reader" in claude


def test_format_nudge_dialects():
    msg = "m"
    claude = json.loads(hosts.format_nudge("claude", "prompt", msg))
    assert claude["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert claude["hookSpecificOutput"]["additionalContext"] == msg
    codex = json.loads(hosts.format_nudge("codex", "prompt", msg))
    assert codex == claude
    grok = json.loads(hosts.format_nudge("grok", "stop", msg))
    assert grok["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert json.loads(hosts.format_nudge("copilot", "stop", msg)) == {
        "decision": "block",
        "reason": msg,
    }
    assert json.loads(hosts.format_nudge("agy", "stop", msg)) == {
        "decision": "continue",
        "reason": msg,
    }


@pytest.mark.parametrize(
    "host,event",
    [("grok", "prompt"), ("copilot", "prompt"), ("claude", "stop"), ("codex", "stop")],
)
def test_format_nudge_returns_none_where_host_cannot_carry_context(host, event):
    assert hosts.format_nudge(host, event, "m") is None


def test_empty_output_only_agy_requires_json_object():
    assert hosts.empty_output("agy") == "{}"
    assert hosts.empty_output("claude") is None


def test_should_nudge_once_dedupes_same_pending_set(tmp_path):
    pending = tmp_path / "pending"
    pending.mkdir()
    (pending / "a.json").write_text("{}")
    assert hosts.should_nudge_once(pending) is True
    assert hosts.should_nudge_once(pending) is False
    (pending / "b.json").write_text("{}")
    assert hosts.should_nudge_once(pending) is True
    assert hosts.should_nudge_once(pending) is False


def test_split_frontmatter_and_codex_toml():
    md = '---\nname: postcard-reader\ndescription: Triage "mail".\ntools: Bash\n---\n\nBody line 1\n\n## Section\n'
    meta, body = hosts.split_frontmatter(md)
    assert meta == {
        "name": "postcard-reader",
        "description": 'Triage "mail".',
        "tools": "Bash",
    }
    assert body.startswith("Body line 1")
    toml_text = hosts.codex_agent_toml(md)
    assert 'name = "postcard-reader"' in toml_text
    assert 'description = "Triage \\"mail\\"."' in toml_text
    assert "developer_instructions = '''\nBody line 1" in toml_text
    assert toml_text.rstrip().endswith("'''")


def test_split_frontmatter_without_frontmatter_returns_text():
    meta, body = hosts.split_frontmatter("plain text")
    assert meta == {} and body == "plain text"


def test_plugin_root_finds_this_checkout():
    root = hosts.plugin_root()
    assert root is not None
    assert (root / "agents" / "postcard-reader.md").exists()
    assert hosts.cli_path() == str(Path(root) / "bin" / "oat-postcard")


def test_real_agent_file_renders_as_valid_toml():
    root = hosts.plugin_root()
    assert root is not None
    text = hosts.codex_agent_toml((root / "agents" / "postcard-reader.md").read_text())
    tomllib = pytest.importorskip("tomllib")
    data = tomllib.loads(text)
    assert data["name"] == "postcard-reader"
    assert "clerk-pending --json" in data["developer_instructions"]
