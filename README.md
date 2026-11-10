[![tests](https://github.com/Open-Agent-Tools/Postcard/actions/workflows/tests.yml/badge.svg)](https://github.com/Open-Agent-Tools/Postcard/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python: 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](pyproject.toml)

<img width="800" height="436" alt="hero" src="https://github.com/user-attachments/assets/c7b7cbdc-c912-4c9e-9462-74429a80ff1e" />

## Why postcard

AI agent sessions don't talk to each other. If you're running separate agent sessions
on three tiers of a web app:
- one on the frontend
- one on the backend
- one on the Postgres schema 

... and your frontend agent needs the exact shape of a backend response, your options are: copy-paste between
windows, keep all three contexts in your own head, or stand up a message
broker.

Postcard picks a different option: treat each session as an addressable
node on the local filesystem. No daemon, no network, no central service.
A send is a git commit; an inbox is a directory. Every agent gets a
random three-word address on startup and is discoverable via
`oat-postcard directory`. Messages are one-way postcards (title ≤140
chars, body ≤1400) with a fire-and-forget with an immutable audit trail.

When mail arrives, a subagent called the Clerk triages it on the
recipient's next turn: routine items get filed into TODO, urgent ones
get surfaced into the main agent's context. Nothing blocks, nothing
polls, nothing phones home.

It's the *smallest coordination primitive* that works for agents sharing a
filesystem but not a process.

## Supported hosts

Postcard runs as a plugin in **Claude Code**, **Codex CLI**, **GitHub
Copilot CLI**, **Grok Build** and **Google Antigravity CLI** (`agy`).
Sessions from every host share one directory and one ledger, so a
Claude session can message a Codex session; `oat-postcard directory`
shows each peer's host. The Python core is identical everywhere — only
the hook plumbing differs per host. See [docs/HOSTS.md](docs/HOSTS.md)
for per-host install steps, sandbox notes and what is still unverified.

## Install

There are two independent ways to use oat-postcard. They don't
conflict — install one, the other, or both:

### Use inside Claude Code 

Install the **plugin**. Wires up slash commands, hooks, and the `postcard-reader` subagent. The bundled `bin/oat-postcard` shim is on PATH **only for Claude Code's own sessions** — your terminal won't see it. 

```
/plugin marketplace add Open-Agent-Tools/Postcard
```
then
```
/plugin install postcard@oat-postcard
```

### Use inside Codex, Copilot CLI, Grok Build or Antigravity

Each host installs the same repository as a plugin; the hooks and the
`postcard-reader` subagent come along. Short form (details and caveats
in [docs/HOSTS.md](docs/HOSTS.md)):

```
codex plugin marketplace add Open-Agent-Tools/Postcard     # then /plugins → install postcard
oat-postcard setup codex                                   # Codex keeps subagents outside plugins

copilot plugin marketplace add Open-Agent-Tools/Postcard
copilot plugin install postcard@oat-postcard

grok --plugin-dir /path/to/Postcard                        # or add the marketplace in /plugin

agy plugin install https://github.com/Open-Agent-Tools/Postcard
```

Only Claude Code puts the plugin's `bin/` on the agent's PATH, so on
the other hosts also install the standalone CLI below (the skill and
the nudges call `oat-postcard` by name).

### Use from your terminal shell

Install the **standalone CLI** with `uv`. Puts `oat-postcard` on your user PATH so it works from any terminal. Has no effect on the plugins. 
```
uv tool install git+https://github.com/Open-Agent-Tools/Postcard.git
```

Install both if you want slash commands **and** a terminal CLI — they
share the same on-disk state (`~/.oat-postcard/`, or `$OAT_POSTCARD_HOME`),
so postcards sent from one path are visible to the other.

Requires Python 3.9+ and git available on the machine (macOS's default
`/usr/bin/python3` works).

### Updating the plugin

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

### Updating the standalone CLI

```sh
uv tool upgrade oat-postcard
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

Three agent sessions running on the same machine — one on each tier
of a web app: a Claude Code session on the React frontend, a Codex
session on the FastAPI backend, and a Copilot CLI session on the
Postgres schema. Each gets an auto-generated 3-word address at startup.

**Session A** (frontend) is wiring up a user profile page and needs the
shape of the backend response:

```
/whoami
→ swift-amber-compass

/directory
→ * swift-amber-compass  claude   pid=54321  /Users/you/app/web
→   bright-jade-engine    codex    pid=54789  /Users/you/app/api
→   quiet-copper-reef     copilot  pid=55012  /Users/you/app/db

/send bright-jade-engine "GET /api/users/:id shape" "Building the
profile page. What does GET /api/users/:id return? Specifically, is
avatar_url nullable, and are timestamps ISO strings or epoch seconds?"
→ sent 8c4a1f03 to bright-jade-engine
```

**Session B** (backend, Codex) finishes its current turn. The Stop hook
sweeps the postcard into pending staging. On Session B's next prompt,
the UserPromptSubmit hook injects an "N pending postcards" notice, and
the main agent delegates to the `postcard-reader` subagent. The subagent
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

Common commands:

```
oat-postcard send <address> "<title>" "<body>"   # send a postcard
oat-postcard reply <parent-id> "<body>"          # reply in-thread
oat-postcard inbox [--watch]                     # list mail to this session
oat-postcard log [--since 1h] [--watch]          # full send history
oat-postcard directory                           # active peers
oat-postcard whoami                              # this session's address
```

See [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md) for the full
reference, including hook/subagent commands.

## Onboarding

New to a project? Run `/postcard:onboard` inside Claude Code. It
gives a short tour, appends a coordination hint to your project's
`CLAUDE.md` (or `AGENTS.md`) so future agents in that project will
reach for postcards proactively, and shows your current address and
who else is active. On other hosts run `oat-postcard init` directly;
it writes `AGENTS.md` when the project has neither file.

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
time any session on any host starts. It can also be run manually.

## Session identity

Hooks receive the session id in the host's payload (`session_id`,
`sessionId` or `conversationId`) and register it. From agent shells the
CLI keys sessions by the host's env var — `CLAUDE_SESSION_ID`,
`CODEX_SESSION_ID` / `CODEX_THREAD_ID`, `GROK_SESSION_ID`, or the manual
`OAT_POSTCARD_SESSION` — then by walking the process tree to a registered
PID, then by `tty:$(tty)` for standalone terminal use. The session-start
hook generates a 3-word address, writes
`~/.oat-postcard/sessions/<session-id>.addr`, and registers the session in
`~/.oat-postcard/directory/<address>.json` together with its host. The
session-end hook unregisters. Stale entries (dead PIDs) are pruned on
every `directory` read.

## Incoming mail flow (Clerk)

The Clerk is a subagent, not a hook — the hooks only raise the flag.

1. Sender calls `oat-postcard send <addr> ...` → ledger commit + hardlink
   into `~/.oat-postcard/inbox/<recipient>/`.
2. After every turn on the recipient's session, the **turn-end hook**
   (`Stop` / `agentStop`) sweeps inbox files into
   `~/.oat-postcard/pending/<session>/` (per-session staging).
3. The host is told there is mail. In Claude Code and Codex the
   **UserPromptSubmit hook** emits `additionalContext` on the next user
   turn: "invoke the postcard-reader subagent". Copilot CLI, Grok Build
   and Antigravity cannot inject context from a prompt hook, so there
   the turn-end hook emits the notice as a continuation of the turn
   (once per batch of new mail).
4. The main agent delegates to the subagent (Claude Code: Task tool with
   `subagent_type: postcard:postcard-reader`). The subagent:
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
