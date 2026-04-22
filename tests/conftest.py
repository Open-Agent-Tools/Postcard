import pytest

from oat_postcard import paths


@pytest.fixture
def tmp_root(tmp_path, monkeypatch):
    root = tmp_path / "oat-postcard"
    monkeypatch.setattr(paths, "ROOT", root)
    monkeypatch.setattr(paths, "DIRECTORY_DIR", root / "directory")
    monkeypatch.setattr(paths, "POSTCARDS_DIR", root / "postcards")
    monkeypatch.setattr(paths, "INBOX_DIR", root / "inbox")
    monkeypatch.setattr(paths, "DROPBOX_DIR", root / "dropbox")
    monkeypatch.setattr(paths, "SESSIONS_DIR", root / "sessions")
    monkeypatch.setattr(paths, "PENDING_DIR", root / "pending")
    paths.ensure_root()
    yield root


@pytest.fixture
def session_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session-A")
    return "test-session-A"
