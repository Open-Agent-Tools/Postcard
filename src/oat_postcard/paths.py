from pathlib import Path

ROOT = Path.home() / ".oat-postcard"
DIRECTORY_DIR = ROOT / "directory"
POSTCARDS_DIR = ROOT / "postcards"
INBOX_DIR = ROOT / "inbox"
DROPBOX_DIR = ROOT / "dropbox"
SESSIONS_DIR = ROOT / "sessions"


def ensure_root() -> None:
    for d in (ROOT, DIRECTORY_DIR, POSTCARDS_DIR, INBOX_DIR, DROPBOX_DIR, SESSIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def inbox_for(address: str) -> Path:
    return INBOX_DIR / address


def read_dir_for(address: str) -> Path:
    return INBOX_DIR / address / ".read"
