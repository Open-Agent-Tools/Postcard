import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import addressing, directory, paths

STALE_DROPBOX_SECONDS = 5 * 60


@dataclass
class CleanupResult:
    directory: int = 0
    sidecars: int = 0
    pending: int = 0
    inbox: int = 0
    dropbox: int = 0

    def total(self) -> int:
        return self.directory + self.sidecars + self.pending + self.inbox + self.dropbox


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
    cleanup()
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
    if f.exists():
        addr = f.read_text().strip()
        directory.unregister(addr)
        f.unlink(missing_ok=True)
    pending = paths.pending_for(sid)
    if pending.exists():
        shutil.rmtree(pending, ignore_errors=True)


def resolve_or_init() -> str:
    return current_address() or init_session()


def cleanup(dry_run: bool = False) -> CleanupResult:
    paths.ensure_root()
    result = CleanupResult()

    live_entries = directory.list_active(prune=False)
    live_paths = {paths.DIRECTORY_DIR / f"{e.address}.json" for e in live_entries}
    dead_paths = [p for p in paths.DIRECTORY_DIR.glob("*.json") if p not in live_paths]
    result.directory = len(dead_paths)
    if not dry_run:
        for p in dead_paths:
            p.unlink(missing_ok=True)

    live_sids = {e.session_id for e in live_entries}
    live_addrs = {e.address for e in live_entries}

    expected_sidecars = {_sidecar(sid) for sid in live_sids}
    for sc in paths.SESSIONS_DIR.glob("*.addr"):
        if sc not in expected_sidecars:
            if not dry_run:
                sc.unlink(missing_ok=True)
            result.sidecars += 1

    expected_pending = {paths.pending_for(sid) for sid in live_sids}
    if paths.PENDING_DIR.exists():
        for pd in paths.PENDING_DIR.iterdir():
            if pd.is_dir() and pd not in expected_pending:
                if not dry_run:
                    shutil.rmtree(pd, ignore_errors=True)
                result.pending += 1

    if paths.INBOX_DIR.exists():
        for ib in paths.INBOX_DIR.iterdir():
            if ib.is_dir() and ib.name not in live_addrs:
                if not dry_run:
                    shutil.rmtree(ib, ignore_errors=True)
                result.inbox += 1

    now = time.time()
    if paths.DROPBOX_DIR.exists():
        for df in paths.DROPBOX_DIR.iterdir():
            if df.is_file():
                try:
                    age = now - df.stat().st_mtime
                except OSError:
                    continue
                if age > STALE_DROPBOX_SECONDS:
                    if not dry_run:
                        df.unlink(missing_ok=True)
                    result.dropbox += 1

    return result
