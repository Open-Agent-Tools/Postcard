import json
from pathlib import Path

from . import ledger, paths
from .ledger import Postcard

TODO_HEADER = "## Postcards"


def _json_files(d: Path) -> list[Path]:
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir() if p.is_file() and p.suffix == ".json")


def sweep(address: str, session_id: str) -> int:
    """Move new inbox postcards into the session's pending staging area."""
    paths.ensure_root()
    inbox = paths.inbox_for(address)
    if not inbox.exists():
        return 0
    pending = paths.pending_for(session_id)
    pending.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in _json_files(inbox):
        p.rename(pending / p.name)
        count += 1
    return count


def pending(session_id: str) -> list[Postcard]:
    cards: list[Postcard] = []
    for p in _json_files(paths.pending_for(session_id)):
        try:
            cards.append(Postcard(**json.loads(p.read_text())))
        except (json.JSONDecodeError, OSError, TypeError):
            continue
    return cards


def pending_count(session_id: str) -> int:
    return len(_json_files(paths.pending_for(session_id)))


def _find(session_id: str, postcard_id: str) -> tuple[Path, Postcard] | None:
    for p in _json_files(paths.pending_for(session_id)):
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        pid = data.get("id", "")
        if pid == postcard_id or pid.startswith(postcard_id):
            try:
                return p, Postcard(**data)
            except TypeError:
                return None
    return None


def file_to_todo(
    session_id: str,
    reader_address: str,
    postcard_id: str,
    todo_path: Path | None = None,
) -> Postcard | None:
    """Append a pending postcard to TODO.md, archive it, and emit a file receipt."""
    found = _find(session_id, postcard_id)
    if found is None:
        return None
    path, card = found
    _append_todo(todo_path or (Path.cwd() / "TODO.md"), [card])
    _move_to_read(session_id, path)
    ledger.write_receipt(card.id, "file", reader_address, session_id)
    return card


def surface(
    session_id: str,
    reader_address: str,
    postcard_id: str,
) -> Postcard | None:
    """Mark a pending postcard as surfaced to the main agent and emit a surface receipt."""
    found = _find(session_id, postcard_id)
    if found is None:
        return None
    path, card = found
    _move_to_read(session_id, path)
    ledger.write_receipt(card.id, "surface", reader_address, session_id)
    return card


def _move_to_read(session_id: str, path: Path) -> None:
    dest = paths.archive_for(session_id)
    dest.mkdir(parents=True, exist_ok=True)
    path.rename(dest / path.name)


def _append_todo(todo: Path, cards: list[Postcard]) -> None:
    existing = todo.read_text() if todo.exists() else ""
    lines: list[str] = []
    if TODO_HEADER not in existing:
        if existing and not existing.endswith("\n"):
            lines.append("")
        lines.append(TODO_HEADER)
    for pc in cards:
        lines.append(f"- [ ] **{pc.title}** — from `{pc.sender}` ({pc.sent_at})")
        for bline in pc.body.splitlines():
            lines.append(f"  > {bline}")
    sep = "\n" if existing and not existing.endswith("\n") else ""
    todo.write_text(existing + sep + "\n".join(lines) + "\n")
