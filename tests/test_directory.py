from pathlib import Path

from oat_postcard import directory


def test_register_and_resolve(tmp_root):
    entry = directory.register(
        "sweet-blue-gate", session_id="s1", pid=1, cwd=Path("/tmp")
    )
    assert entry.address == "sweet-blue-gate"
    found = directory.resolve("sweet-blue-gate")
    assert found is not None
    assert found.session_id == "s1"


def test_list_prunes_dead_pids(tmp_root):
    directory.register("alive", session_id="s1", pid=1, cwd=Path("/tmp"))
    directory.register("dead", session_id="s2", pid=999_999, cwd=Path("/tmp"))
    addrs = {e.address for e in directory.list_active()}
    assert "alive" in addrs
    assert "dead" not in addrs


def test_unregister(tmp_root):
    directory.register("x", session_id="s", pid=1, cwd=Path("/tmp"))
    directory.unregister("x")
    assert directory.resolve("x") is None
