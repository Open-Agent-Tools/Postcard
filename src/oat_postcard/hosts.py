"""Host adapters: which agent CLI is running us, and how to talk to its hooks.

Postcard's core (ledger, directory, clerk) is host-agnostic. Everything that
differs between Claude Code, Codex, Copilot CLI, Grok Build and Antigravity
lives here: how to detect the host, which env var carries its session id,
how to read its hook payload, and what JSON its hooks expect back.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

CLAUDE = "claude"
CODEX = "codex"
COPILOT = "copilot"
GROK = "grok"
AGY = "agy"
SHELL = "shell"
HOSTS = (CLAUDE, CODEX, COPILOT, GROK, AGY, SHELL)
AUTO = "auto"

HOST_LABELS = {
    CLAUDE: "Claude Code",
    CODEX: "Codex CLI",
    COPILOT: "GitHub Copilot CLI",
    GROK: "Grok Build",
    AGY: "Antigravity CLI",
    SHELL: "shell",
}

# Env vars that carry the host's session id into shell commands the agent
# runs. Order matters: the manual override wins, then each host's own var.
# Codex exposes both; CODEX_SESSION_ID is the root thread (stable across
# subagents) so it is preferred over CODEX_THREAD_ID.
SESSION_ENV_VARS: tuple[tuple[str, Optional[str]], ...] = (
    ("OAT_POSTCARD_SESSION", None),
    ("CLAUDE_SESSION_ID", CLAUDE),
    ("CODEX_SESSION_ID", CODEX),
    ("CODEX_THREAD_ID", CODEX),
    ("GROK_SESSION_ID", GROK),
)

# Normalized hook events. Each host maps its own event names onto these.
EV_SESSION_START = "session-start"
EV_SESSION_END = "session-end"
EV_STOP = "stop"
EV_PROMPT = "prompt"
EVENTS = (EV_SESSION_START, EV_SESSION_END, EV_STOP, EV_PROMPT)

# Hosts whose per-prompt hook cannot inject context, so the "pending mail"
# nudge is delivered from the turn-end hook as a continuation instead.
STOP_NUDGE_HOSTS = (GROK, COPILOT, AGY)


def session_id_from_env(env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    env = os.environ if env is None else env
    for var, _host in SESSION_ENV_VARS:
        sid = env.get(var)
        if sid:
            return sid
    return None


def detect_host(
    env: Optional[Mapping[str, str]] = None,
    payload: Optional[Mapping[str, Any]] = None,
    hint: Optional[str] = None,
) -> str:
    """Best-effort host detection.

    ``hint`` is an explicit host name (from ``--host``); ``auto``/None
    means detect. Strong env signals are checked first because Grok's
    Claude-compat layer runs the *Claude* hooks file under Grok, so the
    hooks.json alone cannot be trusted to know which host it's in.
    """
    if hint and hint != AUTO:
        if hint not in HOSTS:
            raise ValueError(
                f"unknown host {hint!r}; expected one of {', '.join(HOSTS)}"
            )
        return hint
    env = os.environ if env is None else env
    payload = payload or {}

    if env.get("GROK_HOOK_EVENT") or env.get("GROK_SESSION_ID"):
        return GROK
    if env.get("COPILOT_HOOK_DEPTH"):
        return COPILOT
    if env.get("CODEX_SESSION_ID") or env.get("CODEX_THREAD_ID"):
        return CODEX

    if "conversationId" in payload or "workspacePaths" in payload:
        return AGY
    transcript = str(payload.get("transcript_path") or "")
    if "turn_id" in payload or Path(transcript).name.startswith("rollout-"):
        return CODEX
    if "sessionId" in payload:
        return COPILOT
    if env.get("CLAUDECODE") or env.get("CLAUDE_SESSION_ID") or "session_id" in payload:
        return CLAUDE
    return SHELL


@dataclass
class HookInput:
    host: str
    session_id: Optional[str]
    cwd: Optional[str]
    raw: dict = field(default_factory=dict)

    @property
    def stop_hook_active(self) -> bool:
        v = self.raw.get("stop_hook_active")
        if v is None:
            v = self.raw.get("stopHookActive")
        return bool(v)


def _first(payload: Mapping[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def parse_hook_input(
    text: str,
    host_hint: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
) -> HookInput:
    """Parse a hook's stdin payload from any supported host."""
    payload: dict = {}
    text = (text or "").strip()
    if text:
        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {}

    host = detect_host(env=env, payload=payload, hint=host_hint)
    sid = _first(payload, "session_id", "sessionId", "conversationId", "thread_id")
    cwd = _first(payload, "cwd", "workspaceRoot", "workspace_root")
    if cwd is None:
        wp = payload.get("workspacePaths") or payload.get("workspace_paths")
        if isinstance(wp, list) and wp and isinstance(wp[0], str):
            cwd = wp[0]
    return HookInput(host=host, session_id=sid, cwd=cwd, raw=payload)


# --- Nudge text ------------------------------------------------------------

_TRIAGE_HINT = {
    CLAUDE: (
        "invoke the postcard-reader subagent via the Task tool "
        "(subagent_type='postcard:postcard-reader') to triage them"
    ),
    CODEX: (
        "spawn the postcard-reader agent (spawn_agent) to triage them if it is "
        "installed (oat-postcard setup codex)"
    ),
    COPILOT: "delegate to the postcard-reader custom agent to triage them",
    GROK: (
        "spawn the postcard-reader subagent "
        "(subagent_type 'postcard:postcard-reader') to triage them"
    ),
    AGY: "invoke the postcard-reader subagent to triage them",
    SHELL: "triage them",
}


def pending_notice(host: str, count: int, cli: str = "oat-postcard") -> str:
    hint = _TRIAGE_HINT.get(host, _TRIAGE_HINT[SHELL])
    msg = (
        f"postcard: {count} pending postcard(s) from other agent sessions. "
        f"Before continuing, {hint}. The subagent files routine mail into "
        "TODO.md and surfaces urgent mail back for your response."
    )
    if host != CLAUDE:
        msg += (
            f" If no such subagent is available, run `{cli} clerk-pending --json` "
            f"and triage each card yourself with `{cli} clerk-file <id>` or "
            f"`{cli} clerk-surface <id>`."
        )
    return msg


def format_nudge(host: str, event: str, message: str) -> Optional[str]:
    """Render the nudge in the host's hook-output dialect for ``event``.

    Returns None when this host/event pair cannot carry context, in
    which case the hook prints nothing (or ``{}`` for hosts that require
    a JSON object).
    """
    if host in (CLAUDE, CODEX) and event == EV_PROMPT:
        return json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message,
                }
            }
        )
    if host == GROK and event == EV_STOP:
        # Grok discards UserPromptSubmit output; Stop additionalContext
        # reaches the model on the following turn.
        return json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": message,
                }
            }
        )
    if host == COPILOT and event == EV_STOP:
        # agentStop: "block" forces one more turn with `reason` as its prompt.
        return json.dumps({"decision": "block", "reason": message})
    if host == AGY and event == EV_STOP:
        # Stop: "continue" keeps the loop going; `reason` lands as a system message.
        return json.dumps({"decision": "continue", "reason": message})
    return None


def empty_output(host: str) -> Optional[str]:
    """What to print when a hook has nothing to say."""
    if host == AGY:
        return "{}"
    return None


# --- Nudge de-duplication ---------------------------------------------------
# Hosts in STOP_NUDGE_HOSTS deliver the nudge as a *continuation* of the
# turn. If the agent never triages, we must not loop forever, so the nudge
# for a given set of pending cards is emitted once.

_NUDGE_MARKER = ".nudged"


def pending_fingerprint(pending_dir: Path) -> str:
    names = (
        sorted(p.name for p in pending_dir.glob("*.json"))
        if pending_dir.exists()
        else []
    )
    return hashlib.sha1("\n".join(names).encode()).hexdigest()


def should_nudge_once(pending_dir: Path) -> bool:
    """True the first time this exact set of pending cards is seen."""
    fp = pending_fingerprint(pending_dir)
    marker = pending_dir / _NUDGE_MARKER
    try:
        if marker.exists() and marker.read_text().strip() == fp:
            return False
        pending_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(fp + "\n")
    except OSError:
        return True
    return True


# --- Plugin root / CLI path -------------------------------------------------


def plugin_root() -> Optional[Path]:
    """The plugin checkout containing this package, if we're running from one."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(Path(__file__).resolve().parents[2])
    for c in candidates:
        if (c / "bin" / "oat-postcard").exists() and (c / "agents").is_dir():
            return c
    return None


def cli_path() -> str:
    root = plugin_root()
    if root is not None:
        return str(root / "bin" / "oat-postcard")
    return "oat-postcard"


# --- Codex subagent (TOML) --------------------------------------------------


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal frontmatter splitter for our own ``key: value`` agent files."""
    meta: dict = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return meta, text
    for line in lines[1:end]:
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body


def codex_agent_toml(agent_md: str, name: str = "postcard-reader") -> str:
    """Render our markdown subagent definition as a Codex custom-agent TOML."""
    meta, body = split_frontmatter(agent_md)
    desc = meta.get("description", "Triage pending postcard mail for this session.")
    desc = desc.replace("\\", "\\\\").replace('"', '\\"')
    if "'''" in body:
        body = body.replace("'''", "''\\'")
    return (
        f'name = "{meta.get("name", name)}"\n'
        f'description = "{desc}"\n'
        "developer_instructions = '''\n"
        f"{body.rstrip()}\n"
        "'''\n"
    )
