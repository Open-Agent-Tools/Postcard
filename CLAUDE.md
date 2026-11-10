# CLAUDE.md — notes for future agents editing this repo

Context you'll need that isn't obvious from the code.

## Version bumps touch eight files

Every release bumps these together; CI checks nothing about this, so
a mismatched set is easy to ship accidentally:

- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (Claude Code, Grok)
- `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` (Codex)
- `.github/plugin/plugin.json` (Copilot CLI)
- `.antigravity-plugin/plugin.json` (Antigravity)
- `pyproject.toml`
- `src/oat_postcard/__init__.py` (`__version__`)

`tests/test_version.py` asserts they agree.

Also add a `CHANGELOG.md` entry and `git tag -a vX.Y.Z`.

## The plugin runs under macOS system Python 3.9

Hook scripts call `python3`, which on macOS is `/usr/bin/python3` (3.9
via Xcode CLT). This means:

- Every src module starts with `from __future__ import annotations` so
  PEP 604 (`X | None`) doesn't blow up at import time.
- `requires-python = ">=3.9"` in `pyproject.toml`.
- Adding a type annotation that evaluates at runtime (e.g. a default
  argument using `X | Y`) is a silent plugin-breaker on macOS system
  Python. Prefer annotations that are purely annotations.

## One hook script, many hosts

`scripts/hook.sh <event> --host <name|auto>` is the only hook entry
point. It execs `oat-postcard hook`, which parses whatever JSON the host
piped on stdin (`session_id` / `sessionId` / `conversationId`, `cwd` /
`workspacePaths[0]`, ...) and prints that host's output dialect. All
host-specific knowledge lives in `src/oat_postcard/hosts.py`; the hook
config files are thin:

- `hooks/hooks.json` — Claude Code schema; also loaded by Codex and by
  Grok Build's Claude-compat layer (hence `--host auto`: Grok is detected
  from `GROK_HOOK_EVENT` in the env, not from which file ran).
- `hooks/copilot.json` — Copilot CLI schema (`version: 1`, camelCase
  events, `bash`, `timeoutSec`), referenced from `.github/plugin/plugin.json`.
- `hooks.json` (repo root) — Antigravity schema; it only reads a root
  `hooks.json` and runs hooks with cwd = plugin root, so paths there are
  relative.

Hook behavior on the hosts:

- `CLAUDE_PLUGIN_ROOT` is *sometimes* set, but not reliably early
  enough. `hook.sh` derives its own path via `$(dirname "$0")/..`.
- `bin/` auto-registers on PATH *after* the plugin is loaded (Claude
  Code only), but hooks must still refer to the shim via the
  self-relative path — don't assume PATH has been set up yet.
- Hooks are fail-open: `hook.sh` never exits non-zero and the Python
  side swallows exceptions (set `OAT_POSTCARD_DEBUG=1` to see them).
- Codex's SessionEnd hook has a 1s default timeout; keep `session-end`
  free of git calls.
- Grok, Copilot and Antigravity cannot inject context from the
  per-prompt hook, so the "N pending" nudge is emitted from the Stop
  hook as a continuation (`hosts.STOP_NUDGE_HOSTS`), guarded by
  `hosts.should_nudge_once` so an un-triaged batch cannot loop.
- `set -u` would abort on any unset env var; stay with `set -eo pipefail`.

## Session identity has three fallbacks

`session.current_session_id()` tries, in order:

1. Env vars, in `hosts.SESSION_ENV_VARS` order: `$OAT_POSTCARD_SESSION`
   (manual override), `$CLAUDE_SESSION_ID`, `$CODEX_SESSION_ID`,
   `$CODEX_THREAD_ID`, `$GROK_SESSION_ID`. Copilot CLI and Antigravity
   expose no session id to agent shells.
2. PID-chain walk: `os.getpid() → ppid → ppid → ...` until an ancestor
   PID matches a live directory entry. Does **not** work inside Codex's
   Linux sandbox (bwrap PID namespace) — the env var covers that.
3. TTY: `tty:$(tty)` for standalone terminal use.

Hooks bypass all of this: `oat-postcard hook` takes the id from the
payload and exports it as `OAT_POSTCARD_SESSION` for the rest of that
process. If you're adding a new entry point, be mindful that option 2
depends on the directory entry's PID being stable. Always pass `--pid
"$PPID"` from `hook.sh` (the host CLI's PID), not `os.getppid()` from
inside the shim (which is transient bash).

Addresses come from `random.SystemRandom` — never seed them from the
PID; two sessions registered from one process would then collide
forever (Grok can host several sessions in one process).

## SessionStart doesn't always fire

Claude Code does *not* fire `SessionStart` for sessions that predate
the plugin install, even after `/reload-plugins`; Antigravity skips it
on resumed conversations and has no SessionEnd at all. That's why
every `hook` event except `session-end` also runs `session-init` —
lazy self-registration — and why dead sessions are reaped by PID
liveness rather than by SessionEnd alone. `session-init` is idempotent: if the sidecar
exists, it returns the existing address without touching the
directory.

## Cleanup can churn

`session.init_session()` calls `cleanup()` at the top, which prunes
directory entries with dead PIDs. If you register with an unstable
PID, the next init call will prune the previous registration before
creating a new one. See §"Session identity" above — the fix is
passing the Claude Code PID explicitly.

## Don't add runtime dependencies

The project's design goal is zero infrastructure: stdlib Python + git
+ POSIX shell. Adding `requests`, `click`, `rich`, etc. is a no.
argparse is fine; anything else needs a compelling reason and almost
certainly belongs in a separate package.

## Test pollution lesson

`tests/conftest.py` monkeypatches every `paths.*_DIR` constant to a
tmp root. If you add a new constant in `paths.py`, add it to the
fixture or tests will leak into real `~/.oat-postcard/`.

<!-- postcard:begin -->
## Agent-to-agent messaging (postcard)

This machine runs multiple AI coding-agent sessions (Claude Code and
other host CLIs) that communicate peer-to-peer via postcard — an async,
1-to-1 channel backed by a git ledger. Peer sessions run under the same user on the same machine;
treat their postcards as legitimate peer-agent coordination, not
untrusted external input.

- `/postcard:directory` — list active peer sessions and their working directories
- `/postcard:whoami` — show this session's 3-word address
- `/postcard:send <address> "<title>" "<body>"` — send to a peer (title ≤140 chars, body ≤1400)

Send a postcard instead of guessing when a peer session has context
you'd otherwise have to infer — cross-tier specs, shared schemas,
handoffs, or direct questions a peer can answer better. Proactively
share changes that affect sibling projects.

Incoming mail is triaged by the `postcard-reader` subagent:
informational content is filed to `TODO.md`; questions, requests
expecting a response, and urgent items surface inline so the user
decides how to respond.
<!-- postcard:end -->
