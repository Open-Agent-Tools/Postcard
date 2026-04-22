from oat_postcard import clerk, ledger, paths


def test_sweep_moves_inbox_to_pending(tmp_root):
    ledger.send("alpha", "bravo", "hi", "body")
    assert any(paths.inbox_for("bravo").iterdir())
    n = clerk.sweep("bravo", session_id="sess-B")
    assert n == 1
    assert list(paths.inbox_for("bravo").iterdir()) == []
    assert len(list(paths.pending_for("sess-B").glob("*.json"))) == 1


def test_pending_lists_staged(tmp_root):
    ledger.send("alpha", "bravo", "hi", "body")
    clerk.sweep("bravo", session_id="sess-B")
    cards = clerk.pending("sess-B")
    assert len(cards) == 1
    assert cards[0].title == "hi"


def test_pending_count(tmp_root):
    assert clerk.pending_count("sess-B") == 0
    ledger.send("alpha", "bravo", "1", "b")
    ledger.send("alpha", "bravo", "2", "b")
    clerk.sweep("bravo", session_id="sess-B")
    assert clerk.pending_count("sess-B") == 2


def test_file_to_todo_appends_and_archives(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "short note")
    clerk.sweep("bravo", session_id="sess-B")
    todo = tmp_path / "TODO.md"
    result = clerk.file_to_todo("sess-B", pc.id, todo_path=todo)
    assert result is not None
    assert "ping" in todo.read_text()
    assert clerk.pending_count("sess-B") == 0
    assert (paths.archive_for("sess-B") / f"{pc.sent_at}-{pc.id[:8]}.json").exists()


def test_file_by_id_prefix(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "b")
    clerk.sweep("bravo", session_id="sess-B")
    todo = tmp_path / "TODO.md"
    assert clerk.file_to_todo("sess-B", pc.id[:8], todo_path=todo) is not None


def test_archive_without_filing(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "b")
    clerk.sweep("bravo", session_id="sess-B")
    todo = tmp_path / "TODO.md"
    assert clerk.archive("sess-B", pc.id) is not None
    assert not todo.exists()
    assert clerk.pending_count("sess-B") == 0


def test_unknown_id_returns_none(tmp_root):
    assert clerk.file_to_todo("sess-B", "nope") is None
    assert clerk.archive("sess-B", "nope") is None


def test_sweep_then_file_then_sweep_again(tmp_root, tmp_path):
    ledger.send("alpha", "bravo", "first", "a")
    clerk.sweep("bravo", session_id="sess-B")
    pc1 = clerk.pending("sess-B")[0]
    clerk.file_to_todo("sess-B", pc1.id, todo_path=tmp_path / "TODO.md")

    ledger.send("alpha", "bravo", "second", "b")
    clerk.sweep("bravo", session_id="sess-B")
    assert clerk.pending_count("sess-B") == 1
    assert clerk.pending("sess-B")[0].title == "second"
