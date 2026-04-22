from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import paths


@dataclass
class Entry:
    address: str
    session_id: str
    pid: int
    cwd: str
    started_at: str


def _entry_path(address: str) -> Path:
    return paths.DIRECTORY_DIR / f"{address}.json"


def _write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def register(address: str, session_id: str, pid: int, cwd: Path) -> Entry:
    paths.ensure_root()
    entry = Entry(
        address=address,
        session_id=session_id,
        pid=pid,
        cwd=str(cwd),
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    _write_atomic(_entry_path(address), asdict(entry))
    return entry


def unregister(address: str) -> None:
    _entry_path(address).unlink(missing_ok=True)


def resolve(address: str) -> Entry | None:
    p = _entry_path(address)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return Entry(**data)


def is_active(address: str) -> bool:
    return any(e.address == address for e in list_active())


def list_active(prune: bool = True) -> list[Entry]:
    paths.ensure_root()
    entries: list[Entry] = []
    for p in sorted(paths.DIRECTORY_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            e = Entry(**data)
        except (json.JSONDecodeError, OSError, TypeError):
            continue
        if not _pid_alive(e.pid):
            if prune:
                p.unlink(missing_ok=True)
            continue
        entries.append(e)
    return entries
