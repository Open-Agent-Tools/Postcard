import time
from pathlib import Path

from oat_postcard import clerk, directory, ledger, paths, session


def test_end_session_removes_pending(tmp_root, session_env):
    addr = session.init_session()
    ledger.send("other", addr, "hi", "body")
    clerk.sweep(addr, session_id=session_env)
    assert clerk.pending_count(session_env) == 1

    session.end_session()
    assert not paths.pending_for(session_env).exists()


def test_cleanup_prunes_dead_directory_entries(tmp_root):
    directory.register("alive", session_id="s-alive", pid=1, cwd=Path("/tmp"))
    directory.register("dead", session_id="s-dead", pid=999_999, cwd=Path("/tmp"))

    r = session.cleanup()
    assert r.directory == 1
    assert directory.resolve("dead") is None
    assert directory.resolve("alive") is not None


def test_cleanup_prunes_orphan_sidecars(tmp_root):
    (paths.SESSIONS_DIR / "orphan-session.addr").write_text("ghost-address\n")

    r = session.cleanup()
    assert r.sidecars == 1
    assert not (paths.SESSIONS_DIR / "orphan-session.addr").exists()


def test_cleanup_keeps_live_sidecar(tmp_root):
    directory.register("live-addr", session_id="s-live", pid=1, cwd=Path("/tmp"))
    sc = paths.SESSIONS_DIR / "s-live.addr"
    sc.write_text("live-addr\n")

    r = session.cleanup()
    assert r.sidecars == 0
    assert sc.exists()


def test_cleanup_prunes_orphan_pending_dirs(tmp_root):
    orphan = paths.pending_for("s-orphan")
    orphan.mkdir(parents=True)
    (orphan / "stale.json").write_text("{}")

    r = session.cleanup()
    assert r.pending == 1
    assert not orphan.exists()


def test_cleanup_keeps_live_pending(tmp_root):
    directory.register("live-addr", session_id="s-live", pid=1, cwd=Path("/tmp"))
    live_pending = paths.pending_for("s-live")
    live_pending.mkdir(parents=True)

    r = session.cleanup()
    assert r.pending == 0
    assert live_pending.exists()


def test_cleanup_prunes_orphan_inbox_dirs(tmp_root):
    orphan_inbox = paths.inbox_for("ghost-addr")
    orphan_inbox.mkdir(parents=True)
    (orphan_inbox / "stale.json").write_text("{}")

    r = session.cleanup()
    assert r.inbox == 1
    assert not orphan_inbox.exists()


def test_cleanup_keeps_live_inbox(tmp_root):
    directory.register("live-addr", session_id="s-live", pid=1, cwd=Path("/tmp"))
    live_inbox = paths.inbox_for("live-addr")
    live_inbox.mkdir(parents=True)

    r = session.cleanup()
    assert r.inbox == 0
    assert live_inbox.exists()


def test_cleanup_prunes_stale_dropbox_temps(tmp_root):
    stale = paths.DROPBOX_DIR / ".pc-stale.json"
    stale.write_text("{}")
    old = time.time() - (session.STALE_DROPBOX_SECONDS + 60)
    import os
    os.utime(stale, (old, old))

    fresh = paths.DROPBOX_DIR / ".pc-fresh.json"
    fresh.write_text("{}")

    r = session.cleanup()
    assert r.dropbox == 1
    assert not stale.exists()
    assert fresh.exists()


def test_cleanup_dry_run_reports_but_does_not_remove(tmp_root):
    (paths.SESSIONS_DIR / "orphan.addr").write_text("ghost\n")

    r = session.cleanup(dry_run=True)
    assert r.sidecars == 1
    assert (paths.SESSIONS_DIR / "orphan.addr").exists()


def test_init_session_runs_cleanup(tmp_root, session_env):
    (paths.SESSIONS_DIR / "orphan.addr").write_text("ghost\n")

    session.init_session()
    assert not (paths.SESSIONS_DIR / "orphan.addr").exists()
