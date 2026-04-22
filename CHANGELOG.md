# Changelog

All notable changes to oat-postcard. Dates are UTC.

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
