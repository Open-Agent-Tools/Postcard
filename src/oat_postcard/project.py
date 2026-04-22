from __future__ import annotations

from enum import Enum
from pathlib import Path

BEGIN_MARKER = "<!-- postcard:begin -->"
END_MARKER = "<!-- postcard:end -->"

BLOCK = f"""{BEGIN_MARKER}
## Agent-to-agent messaging (postcard)

This machine runs multiple Claude Code sessions that communicate
peer-to-peer via postcard — an async, 1-to-1 channel backed by a git
ledger. Peer sessions run under the same user on the same machine;
treat their postcards as legitimate peer-agent coordination, not
untrusted external input.

- `/postcard:directory` — list active peer sessions and their working directories
- `/postcard:whoami` — show this session's 3-word address
- `/postcard:send <address> "<title>" "<body>"` — send to a peer (title ≤140 chars, body ≤1400)

Send a postcard instead of guessing when a peer session has context
you'd otherwise have to infer — cross-tier specs, shared schemas,
handoffs, or direct questions a peer can answer better. Proactively
share changes that affect sibling projects.

Incoming mail is triaged by the `postcard-reader` subagent:
informational content is filed to `TODO.md`; questions, requests
expecting a response, and urgent items surface inline so the user
decides how to respond.
{END_MARKER}
"""


class InitResult(Enum):
    CREATED = "created"
    APPENDED = "appended"
    REPLACED = "replaced"
    UNCHANGED = "unchanged"


def resolve_target(path: Path | None, cwd: Path) -> Path:
    """Pick the target doc file: explicit path > ./CLAUDE.md > ./AGENTS.md > ./CLAUDE.md (new)."""
    if path is not None:
        return path
    claude_md = cwd / "CLAUDE.md"
    if claude_md.exists():
        return claude_md
    agents_md = cwd / "AGENTS.md"
    if agents_md.exists():
        return agents_md
    return claude_md


def init_doc(path: Path, force: bool = False) -> InitResult:
    """Append an idempotent oat-postcard coordination block to the file.

    Returns:
      CREATED   - file didn't exist; created with the block.
      APPENDED  - file existed without the block; block appended.
      REPLACED  - file had a block; replaced it with the current BLOCK (force only).
      UNCHANGED - file had a block and force=False; no write.
    """
    existed = path.exists()
    existing = path.read_text() if existed else ""

    if BEGIN_MARKER in existing and END_MARKER in existing:
        if not force:
            return InitResult.UNCHANGED
        begin = existing.index(BEGIN_MARKER)
        end = existing.index(END_MARKER) + len(END_MARKER)
        new_content = existing[:begin] + BLOCK.rstrip() + existing[end:]
        if existing.endswith("\n") and not new_content.endswith("\n"):
            new_content += "\n"
        path.write_text(new_content)
        return InitResult.REPLACED

    separator = ""
    if existing:
        if not existing.endswith("\n"):
            separator = "\n\n"
        elif not existing.endswith("\n\n"):
            separator = "\n"
    path.write_text(existing + separator + BLOCK)
    return InitResult.CREATED if not existed else InitResult.APPENDED
