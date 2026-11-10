import os

from oat_postcard import directory, session


def test_init_session_creates_address_and_directory_entry(tmp_root, session_env):
    addr = session.init_session(cwd=tmp_root)
    assert addr.count("-") == 2
    assert session.current_address() == addr
    entry = directory.resolve(addr)
    assert entry is not None
    assert entry.session_id == session_env


def test_init_session_is_idempotent(tmp_root, session_env):
    a = session.init_session()
    b = session.init_session()
    assert a == b


def test_end_session_removes_entry(tmp_root, session_env):
    addr = session.init_session()
    session.end_session()
    assert directory.resolve(addr) is None
    assert session.current_address() is None


def test_resolve_or_init(tmp_root, session_env):
    addr = session.resolve_or_init()
    assert session.current_address() == addr
    assert session.resolve_or_init() == addr


def test_resolve_by_pid_chain_finds_ancestor(tmp_root, monkeypatch):
    from pathlib import Path

    directory.register(
        "pid-chain-addr",
        session_id="pid-chain-sess",
        pid=os.getpid(),
        cwd=Path("/tmp"),
    )
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("OAT_POSTCARD_SESSION", raising=False)
    assert session.current_session_id() == "pid-chain-sess"


def test_resolve_by_pid_chain_returns_none_when_no_match(tmp_root, monkeypatch):
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("OAT_POSTCARD_SESSION", raising=False)
    assert session._resolve_by_pid_chain() is None


def test_current_session_id_from_codex_and_grok_env(tmp_root, monkeypatch):
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-root")
    monkeypatch.setenv("CODEX_THREAD_ID", "codex-sub")
    assert session.current_session_id() == "codex-root"
    monkeypatch.delenv("CODEX_SESSION_ID")
    assert session.current_session_id() == "codex-sub"
    monkeypatch.delenv("CODEX_THREAD_ID")
    monkeypatch.setenv("GROK_SESSION_ID", "grok-1")
    assert session.current_session_id() == "grok-1"


def test_init_session_records_detected_host(tmp_root, monkeypatch):
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("GROK_SESSION_ID", "grok-1")
    addr = session.init_session()
    assert directory.resolve(addr).host == "grok"
