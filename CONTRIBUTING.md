# Contributing to oat-postcard

Thanks for your interest! This project is small and intentionally
zero-infrastructure — it should stay that way.

## Setup

```sh
git clone https://github.com/Open-Agent-Tools/Postcard.git
cd Postcard
uv sync
```

## Before you submit

Run the full local gate:

```sh
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
```

CI runs the same on Ubuntu + macOS across Python 3.9–3.14.

## Commit style

- Imperative, lowercase subject (`fix the thing`, not `Fixed the thing`).
- Body explains *why*, not *what* — the diff shows what.
- No generated trailers added by tooling; a human-written
  `Co-Authored-By:` line is fine.

## Scope

Features that fit the project:

- Anything that improves the core send → receive → triage loop on a
  single machine.
- Better Clerk heuristics, receipt data, housekeeping, CLI ergonomics.

Features that do *not* fit:

- Network transport, SaaS sync, push notifications.
- New dependencies on anything that isn't stdlib + git.
- Rich-media postcards (attachments, images). Text only.

If in doubt, open an issue first.

## Testing hooks / plugin behavior

Pure-Python logic — including payload parsing and output dialects for
every host — is covered by `tests/` (`test_hosts.py`,
`test_hook_cmd.py`). Whether a given host CLI actually fires the events
with the documented payload requires a running session of that CLI and
is verified manually; see `docs/HOSTS.md` for the per-host checklist.
To exercise the hook path by hand against an isolated state root:

```sh
OAT_POSTCARD_HOME=/tmp/pc-test bash ./scripts/hook.sh session-start --host claude \
  <<< '{"session_id":"manual-test","cwd":"/tmp"}'
OAT_POSTCARD_HOME=/tmp/pc-test ./bin/oat-postcard directory
```

Swap `--host` and the payload shape to test another host (Copilot:
`{"sessionId":...}`, Antigravity: `{"conversationId":...,"workspacePaths":[...]}`).

## Releasing

1. Bump version in every manifest and the package — `.claude-plugin/`
   (`plugin.json`, `marketplace.json`), `.codex-plugin/plugin.json`,
   `.agents/plugins/marketplace.json`, `.github/plugin/plugin.json`,
   `.antigravity-plugin/plugin.json`, `pyproject.toml`,
   `src/oat_postcard/__init__.py`. `tests/test_version.py` checks they agree.
2. Update `CHANGELOG.md`.
3. Tag: `git tag -a vX.Y.Z -m 'vX.Y.Z' && git push --tags`.
