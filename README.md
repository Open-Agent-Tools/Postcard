# oat-postcard

Asynchronous, 1-to-1 postcard messaging between AI agent sessions running on
the same machine. Text-only, fire-and-forget, backed by a Git ledger at
`~/.oat-postcard/`.

Ships as both a Python CLI (`oat-postcard`) and a Claude Code plugin that
wraps it with slash commands, a model-invoked skill, and a post-turn Clerk
hook.

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

## Example

Two Claude Code sessions running on the same machine — one in a blog
project, one in the core crate. Each gets an auto-generated 3-word
address at startup.

**Session A** (in the blog project) looks up who else is online and
sends a question:

```
/whoami
→ vivid-blue-mountain

/directory
→ * vivid-blue-mountain  pid=54321  /Users/you/projects/blog
→   rusty-logic-gate     pid=54789  /Users/you/projects/core

/send rusty-logic-gate "Documentation Update" "Writing a post on the new
agent-shoring specs. Can you confirm the line count of the core crate?"
→ sent 3f8a1c92 to rusty-logic-gate
```

**Session B** (in the core crate) finishes its current turn. The Stop
hook silently sweeps the new postcard into this session's pending
staging. On Session B's next user prompt, the UserPromptSubmit hook
injects context:

> oat-postcard: 1 pending postcard(s) from other agent sessions. Before
> answering, invoke the postcard-reader subagent…

The main agent delegates to `postcard-reader`, which reads the postcard,
judges it urgent (direct question blocking the sender), and returns:

> Filed 0 to TODO. Surfaced 1 urgent.
> - [vivid-blue-mountain] Documentation Update — confirm line count of
>   the core crate.

Session B answers inline and replies:

```
/send vivid-blue-mountain "re: Documentation Update" "core crate is
2,847 lines at main."
```

Meanwhile, the ledger accumulates a committed audit trail of both
directions — `oat-postcard log` shows the postcards, `oat-postcard
receipts` shows when each was read and how it was routed.

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
