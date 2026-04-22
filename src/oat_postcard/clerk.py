import json
from pathlib import Path

from . import paths
from .ledger import Postcard

TODO_HEADER = "## Postcards"


def _pending_files(address: str) -> list[Path]:
    inbox = paths.inbox_for(address)
    if not inbox.exists():
        return []
    return sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix == ".json")


def check_inbox(address: str) -> list[Postcard]:
    cards: list[Postcard] = []
    for p in _pending_files(address):
        try:
            cards.append(Postcard(**json.loads(p.read_text())))
        except (json.JSONDecodeError, OSError, TypeError):
            continue
    return cards


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
    todo.write_text(existing + ("\n" if existing and not existing.endswith("\n") else "") + "\n".join(lines) + "\n")


def relay(address: str, todo_path: Path | None = None) -> int:
    cards = check_inbox(address)
    if not cards:
        return 0
    todo = todo_path or (Path.cwd() / "TODO.md")
    _append_todo(todo, cards)

    read_dir = paths.read_dir_for(address)
    read_dir.mkdir(parents=True, exist_ok=True)
    for p in _pending_files(address):
        p.rename(read_dir / p.name)
    return len(cards)
