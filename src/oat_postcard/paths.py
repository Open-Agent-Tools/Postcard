from pathlib import Path

ROOT = Path.home() / ".oat-postcard"
DIRECTORY_DIR = ROOT / "directory"
POSTCARDS_DIR = ROOT / "postcards"
INBOX_DIR = ROOT / "inbox"
DROPBOX_DIR = ROOT / "dropbox"
SESSIONS_DIR = ROOT / "sessions"
PENDING_DIR = ROOT / "pending"


def ensure_root() -> None:
    for d in (ROOT, DIRECTORY_DIR, POSTCARDS_DIR, INBOX_DIR, DROPBOX_DIR, SESSIONS_DIR, PENDING_DIR):
        d.mkdir(parents=True, exist_ok=True)


def inbox_for(address: str) -> Path:
    return INBOX_DIR / address


def pending_for(session_id: str) -> Path:
    safe = session_id.replace("/", "_")
    return PENDING_DIR / safe


def archive_for(session_id: str) -> Path:
    return pending_for(session_id) / ".read"
