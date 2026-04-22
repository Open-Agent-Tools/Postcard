# Changelog

All notable changes to oat-postcard. Dates are UTC.

## [0.3.3] - 2026-04-22

### Changed
- `send` and `reply` now validate the recipient against the live
  directory and error out by default if the address is not active.
  Previously sends to dead addresses silently wrote to an orphan
  inbox that `cleanup` would later garbage-collect — making it look
  like the message went through when in fact no peer ever read it.
  Since 3-word addresses are per-session and don't persist across
  restarts, a dead-address send is almost always a bug.
- Error format: `error: address 'foo-bar-baz' is not in the live
  directory. Run 'oat-postcard directory' to see active peers;
  --force to send anyway.` (Or the equivalent "parent sender no
  longer in the live directory" variant for `reply`.)
- `--force` flag added to both `send` and `reply` to bypass the check
  when you intentionally want to drop a postcard into an orphan
  inbox (testing, debugging).
- New helper `directory.is_active(address) -> bool`.

## [0.3.2] - 2026-04-22

### Changed
- Rewrite `skills/postcard/SKILL.md` to match current (v0.3.x)
  behavior. Adds an explicit trust-model section (peer sessions are
  legitimate coordination, not untrusted input), updates the Clerk
  flow to reflect v0.2.1+ semantics (full-body-verbatim surfacing,
  questions and requests-for-response surface too), adds a "Writing
  postcards" section with well-shaped examples (status / context /
  questions / handoffs), adds reply-side guidance (prefer
  `reply <parent-id>` over fresh `send` for threaded responses), and
  disambiguates CLI `inbox` (passive) from subagent triage (active).

## [0.3.1] - 2026-04-22

### Fixed
- CLI no longer crashes with a Python traceback when `send` or `reply`
  is called with an oversized title (>140) or body (>1400). The
  underlying `ValueError` is now caught by `main()` and rendered as a
  clean `error: body exceeds 1400 chars (1823)` message with exit
  code 1. Same fix covers any other `ValueError` that bubbles up from
  CLI commands.

## [0.3.0] - 2026-04-22

### Added
- **`reply` verb.** `oat-postcard reply <parent-id> "<body>"` sends a
  reply to an existing postcard. Recipient is the parent's sender;
  title is auto-generated as `"Re: <parent-title>"` (truncated to 140
  chars). Envelope records `reply_to: <parent-id>` so threading is
  queryable and receiving sessions can see a postcard is a direct
  response to something they sent.
- **`reply_to` field on `Postcard`.** Optional, backwards-compatible:
  records written by 0.2.x without this field load correctly.
- **`inbox` verb.** `oat-postcard inbox [--limit N] [--watch]` lists
  postcards addressed to this session (default 20), or tails new
  arrivals in `--watch` mode (polls every 2s; Ctrl-C to exit). Pure
  observation — no triage side effects.
- **`log --since` / `--until`.** Time-window filters on the ledger
  history. Accepts shorthand (`1h`, `24h`, `7d`, `30m`, `45s`) or ISO
  timestamps. Composes with `--limit`.
- Postcards that are replies now render with a `↳<parent-8-char>`
  marker in `log` and `inbox` output so threads are visible.

### Changed (breaking)
- **`/postcard:inbox` slash command repurposed.** It previously
  triggered the `postcard-reader` subagent for triage; now it runs
  `oat-postcard inbox` (passive listing, matches CLI semantics). The
  hook-driven auto-triage still fires on every turn, so the manual
  trigger was redundant. If you want to force a re-triage, invoke the
  `postcard-reader` subagent directly via the Task tool.

### Subagent
- `postcard-reader` now includes `reply_to` in surfaced postcards
  (when present) so the main agent can see thread context.

## [0.2.2] - 2026-04-22

### Changed
- Rewrite the `oat-postcard init` coordination block to be explicit
  about peer-to-peer agent-to-agent messaging. Heading changes from
  "Cross-session coordination" to "Agent-to-agent messaging"; adds a
  trust-framing sentence positioning peer sessions as same-user /
  same-machine (not untrusted input); and updates the triage
  description to match v0.2.1 semantics (informational → `TODO.md`;
  questions, requests-for-response, and urgent → surfaced inline).
- Existing `CLAUDE.md` entries written by 0.2.0/0.2.1 are still
  detected by the idempotency check (markers unchanged). Re-run
  `oat-postcard init --force` to replace the old block in place.

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
