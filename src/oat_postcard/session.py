import os
import subprocess
from pathlib import Path

from . import addressing, directory, paths


def current_session_id() -> str:
    sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("OAT_POSTCARD_SESSION")
    if sid:
        return sid
    try:
        tty = subprocess.check_output(["tty"], stderr=subprocess.DEVNULL, text=True).strip()
        if tty and tty != "not a tty":
            return f"tty:{tty}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    raise RuntimeError(
        "no session id: set CLAUDE_SESSION_ID or run from a terminal with a TTY"
    )


def _sidecar(session_id: str) -> Path:
    safe = session_id.replace("/", "_")
    return paths.SESSIONS_DIR / f"{safe}.addr"


def current_address() -> str | None:
    paths.ensure_root()
    try:
        sid = current_session_id()
    except RuntimeError:
        return None
    f = _sidecar(sid)
    if not f.exists():
        return None
    return f.read_text().strip() or None


def init_session(session_id: str | None = None, cwd: Path | None = None) -> str:
    paths.ensure_root()
    sid = session_id or current_session_id()
    f = _sidecar(sid)
    if f.exists():
        return f.read_text().strip()
    for _ in range(64):
        addr = addressing.generate_address()
        if directory.resolve(addr) is None:
            break
    else:
        raise RuntimeError("could not find a free address after 64 tries")
    f.write_text(addr + "\n")
    directory.register(addr, session_id=sid, pid=os.getppid(), cwd=cwd or Path.cwd())
    return addr


def end_session(session_id: str | None = None) -> None:
    paths.ensure_root()
    sid = session_id or current_session_id()
    f = _sidecar(sid)
    if not f.exists():
        return
    addr = f.read_text().strip()
    directory.unregister(addr)
    f.unlink(missing_ok=True)


def resolve_or_init() -> str:
    return current_address() or init_session()
