from oat_postcard import clerk, ledger


def test_check_inbox_lists_pending(tmp_root):
    ledger.send("alpha", "bravo", "hi", "body")
    pending = clerk.check_inbox("bravo")
    assert len(pending) == 1
    assert pending[0].title == "hi"


def test_relay_appends_to_todo_and_clears_inbox(tmp_root, tmp_path):
    ledger.send("alpha", "bravo", "ping", "short note")
    todo = tmp_path / "TODO.md"
    count = clerk.relay("bravo", todo_path=todo)
    assert count == 1
    text = todo.read_text()
    assert "## Postcards" in text
    assert "ping" in text
    assert "short note" in text
    assert clerk.check_inbox("bravo") == []


def test_relay_no_mail_no_op(tmp_root, tmp_path):
    todo = tmp_path / "TODO.md"
    assert clerk.relay("ghost", todo_path=todo) == 0
    assert not todo.exists()


def test_relay_appends_without_duplicating_header(tmp_root, tmp_path):
    todo = tmp_path / "TODO.md"
    ledger.send("alpha", "bravo", "first", "one")
    clerk.relay("bravo", todo_path=todo)
    ledger.send("alpha", "bravo", "second", "two")
    clerk.relay("bravo", todo_path=todo)
    assert todo.read_text().count("## Postcards") == 1
    assert "first" in todo.read_text()
    assert "second" in todo.read_text()
