# CLAUDE.md — notes for future agents editing this repo

Context you'll need that isn't obvious from the code.

## Version bumps touch four files

Every release bumps these together; CI checks nothing about this, so
a mismatched set is easy to ship accidentally:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `pyproject.toml`
- `src/oat_postcard/__init__.py` (`__version__`)

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

## Hook scripts must be self-contained

Claude Code's behavior on firing hooks:

- `CLAUDE_PLUGIN_ROOT` is *sometimes* set, but not reliably early
  enough. Hooks derive their own path via `$(dirname "$0")/..`.
- `bin/` auto-registers on PATH *after* the plugin is loaded, but
  hooks must still refer to the shim via the self-relative path —
  don't assume PATH has been set up yet.
- `set -u` will abort on any unset env var. Hooks use `set -eo
  pipefail` (no `-u`) and `${var:-}` guards around optional payload
  fields.

## Session identity has four fallbacks

`session.current_session_id()` tries, in order:

1. `$CLAUDE_SESSION_ID` env var (set by Claude Code; not always
   propagated to tool Bash invocations).
2. `$OAT_POSTCARD_SESSION` env var (manual override for tests).
3. PID-chain walk: `os.getpid() → ppid → ppid → ...` until an ancestor
   PID matches a live directory entry.
4. TTY: `tty:$(tty)` for standalone terminal use.

If you're adding a new entry point, be mindful that option 3 depends
on the directory entry's PID being stable. Always pass `--pid "$PPID"`
from hook scripts (which is Claude Code's PID), not `os.getppid()`
from inside the shim (which is transient bash).

## SessionStart doesn't always fire

Claude Code does *not* fire `SessionStart` for sessions that predate
the plugin install, even after `/reload-plugins`. That's why the
`Stop` and `UserPromptSubmit` hooks also call `session-init` — lazy
self-registration. `session-init` is idempotent: if the sidecar
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
## Cross-session coordination (postcard)

This machine runs multiple AI agent sessions. You have postcard messaging available:

- `/postcard:directory` — list active sessions and their working directories
- `/postcard:whoami` — show this session's 3-word address
- `/postcard:send <address> "<title>" "<body>"` — message another session (title ≤140 chars, body ≤1400)

When the user's question would benefit from another session's context
(cross-tier specs, shared schemas, cross-project handoffs, or explicit
"ask the other agent" requests), send a postcard instead of guessing.
Incoming mail is triaged automatically by the `postcard-reader`
subagent — routine items go to `TODO.md`, urgent ones surface inline
in your next reply.
<!-- postcard:end -->
