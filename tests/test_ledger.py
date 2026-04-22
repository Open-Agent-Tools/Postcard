import pytest

from oat_postcard import ledger


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
