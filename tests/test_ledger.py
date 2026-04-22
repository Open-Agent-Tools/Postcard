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


def test_send_with_reply_to_round_trips(tmp_root):
    parent = ledger.send("alpha", "bravo", "hi", "parent")
    child = ledger.send("bravo", "alpha", "Re: hi", "response", reply_to=parent.id)
    assert child.reply_to == parent.id
    cards = ledger.log()
    assert any(c.id == child.id and c.reply_to == parent.id for c in cards)


def test_get_postcard_full_and_prefix(tmp_root):
    pc = ledger.send("alpha", "bravo", "t", "b")
    assert ledger.get_postcard(pc.id) == pc
    assert ledger.get_postcard(pc.id[:8]) == pc
    assert ledger.get_postcard("nope-does-not-exist") is None
    assert ledger.get_postcard("") is None


def test_inbox_for_address_filters_recipient(tmp_root):
    ledger.send("alpha", "bravo", "t1", "b")
    ledger.send("alpha", "charlie", "t2", "b")
    ledger.send("delta", "bravo", "t3", "b")
    bravo = ledger.inbox_for_address("bravo")
    assert len(bravo) == 2
    assert {pc.title for pc in bravo} == {"t1", "t3"}


def test_inbox_for_address_respects_limit(tmp_root):
    for i in range(3):
        ledger.send("alpha", "bravo", f"t{i}", "b")
    assert len(ledger.inbox_for_address("bravo", limit=2)) == 2


def test_postcard_loads_without_reply_to_field(tmp_root):
    import json as _json

    ledger.init_ledger()
    # Simulate a pre-0.3.0 record: write JSON without reply_to, then commit
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    legacy = {
        "id": "deadbeef" + "0" * 24,
        "sender": "alpha",
        "recipient": "bravo",
        "title": "legacy",
        "body": "old",
        "sent_at": now.isoformat(timespec="seconds"),
    }
    relpath = ledger._postcard_relpath(now, legacy["id"])
    dest = paths.POSTCARDS_DIR / relpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_json.dumps(legacy, indent=2))
    ledger._git("add", str(relpath), cwd=paths.POSTCARDS_DIR)
    ledger._git("commit", "--quiet", "-m", "legacy", cwd=paths.POSTCARDS_DIR)

    cards = ledger.log()
    legacy_card = next(c for c in cards if c.id == legacy["id"])
    assert legacy_card.reply_to is None
    assert legacy_card.title == "legacy"
