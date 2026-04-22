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

CI runs the same on Ubuntu + macOS across Python 3.9–3.12.

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

Pure-Python logic is covered by `tests/`. Hook-level behavior
(SessionStart firing, PID registration, lazy init) requires a running
Claude Code session and is verified manually. When you change a hook
script, run:

```sh
env -i HOME="$HOME" PATH=/usr/bin:/bin bash ./scripts/session-start.sh \
  <<< '{"session_id":"manual-test","cwd":"/tmp"}'
```

and confirm `~/.oat-postcard/directory/` gets a fresh entry.

## Releasing

1. Bump version in `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json`, `pyproject.toml`, and
   `src/oat_postcard/__init__.py` — they must agree.
2. Update `CHANGELOG.md`.
3. Tag: `git tag -a vX.Y.Z -m 'vX.Y.Z' && git push --tags`.
