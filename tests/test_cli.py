from datetime import datetime, timezone

import pytest

from oat_postcard import cli, ledger, session


def test_parse_time_window_accepts_shorthand():
    now = datetime.now(timezone.utc)
    since = cli._parse_time_window("1h")
    assert (now - since).total_seconds() == pytest.approx(3600, abs=5)

    since = cli._parse_time_window("7d")
    assert (now - since).total_seconds() == pytest.approx(7 * 86400, abs=5)


def test_parse_time_window_accepts_iso():
    ts = cli._parse_time_window("2026-01-01T00:00:00+00:00")
    assert ts.year == 2026 and ts.month == 1 and ts.day == 1


def test_parse_time_window_rejects_garbage():
    with pytest.raises(ValueError):
        cli._parse_time_window("not a duration")


def test_reply_title_prefixes_re():
    assert cli._reply_title("hello").startswith("Re: ")
    assert cli._reply_title("Re: hello") == "Re: hello"


def test_reply_title_truncates_to_max():
    long = "x" * 200
    out = cli._reply_title(long)
    assert len(out) == ledger.TITLE_MAX


def test_reply_cmd_sends_with_reply_to(tmp_root, session_env, capsys):
    me = session.init_session()
    parent = ledger.send("peer", me, "parent title", "parent body")

    rc = cli.main(["reply", parent.id[:8], "acknowledged"])
    assert rc == 0

    out = capsys.readouterr().out
    assert "reply to" in out and parent.id[:8] in out

    cards = ledger.log()
    child = next(c for c in cards if c.reply_to == parent.id)
    assert child.recipient == "peer"
    assert child.title == "Re: parent title"
    assert child.body == "acknowledged"


def test_reply_cmd_errors_on_missing_parent(tmp_root, session_env, capsys):
    session.init_session()
    rc = cli.main(["reply", "deadbeef", "body"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no postcard matching" in err


def test_inbox_cmd_lists_mail_for_this_session(tmp_root, session_env, capsys):
    me = session.init_session()
    ledger.send("peer", me, "first", "one")
    ledger.send("peer", me, "second", "two")
    ledger.send("peer", "someone-else", "skip", "nope")

    rc = cli.main(["inbox", "--limit", "10"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "first" in out and "second" in out
    assert "skip" not in out


def test_inbox_cmd_empty(tmp_root, session_env, capsys):
    session.init_session()
    rc = cli.main(["inbox"])
    assert rc == 0
    assert "(no inbox)" in capsys.readouterr().out


def test_inbox_cmd_shows_reply_marker(tmp_root, session_env, capsys):
    me = session.init_session()
    parent = ledger.send("peer", me, "parent", "body")
    ledger.send("peer", me, "Re: parent", "reply body", reply_to=parent.id)

    rc = cli.main(["inbox"])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"↳{parent.id[:8]}" in out


def test_log_since_filters_by_time(tmp_root, session_env, capsys):
    ledger.send("alpha", "bravo", "recent", "body")

    rc = cli.main(["log", "--since", "1h"])
    assert rc == 0
    assert "recent" in capsys.readouterr().out


def test_log_until_excludes_recent(tmp_root, session_env, capsys):
    ledger.send("alpha", "bravo", "too-new", "body")

    rc = cli.main(["log", "--until", "1h"])
    assert rc == 0
    assert "(no matching postcards)" in capsys.readouterr().out


def test_log_rejects_bad_time_spec(tmp_root, session_env, capsys):
    rc = cli.main(["log", "--since", "not a real duration"])
    assert rc == 2
    assert "invalid time spec" in capsys.readouterr().err


def test_send_oversized_body_returns_clean_error(tmp_root, session_env, capsys):
    session.init_session()
    big = "x" * (ledger.BODY_MAX + 1)
    rc = cli.main(["send", "peer", "short title", big])
    assert rc == 1
    err = capsys.readouterr().err
    assert "body exceeds" in err
    assert "Traceback" not in err


def test_send_oversized_title_returns_clean_error(tmp_root, session_env, capsys):
    session.init_session()
    rc = cli.main(["send", "peer", "x" * (ledger.TITLE_MAX + 1), "body"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "title exceeds" in err
    assert "Traceback" not in err
