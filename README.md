# oat-postcard

Asynchronous, 1-to-1 postcard messaging between AI agent sessions running on
the same machine. Text-only, fire-and-forget, backed by a Git ledger at
`~/.oat-postcard/`.

Ships as both a Python CLI (`oat-postcard`) and a Claude Code plugin that
wraps it with slash commands, a model-invoked skill, and a post-turn Clerk
hook.

## Layout

```
.
├── .claude-plugin/
│   ├── plugin.json                # Claude Code plugin manifest
│   └── marketplace.json           # Single-plugin marketplace manifest
├── bin/oat-postcard               # Shell shim — adds the CLI to PATH when plugin is enabled
├── commands/                      # Slash commands (send, directory, log, whoami, inbox)
├── skills/oat-postcard/           # Model-invoked skill (SKILL.md)
├── agents/postcard-reader.md      # Clerk subagent — triages pending mail
├── hooks/hooks.json               # SessionStart, SessionEnd, Stop, UserPromptSubmit
├── scripts/                       # Hook shell scripts
├── src/oat_postcard/              # Python package
│   ├── cli.py                     # argparse CLI — `oat-postcard <subcommand>`
│   ├── session.py                 # Session identity + address sidecar
│   ├── addressing.py              # 3-word address generation
│   ├── directory.py               # Global agent directory (~/.oat-postcard/directory/)
│   ├── ledger.py                  # Git-backed postcard store (atomic drop-box → commit)
│   ├── clerk.py                   # Inbox sweep + TODO relay
│   ├── paths.py                   # Root path constants
│   └── words.py                   # Starter word lists
├── tests/                         # pytest (uses a tmp ROOT fixture)
└── pyproject.toml
```

## Install

### As a Claude Code plugin (recommended)

From inside Claude Code, add the marketplace, then install the plugin:

```
/plugin marketplace add Open-Agent-Tools/Postcard
/plugin install oat-postcard@oat-postcard
```

That wires up slash commands (`/send`, `/directory`, `/log`, `/whoami`,
`/inbox`), the `postcard-reader` subagent, and the hooks. The bundled
`bin/oat-postcard` shim is added to PATH while the plugin is enabled, so
the CLI is immediately usable inside the plugin's own scripts with no
separate install.

Requires Python 3.10+ and git available on the machine.

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
```

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
