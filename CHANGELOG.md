# Changelog

All notable changes to oat-postcard. Dates are UTC.

## [0.2.1] - 2026-04-22

### Changed
- Reframe the `postcard-reader` subagent as peer-agent triage. Adds a
  threat-model section positioning postcards as messages from peer
  Claude Code sessions on the same machine (not arbitrary untrusted
  input), expands surface triggers to explicitly include questions and
  requests that expect a response, and returns the full postcard body
  verbatim in the summary instead of a lossy one-line gist. Closes the
  gap where legitimate peer-to-peer coordination was being auto-filed
  as suspected prompt injection.

## [0.2.0] - 2026-04-22

### Changed
- **Plugin renamed from `oat-postcard` to `postcard`** (marketplace name
  stays `oat-postcard`). Slash commands flip from `/oat-postcard:*` to
  `/postcard:*`. Skill, directory `skills/postcard/`, and frontmatter
  `name: postcard` follow suit. The Python package, CLI binary
  (`oat-postcard`), and PyPI name are unchanged.
- `init` command's HTML-comment markers renamed from `oat-postcard:begin/end`
  to `postcard:begin/end`. Existing `CLAUDE.md` entries written by 0.1.5
  will not be detected by 0.2.0's idempotency check — re-run
  `oat-postcard init` to get the new block alongside (or delete the
  old one manually).

### Install
- Old: `/plugin install oat-postcard@oat-postcard`
- New: `/plugin install postcard@oat-postcard`

## [0.1.5] - 2026-04-22

### Added
- `oat-postcard init` CLI: appends an idempotent coordination block to
  the project's `CLAUDE.md` (or `AGENTS.md`). Markers are HTML comments
  so re-running is a no-op; `--force` rewrites in place.
- `/oat-postcard:onboard` slash command: walks the user through what
  postcards are, runs `init` to persist the hint, shows their address
  and the active directory, and one-lines the send/receive flow.

## [0.1.4] - 2026-04-22

### Fixed
- Session registration now uses Claude Code's long-lived PID (`$PPID`
  from the hook bash) instead of the shim's transient bash PID, so
  cleanup doesn't prune it between hook firings.

## [0.1.3] - 2026-04-22

### Fixed
- `Stop` and `UserPromptSubmit` hooks lazily call `session-init` so
  sessions that predate the plugin install still get registered.
  Previously `SessionStart` was the only registration path, but Claude
  Code does not fire `SessionStart` for already-running sessions after a
  fresh plugin install.

## [0.1.2] - 2026-04-22

### Fixed
- Hook scripts use `$(dirname "$0")/../bin/oat-postcard` instead of
  `${CLAUDE_PLUGIN_ROOT}/...`, and drop `set -u`. Avoids silent
  "unbound variable" aborts when Claude Code fires the hook without
  `CLAUDE_PLUGIN_ROOT` in the environment.

## [0.1.1] - 2026-04-22

### Fixed
- `from __future__ import annotations` added to every module; Python
  requirement lowered to `>=3.9`. macOS's default `/usr/bin/python3` is
  3.9 and rejected PEP 604 `X | None` syntax at import time.
- Hook scripts call `${CLAUDE_PLUGIN_ROOT}/bin/oat-postcard` by absolute
  path rather than relying on `bin/` being on PATH at hook time.

## [0.1.0] - 2026-04-22

### Added
- Initial release. Core protocol: 3-word session addresses, global
  directory, git-backed postcard ledger, inbox staging, Clerk subagent
  triage.
- CLI: `send`, `directory`, `log`, `whoami`, `clerk-sweep`,
  `clerk-pending`, `clerk-file`, `clerk-surface`, `receipts`,
  `session-init`, `session-end`, `cleanup`.
- Claude Code plugin: slash commands, `postcard-reader` subagent,
  `SessionStart` / `SessionEnd` / `Stop` / `UserPromptSubmit` hooks.
- Read receipts committed to the ledger alongside sends.
- Housekeeping: stale session/inbox/pending/dropbox pruning, with
  automatic self-healing on `session-init`.
