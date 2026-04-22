from oat_postcard import clerk, ledger, paths

READER_ADDR = "test-reader-addr"
SID = "sess-B"


def test_sweep_moves_inbox_to_pending(tmp_root):
    ledger.send("alpha", "bravo", "hi", "body")
    assert any(paths.inbox_for("bravo").iterdir())
    n = clerk.sweep("bravo", session_id=SID)
    assert n == 1
    assert list(paths.inbox_for("bravo").iterdir()) == []
    assert len(list(paths.pending_for(SID).glob("*.json"))) == 1


def test_pending_lists_staged(tmp_root):
    ledger.send("alpha", "bravo", "hi", "body")
    clerk.sweep("bravo", session_id=SID)
    cards = clerk.pending(SID)
    assert len(cards) == 1
    assert cards[0].title == "hi"


def test_pending_count(tmp_root):
    assert clerk.pending_count(SID) == 0
    ledger.send("alpha", "bravo", "1", "b")
    ledger.send("alpha", "bravo", "2", "b")
    clerk.sweep("bravo", session_id=SID)
    assert clerk.pending_count(SID) == 2


def test_file_to_todo_appends_and_archives(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "short note")
    clerk.sweep("bravo", session_id=SID)
    todo = tmp_path / "TODO.md"
    result = clerk.file_to_todo(SID, READER_ADDR, pc.id, todo_path=todo)
    assert result is not None
    assert "ping" in todo.read_text()
    assert clerk.pending_count(SID) == 0
    assert (paths.archive_for(SID) / f"{pc.sent_at}-{pc.id[:8]}.json").exists()


def test_file_by_id_prefix(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "b")
    clerk.sweep("bravo", session_id=SID)
    todo = tmp_path / "TODO.md"
    assert clerk.file_to_todo(SID, READER_ADDR, pc.id[:8], todo_path=todo) is not None


def test_surface_without_filing(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "b")
    clerk.sweep("bravo", session_id=SID)
    todo = tmp_path / "TODO.md"
    assert clerk.surface(SID, READER_ADDR, pc.id) is not None
    assert not todo.exists()
    assert clerk.pending_count(SID) == 0


def test_unknown_id_returns_none(tmp_root):
    assert clerk.file_to_todo(SID, READER_ADDR, "nope") is None
    assert clerk.surface(SID, READER_ADDR, "nope") is None


def test_file_writes_receipt(tmp_root, tmp_path):
    pc = ledger.send("alpha", "bravo", "ping", "b")
    clerk.sweep("bravo", session_id=SID)
    clerk.file_to_todo(SID, READER_ADDR, pc.id, todo_path=tmp_path / "TODO.md")
    receipt = ledger.receipt_for(pc.id)
    assert receipt is not None
    assert receipt.action == "file"
    assert receipt.reader_address == READER_ADDR
    assert receipt.reader_session_id == SID


def test_surface_writes_receipt(tmp_root):
    pc = ledger.send("alpha", "bravo", "ping", "b")
    clerk.sweep("bravo", session_id=SID)
    clerk.surface(SID, READER_ADDR, pc.id)
    receipt = ledger.receipt_for(pc.id)
    assert receipt is not None
    assert receipt.action == "surface"


def test_unknown_id_does_not_emit_receipt(tmp_root):
    clerk.surface(SID, READER_ADDR, "no-such-id")
    assert ledger.receipts() == []


def test_sweep_then_file_then_sweep_again(tmp_root, tmp_path):
    ledger.send("alpha", "bravo", "first", "a")
    clerk.sweep("bravo", session_id=SID)
    pc1 = clerk.pending(SID)[0]
    clerk.file_to_todo(SID, READER_ADDR, pc1.id, todo_path=tmp_path / "TODO.md")

    ledger.send("alpha", "bravo", "second", "b")
    clerk.sweep("bravo", session_id=SID)
    assert clerk.pending_count(SID) == 1
    assert clerk.pending(SID)[0].title == "second"
