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


def test_register_records_host_and_defaults_to_unknown(tmp_root):
    directory.register("h", session_id="s", pid=1, cwd=Path("/tmp"), host="codex")
    assert directory.resolve("h").host == "codex"
    directory.register("u", session_id="s2", pid=1, cwd=Path("/tmp"))
    assert directory.resolve("u").host == directory.UNKNOWN_HOST


def test_pre_0_5_entry_without_host_still_loads(tmp_root):
    import json

    from oat_postcard import paths

    (paths.DIRECTORY_DIR / "old.json").write_text(
        json.dumps(
            {
                "address": "old",
                "session_id": "s-old",
                "pid": 1,
                "cwd": "/tmp",
                "started_at": "2026-01-01T00:00:00+00:00",
            }
        )
    )
    e = directory.resolve("old")
    assert e is not None and e.host == directory.UNKNOWN_HOST
    assert "old" in {x.address for x in directory.list_active()}


def test_entry_with_unknown_future_field_is_tolerated(tmp_root):
    import json

    from oat_postcard import paths

    (paths.DIRECTORY_DIR / "new.json").write_text(
        json.dumps(
            {
                "address": "new",
                "session_id": "s-new",
                "pid": 1,
                "cwd": "/tmp",
                "started_at": "2026-01-01T00:00:00+00:00",
                "host": "claude",
                "from_the_future": True,
            }
        )
    )
    assert directory.resolve("new") is not None
