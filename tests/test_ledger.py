import pytest

from oat_postcard import ledger, paths


def test_init_ledger_is_idempotent(tmp_root):
    ledger.init_ledger()
    ledger.init_ledger()
    assert (tmp_root / "postcards" / ".git").is_dir()


def test_send_and_log_roundtrip(tmp_root):
    pc = ledger.send("alpha-red-river", "bravo-blue-gate", "hello", "world")
    cards = ledger.log()
    assert len(cards) == 1
    assert cards[0].id == pc.id
    assert cards[0].title == "hello"
    assert cards[0].body == "world"


def test_send_rejects_oversize_title(tmp_root):
    with pytest.raises(ValueError):
        ledger.send("a", "b", "x" * 200, "ok")


def test_send_rejects_oversize_body(tmp_root):
    with pytest.raises(ValueError):
        ledger.send("a", "b", "t", "x" * 2000)


def test_send_populates_recipient_inbox(tmp_root):
    ledger.send("alpha", "bravo", "hi", "there")
    inbox = tmp_root / "inbox" / "bravo"
    assert inbox.exists()
    assert any(inbox.iterdir())


def test_log_limit(tmp_root):
    for i in range(3):
        ledger.send("a", "b", f"t{i}", "body")
    assert len(ledger.log(limit=2)) == 2


def test_write_receipt_commits_and_reads_back(tmp_root):
    pc = ledger.send("alpha", "bravo", "hi", "body")
    r = ledger.write_receipt(
        pc.id, "file", reader_address="bravo", reader_session_id="sess-B"
    )
    assert r.postcard_id == pc.id
    assert r.action == "file"
    back = ledger.receipt_for(pc.id)
    assert back == r
    receipt_file = paths.POSTCARDS_DIR / "receipts" / f"{pc.id}.json"
    assert receipt_file.exists()


def test_receipts_lists_only_receipts(tmp_root):
    pc1 = ledger.send("a", "b", "t1", "body")
    pc2 = ledger.send("a", "b", "t2", "body")
    ledger.write_receipt(pc1.id, "file", "b", "sess")
    ledger.write_receipt(pc2.id, "surface", "b", "sess")
    rs = ledger.receipts()
    assert len(rs) == 2
    assert {r.action for r in rs} == {"file", "surface"}


def test_log_excludes_receipts(tmp_root):
    pc = ledger.send("a", "b", "t", "body")
    ledger.write_receipt(pc.id, "file", "b", "sess")
    cards = ledger.log()
    assert len(cards) == 1
    assert cards[0].id == pc.id


def test_write_receipt_rejects_unknown_action(tmp_root):
    pc = ledger.send("a", "b", "t", "body")
    with pytest.raises(ValueError):
        ledger.write_receipt(pc.id, "ignored", "b", "sess")


def test_receipts_limit(tmp_root):
    for i in range(3):
        pc = ledger.send("a", "b", f"t{i}", "body")
        ledger.write_receipt(pc.id, "file", "b", "sess")
    assert len(ledger.receipts(limit=2)) == 2


def test_receipt_for_missing(tmp_root):
    assert ledger.receipt_for("nonexistent") is None
