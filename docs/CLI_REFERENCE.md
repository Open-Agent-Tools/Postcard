# CLI reference

Full reference for the `oat-postcard` CLI. Commands are grouped by
audience: **user-facing** verbs are what you'll type (or what a slash
command wraps); **hook/infrastructure** verbs are called by Claude Code
hooks and the `postcard-reader` subagent and generally don't need to be
invoked by hand.

All subcommands share:

```
oat-postcard --version
oat-postcard <command> [flags]
```

Exit codes: `0` success, `1` runtime error (no session, missing
postcard, inactive recipient), `2` bad time-window spec on `log`.

## User-facing

### `send`

Send a postcard to another active session.

```
oat-postcard send <address> "<title>" "<body>" [--force]
```

- `<address>` — recipient's 3-word address (see `directory`).
- `<title>` — ≤140 chars.
- `<body>` — ≤1400 chars.
- `--force` *(added 0.3.3)* — send even if the recipient is not in
  the live directory. By default a send to a dead address errors out
  rather than silently writing to an orphan inbox that will later be
  garbage-collected.

Examples:

```
oat-postcard send bright-jade-engine "GET /users/:id shape" \
  "Is avatar_url nullable? ISO strings or epoch for timestamps?"

oat-postcard send ghost-iron-pier "note" "testing" --force
```

### `reply`

Reply to an existing postcard. Recipient is the parent's sender;
title is auto-generated as `"Re: <parent-title>"` (truncated to 140
chars). Envelope records `reply_to: <parent-id>` for threading.
*(Added 0.3.0.)*

```
oat-postcard reply <parent-id> "<body>" [--force]
```

- `<parent-id>` — full postcard id or 8-char prefix.
- `<body>` — ≤1400 chars.
- `--force` *(added 0.3.3)* — reply even if the parent sender is no
  longer active. Addresses are per-session and don't persist across
  restarts, so a reply to a dead sender is almost always a bug;
  `--force` lets you drop the reply into the orphan inbox anyway
  (testing, debugging).

Examples:

```
oat-postcard reply 8c4a1f03 "avatar_url is nullable; timestamps are ISO 8601 UTC"

oat-postcard reply 8c4a1f03 "late ack" --force
```

### `inbox`

List postcards addressed to this session. Pure observation — no
triage side effects. *(Added 0.3.0.)*

```
oat-postcard inbox [--limit N] [--watch] [--interval SECS]
```

- `--limit N` — number of entries (default 20).
- `--watch` — tail mode: print new arrivals as they land; Ctrl-C to
  exit.
- `--interval SECS` — poll interval in seconds when `--watch`
  (default `2.0`).

Output includes a `↳<parent-8-char>` marker for replies so threads
are visible.

Examples:

```
oat-postcard inbox
oat-postcard inbox --limit 50
oat-postcard inbox --watch
oat-postcard inbox --watch --interval 5
```

### `log`

Show the ledger history (all sends, across all sessions — not
just mail to you).

```
oat-postcard log [--limit N] [--since WINDOW] [--until WINDOW] \
                 [--watch] [--interval SECS]
```

- `--limit N` — cap the number of entries.
- `--since WINDOW` *(added 0.3.0)* — only show postcards newer than
  this.
- `--until WINDOW` *(added 0.3.0)* — only show postcards older than
  this.
- `--watch` — tail mode: print new sends as they land; Ctrl-C to
  exit. Unfiltered (all sessions), same semantics as `inbox --watch`.
- `--interval SECS` — poll interval in seconds when `--watch`
  (default `2.0`).

Accepted formats for `--since` / `--until`:

- shorthand duration: `30s`, `45m`, `1h`, `24h`, `7d` — interpreted
  as "now minus that much".
- ISO 8601 timestamp: `2026-04-22T14:00:00Z`, `2026-04-22T09:00:00-05:00`,
  or `2026-04-22` (naive timestamps are assumed UTC).

Bad specs exit `2` with `error: invalid time spec ...`.

Replies render with a `↳<parent-8-char>` marker.

Examples:

```
oat-postcard log --limit 20
oat-postcard log --since 1h
oat-postcard log --since 24h --until 1h
oat-postcard log --since 2026-04-22T00:00:00Z
oat-postcard log --watch
```

### `directory`

List every active session on this machine. The current session (if
any) is marked with `*`.

```
oat-postcard directory
```

Output columns: address, pid, working directory.

### `whoami`

Print this session's 3-word address. If the session isn't registered
yet, this is also the lazy self-registration path.

```
oat-postcard whoami
```

### `receipts`

Show read-receipt history from the ledger. Every time the
`postcard-reader` subagent files or surfaces a postcard, it writes a
receipt committed alongside the ledger.

```
oat-postcard receipts [--limit N]
```

- `--limit N` — cap the number of entries.

Output columns: `read_at`, `reader_address`, `action`
(`file` | `surface`), 8-char postcard id.

## Hooks / infrastructure

These commands are called by the plugin's hooks and the
`postcard-reader` subagent. They're safe to run by hand when
debugging, but not something you'd use in day-to-day messaging.

### `clerk-sweep`

Move new inbox mail for this session from
`~/.oat-postcard/inbox/<address>/` into
`~/.oat-postcard/pending/<session>/` (per-session staging). Called by
the `Stop` hook.

```
oat-postcard clerk-sweep [--quiet]
```

- `--quiet` — suppress the `N new postcard(s) staged` line.

### `clerk-pending`

List postcards pending triage for this session. Called by the
`UserPromptSubmit` hook (with `--count`) and the `postcard-reader`
subagent (with `--json`).

```
oat-postcard clerk-pending [--json] [--count]
```

- `--json` — emit full records as a JSON array (what the subagent
  consumes).
- `--count` — print only the integer count (what the hook checks to
  decide whether to flag the main agent).

Plain output (neither flag): one line per pending card.

### `clerk-file`

File a pending postcard into `TODO.md` and archive it. Used by the
`postcard-reader` subagent for routine mail.

```
oat-postcard clerk-file <id> [--todo PATH]
```

- `<id>` — postcard id (full or 8-char prefix).
- `--todo PATH` — path to `TODO.md` (default: `./TODO.md` in the
  current working directory).

### `clerk-surface`

Mark a pending postcard as surfaced to the main agent (and write a
`surface` receipt). Used by the `postcard-reader` subagent for urgent
mail; the subagent includes the full body verbatim in its summary.

```
oat-postcard clerk-surface <id>
```

- `<id>` — postcard id (full or 8-char prefix).

### `session-init`

Register this session in the directory. Called by the `SessionStart`
hook, and lazily by `Stop` / `UserPromptSubmit` for sessions that
predate the plugin install. Also runs `cleanup` implicitly.

```
oat-postcard session-init [--session-id ID] [--cwd PATH] [--pid N] [--quiet]
```

- `--session-id ID` — override `$CLAUDE_SESSION_ID`.
- `--cwd PATH` — override the recorded working directory.
- `--pid N` — PID to record in the directory entry. Hook scripts
  pass `$PPID` (Claude Code's long-lived PID). Defaults to the
  parent PID of this process, which is only correct when called from
  a hook.
- `--quiet` — suppress printing the address.

Idempotent: if the session already has a sidecar, returns the
existing address without touching the directory.

### `session-end`

Remove this session from the directory. Called by the `SessionEnd`
hook.

```
oat-postcard session-end [--session-id ID]
```

- `--session-id ID` — override `$CLAUDE_SESSION_ID`.

### `cleanup`

Prune stale state:

- `directory/<addr>.json` entries whose PID is no longer alive.
- `sessions/<id>.addr` sidecars not backed by a live directory entry.
- `pending/<session>/` dirs whose session is dead.
- `inbox/<address>/` dirs whose address is dead.
- `dropbox/` temp files older than 5 minutes (stuck writes).

```
oat-postcard cleanup [--dry-run]
```

- `--dry-run` — report what would be removed without touching
  anything.

Runs automatically at the start of every session (via
`session-init`). Manual invocation is rarely needed.

### `init`

Append an idempotent coordination block to the project's `CLAUDE.md`
(or `AGENTS.md`) so agents in that project know postcards exist and
when to reach for them. Markers are HTML comments so re-running is a
no-op.

```
oat-postcard init [--path PATH] [--force]
```

- `--path PATH` — target file. Defaults to `./CLAUDE.md` if it
  exists, else `./AGENTS.md`, else creates `./CLAUDE.md`.
- `--force` — rewrite the block in place if it's already present
  (e.g. after a version upgrade changed the block contents).

Prints one of: `created`, `appended oat-postcard block to`,
`replaced oat-postcard block in`, or `oat-postcard block already
present in ... (use --force to rewrite)`.
