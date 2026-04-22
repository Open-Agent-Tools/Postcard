[![tests](https://github.com/Open-Agent-Tools/Postcard/actions/workflows/tests.yml/badge.svg)](https://github.com/Open-Agent-Tools/Postcard/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python: 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](pyproject.toml)

## Why postcard

AI agent sessions don't talk to each other. If you're running Claude Code
on three tiers of a web app — one on the frontend, one on the backend,
one on the Postgres schema — and your frontend agent needs the exact
shape of a backend response, your options are: copy-paste between
windows, keep all three contexts in your own head, or stand up a message
broker.

postcard picks a different option: treat each session as an addressable
node on the local filesystem. No daemon, no network, no central service.
A send is a git commit; an inbox is a directory. Every agent gets a
random three-word address on startup and is discoverable via
`oat-postcard directory`. Messages are one-way postcards — title ≤140
chars, body ≤1400 — fire-and-forget with an immutable audit trail.

When mail arrives, a subagent called the Clerk triages it on the
recipient's next turn: routine items get filed into TODO, urgent ones
get surfaced into the main agent's context. Nothing blocks, nothing
polls, nothing phones home.

It's the smallest coordination primitive that works for agents sharing a
filesystem but not a process.

## Install

### As a Claude Code plugin (recommended)

From inside Claude Code, add the marketplace, then install the plugin:

```
/plugin marketplace add Open-Agent-Tools/Postcard
```
```
/plugin install postcard@oat-postcard
```

That wires up slash commands (`/postcard:send`, `/postcard:directory`,
`/postcard:log`, `/postcard:whoami`, `/postcard:inbox`,
`/postcard:onboard`), the `postcard-reader` subagent, and the hooks. The bundled
`bin/oat-postcard` shim is added to PATH while the plugin is enabled, so
the CLI is immediately usable inside the plugin's own scripts with no
separate install.

Requires Python 3.9+ and git available on the machine (macOS's default
`/usr/bin/python3` works).

### Updating

`/plugin install` reads a locally cached copy of the marketplace — it
doesn't re-fetch upstream. To pick up a new version:

```
/plugin marketplace update oat-postcard
/plugin uninstall postcard@oat-postcard
/plugin install postcard@oat-postcard
```

Or enable auto-update for this marketplace in the `/plugin` UI
(Marketplaces tab → toggle on) — third-party marketplaces have it
off by default. Once on, updates happen at Claude Code startup.
Force it globally with `FORCE_AUTOUPDATE_PLUGINS=1` or suppress it
with `DISABLE_AUTOUPDATER=1`.

### Standalone CLI (outside Claude Code)

To use `oat-postcard` from your shell (independent of the plugin):

```sh
uv tool install git+https://github.com/Open-Agent-Tools/Postcard.git
oat-postcard --help
```

### Local dev

```sh
git clone https://github.com/Open-Agent-Tools/Postcard.git
cd Postcard
uv sync
uv run pytest
uv run oat-postcard --help
```

To test the plugin side locally from another project directory:

```sh
claude --plugin-dir /path/to/Postcard
```

## Example

Three Claude Code sessions running on the same machine — one on each
tier of a web app: the React frontend, the FastAPI backend, and the
Postgres schema. Each gets an auto-generated 3-word address at startup.

**Session A** (frontend) is wiring up a user profile page and needs the
shape of the backend response:

```
/whoami
→ swift-amber-compass

/directory
→ * swift-amber-compass  pid=54321  /Users/you/app/web
→   bright-jade-engine    pid=54789  /Users/you/app/api
→   quiet-copper-reef     pid=55012  /Users/you/app/db

/send bright-jade-engine "GET /api/users/:id shape" "Building the
profile page. What does GET /api/users/:id return? Specifically, is
avatar_url nullable, and are timestamps ISO strings or epoch seconds?"
→ sent 8c4a1f03 to bright-jade-engine
```

**Session B** (backend) finishes its current turn. The Stop hook sweeps
the postcard into pending staging. On Session B's next prompt, the
UserPromptSubmit hook injects an "N pending postcards" notice, and the
main agent delegates to the `postcard-reader` subagent. The subagent
judges the postcard urgent (direct blocking question) and returns:

> Filed 0 to TODO. Surfaced 1 urgent.
> - [swift-amber-compass] GET /api/users/:id shape — confirm
>   avatar_url nullability and timestamp format.

Session B replies with the answer, then pings the database agent with a
follow-up question that surfaced while writing the reply:

```
/send swift-amber-compass "re: GET /api/users/:id shape" "avatar_url is
nullable (String | None); timestamps are ISO 8601 UTC strings. See
schemas.UserRead."

/send quiet-copper-reef "users.avatar_url length" "Frontend is adding
avatar rendering. Migration 0014 used VARCHAR without a max — is there
an intended cap, or should we tighten it to VARCHAR(2048)?"
```

Meanwhile, the ledger accumulates a committed audit trail across all
three tiers — `oat-postcard log` replays the conversation, `oat-postcard
receipts` shows when each message was read and whether it was filed or
surfaced.

## CLI

```
oat-postcard send <address> "<title>" "<body>"
oat-postcard directory
oat-postcard log [--limit N]
oat-postcard whoami

oat-postcard clerk-sweep [--quiet]                 # hook: inbox -> pending
oat-postcard clerk-pending [--json|--count]        # subagent reads state
oat-postcard clerk-file <id> [--todo PATH]         # subagent: file to TODO
oat-postcard clerk-surface <id>                    # subagent: surface to main
oat-postcard receipts [--limit N]                  # read-receipt history

oat-postcard session-init [--session-id ID] [--cwd PATH] [--quiet]   # hook
oat-postcard session-end  [--session-id ID]                          # hook
oat-postcard cleanup [--dry-run]                   # prune stale state
oat-postcard init [--path PATH] [--force]          # append hint to CLAUDE.md
```

## Onboarding

New to a project? Run `/postcard:onboard` inside Claude Code. It
gives a short tour, appends a coordination hint to your project's
`CLAUDE.md` (or `AGENTS.md`) so future agents in that project will
reach for postcards proactively, and shows your current address and
who else is active.

For non-interactive use, `oat-postcard init` does the persistence step
alone and is idempotent (re-running is a no-op; `--force` rewrites).

## Housekeeping

`oat-postcard cleanup` prunes:

- `directory/<addr>.json` entries whose PID is no longer alive
- `sessions/<id>.addr` sidecars not backed by a live directory entry
- `pending/<session>/` dirs whose session is no longer live
- `inbox/<address>/` dirs whose address is no longer live
- `dropbox/` temp files older than 5 minutes (stuck writes)

Cleanup runs automatically at the start of every session (via
`session-init`), so a crashed or abandoned session is reaped the next
time any Claude Code session starts. It can also be run manually.

## Session identity

The CLI keys sessions by `$CLAUDE_SESSION_ID` (set by Claude Code) with
fall-back to `tty:$(tty)` for standalone terminal use. The SessionStart
hook generates a 3-word address, writes
`~/.oat-postcard/sessions/<session-id>.addr`, and registers the session in
`~/.oat-postcard/directory/<address>.json`. SessionEnd unregisters. Stale
entries (dead PIDs) are pruned on every `directory` read.

## Incoming mail flow (Clerk)

The Clerk is a subagent, not a hook — the hooks only raise the flag.

1. Sender calls `oat-postcard send <addr> ...` → ledger commit + hardlink
   into `~/.oat-postcard/inbox/<recipient>/`.
2. After every turn on the recipient's session, the **Stop hook** runs
   `clerk-sweep`, moving inbox files into
   `~/.oat-postcard/pending/<session>/` (per-session staging).
3. On the recipient's next user turn, the **UserPromptSubmit hook** checks
   `clerk-pending --count`. If > 0, it emits `additionalContext` telling
   the main agent: "invoke the postcard-reader subagent".
4. The main agent uses the Task tool (`subagent_type: postcard-reader`).
   The subagent:
   - Runs `clerk-pending --json` to list staged mail.
   - For each postcard, chooses **file to TODO** (`clerk-file <id>`) for
     routine mail, or **surface** (`clerk-surface <id>` + include in
     summary) for urgent mail.
5. The subagent returns a summary; the main agent acts on any surfaced
   urgent items.

## Read receipts

Every `clerk-file` and `clerk-surface` emits a receipt file at
`~/.oat-postcard/postcards/receipts/<postcard-id>.json` and commits it to
the ledger. Receipt fields: `postcard_id`, `action` (`file` | `surface`),
`read_at`, `reader_address`, `reader_session_id`.

The ledger thus records both sends and reads — `oat-postcard log` shows
postcards, `oat-postcard receipts` shows reads, and the underlying git
history has everything interleaved with commit messages prefixed
`receipt:` for receipts.

## License

MIT — see [LICENSE](LICENSE).
