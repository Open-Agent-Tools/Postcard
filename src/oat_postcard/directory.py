from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import paths

UNKNOWN_HOST = "unknown"


@dataclass
class Entry:
    address: str
    session_id: str
    pid: int
    cwd: str
    started_at: str
    host: str = UNKNOWN_HOST


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


def _load(data: dict) -> Entry:
    """Build an Entry, tolerating fields added in later versions."""
    known = {f for f in Entry.__dataclass_fields__}
    return Entry(**{k: v for k, v in data.items() if k in known})


def register(
    address: str,
    session_id: str,
    pid: int,
    cwd: Path,
    host: str = UNKNOWN_HOST,
) -> Entry:
    paths.ensure_root()
    entry = Entry(
        address=address,
        session_id=session_id,
        pid=pid,
        cwd=str(cwd),
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        host=host,
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
        return _load(data)
    except (json.JSONDecodeError, OSError, TypeError):
        return None


def is_active(address: str) -> bool:
    return any(e.address == address for e in list_active())


def list_active(prune: bool = True) -> list[Entry]:
    paths.ensure_root()
    entries: list[Entry] = []
    for p in sorted(paths.DIRECTORY_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            e = _load(data)
        except (json.JSONDecodeError, OSError, TypeError):
            continue
        if not _pid_alive(e.pid):
            if prune:
                p.unlink(missing_ok=True)
            continue
        entries.append(e)
    return entries
