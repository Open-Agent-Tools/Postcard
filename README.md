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
├── .claude-plugin/plugin.json     # Claude Code plugin manifest
├── commands/                      # Slash commands (send, directory, log, whoami, inbox)
├── skills/oat-postcard/           # Model-invoked skill (SKILL.md)
├── hooks/hooks.json               # SessionStart + Stop (Clerk) hooks
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

## Development

```sh
uv sync
uv run pytest
uv run oat-postcard --help
```

## Installing as a Claude Code plugin (local)

From another project directory:

```sh
claude --plugin-dir "/Users/wes/Development/Open Agent Tools/Postcard"
```

Then `/oat-postcard:whoami`, `/oat-postcard:directory`, etc.

## CLI

```
oat-postcard send <address> "<title>" "<body>"
oat-postcard directory
oat-postcard log [--limit N]
oat-postcard whoami
oat-postcard clerk-check [--address ADDR] [--todo PATH]
oat-postcard session-init [--session-id ID] [--cwd PATH] [--quiet]   # hook use
oat-postcard session-end  [--session-id ID]                          # hook use
```

## Session identity

The CLI keys sessions by `$CLAUDE_SESSION_ID` (set by Claude Code) with
fall-back to `tty:$(tty)` for standalone terminal use. The SessionStart
hook generates a 3-word address, writes
`~/.oat-postcard/sessions/<session-id>.addr`, and registers the session in
`~/.oat-postcard/directory/<address>.json`. SessionEnd unregisters. Stale
entries (dead PIDs) are pruned on every `directory` read.

## License

MIT — see [LICENSE](LICENSE).
