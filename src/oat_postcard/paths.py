import os
from pathlib import Path


def _root() -> Path:
    """State root. ``OAT_POSTCARD_HOME`` overrides the default so sandboxed
    hosts (Codex workspace-write, Grok workspace sandbox) can point it at a
    writable location."""
    override = os.environ.get("OAT_POSTCARD_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".oat-postcard"


ROOT = _root()
DIRECTORY_DIR = ROOT / "directory"
POSTCARDS_DIR = ROOT / "postcards"
INBOX_DIR = ROOT / "inbox"
DROPBOX_DIR = ROOT / "dropbox"
SESSIONS_DIR = ROOT / "sessions"
PENDING_DIR = ROOT / "pending"


def ensure_root() -> None:
    for d in (
        ROOT,
        DIRECTORY_DIR,
        POSTCARDS_DIR,
        INBOX_DIR,
        DROPBOX_DIR,
        SESSIONS_DIR,
        PENDING_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def inbox_for(address: str) -> Path:
    return INBOX_DIR / address


def pending_for(session_id: str) -> Path:
    safe = session_id.replace("/", "_")
    return PENDING_DIR / safe


def archive_for(session_id: str) -> Path:
    return pending_for(session_id) / ".read"
