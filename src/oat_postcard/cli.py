from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__

_DURATION_RE = re.compile(r"(?i)^\s*(\d+)\s*([smhd])\s*$")


def _parse_time_window(spec: str) -> datetime:
    m = _DURATION_RE.match(spec)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        delta = {
            "s": timedelta(seconds=n),
            "m": timedelta(minutes=n),
            "h": timedelta(hours=n),
            "d": timedelta(days=n),
        }[unit]
        return datetime.now(timezone.utc) - delta
    try:
        ts = datetime.fromisoformat(spec.strip())
    except ValueError as e:
        raise ValueError(
            f"invalid time spec {spec!r}: expected Ns/Nm/Nh/Nd or ISO timestamp"
        ) from e
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _reply_title(parent_title: str) -> str:
    from . import ledger as _ledger

    base = parent_title if parent_title.startswith("Re: ") else f"Re: {parent_title}"
    return base[: _ledger.TITLE_MAX]


def _cmd_send(args: argparse.Namespace) -> int:
    from . import directory, ledger, session

    if not args.force and not directory.is_active(args.address):
        print(
            f"error: address {args.address!r} is not in the live directory. "
            "Run 'oat-postcard directory' to see active peers; --force to "
            "send anyway.",
            file=sys.stderr,
        )
        return 1
    sender = session.resolve_or_init()
    pc = ledger.send(sender, args.address, args.title, args.body)
    print(f"sent {pc.id[:8]} to {args.address}")
    return 0


def _cmd_reply(args: argparse.Namespace) -> int:
    from . import directory, ledger, session

    parent = ledger.get_postcard(args.parent_id)
    if parent is None:
        print(f"error: no postcard matching {args.parent_id!r}", file=sys.stderr)
        return 1
    if not args.force and not directory.is_active(parent.sender):
        print(
            f"error: parent sender {parent.sender!r} is no longer in the live "
            "directory (their session has ended). Addresses are per-session "
            "and don't persist across restarts. Use --force to reply into "
            "the orphan inbox anyway.",
            file=sys.stderr,
        )
        return 1
    sender = session.resolve_or_init()
    title = _reply_title(parent.title)
    pc = ledger.send(sender, parent.sender, title, args.body, reply_to=parent.id)
    print(f"sent {pc.id[:8]} to {parent.sender} (reply to {parent.id[:8]})")
    return 0


def _cmd_inbox(args: argparse.Namespace) -> int:
    from . import ledger, session

    me = session.current_address()
    if not me:
        print("error: no session address (run session-init first)", file=sys.stderr)
        return 1

    def _fmt(pc: "ledger.Postcard") -> str:
        tag = f" ↳{pc.reply_to[:8]}" if pc.reply_to else ""
        return f"{pc.sent_at}  {pc.id[:8]}  from {pc.sender}  {pc.title}{tag}"

    cards = ledger.inbox_for_address(me, limit=args.limit)
    cards.reverse()

    for pc in cards:
        print(_fmt(pc))

    if not args.watch:
        if not cards:
            print("(no inbox)")
        return 0

    seen = {pc.id for pc in cards}
    try:
        while True:
            time.sleep(args.interval)
            current = ledger.inbox_for_address(me, limit=args.limit)
            current.reverse()
            for pc in current:
                if pc.id not in seen:
                    print(_fmt(pc), flush=True)
                    seen.add(pc.id)
    except KeyboardInterrupt:
        return 0


def _cmd_directory(args: argparse.Namespace) -> int:
    from . import directory, session

    me = session.current_address()
    entries = directory.list_active()
    if not entries:
        print("(no active agents)")
        return 0
    width = max(len(e.address) for e in entries)
    for e in entries:
        marker = "*" if e.address == me else " "
        print(f"{marker} {e.address:<{width}}  pid={e.pid:<7}  {e.cwd}")
    return 0


def _cmd_log(args: argparse.Namespace) -> int:
    from . import ledger

    try:
        since = _parse_time_window(args.since) if args.since else None
        until = _parse_time_window(args.until) if args.until else None
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    def _fmt(pc: "ledger.Postcard") -> str:
        tag = f" ↳{pc.reply_to[:8]}" if pc.reply_to else ""
        return f"{pc.sent_at}  {pc.sender} -> {pc.recipient}  {pc.title}{tag}"

    cards = ledger.log()
    filtered: list[ledger.Postcard] = []
    for pc in cards:
        if since is not None or until is not None:
            try:
                ts = datetime.fromisoformat(pc.sent_at)
            except ValueError:
                continue
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
        filtered.append(pc)
        if args.limit and len(filtered) >= args.limit:
            break

    if args.watch:
        # Tail mode: print initial window oldest-first so new arrivals
        # stream on naturally at the bottom.
        filtered.reverse()

    if not filtered:
        if not args.watch:
            print("(no matching postcards)" if (since or until) else "(ledger empty)")
    else:
        for pc in filtered:
            print(_fmt(pc))

    if not args.watch:
        return 0

    seen = {pc.id for pc in filtered}
    try:
        while True:
            time.sleep(args.interval)
            current = ledger.log()
            # ledger.log() returns newest-first; reverse to stream
            # chronologically.
            for pc in reversed(current):
                if pc.id in seen:
                    continue
                seen.add(pc.id)
                print(_fmt(pc), flush=True)
    except KeyboardInterrupt:
        return 0


def _cmd_whoami(args: argparse.Namespace) -> int:
    from . import session

    print(session.resolve_or_init())
    return 0


def _cmd_clerk_sweep(args: argparse.Namespace) -> int:
    from . import clerk, session

    sid = session.current_session_id()
    addr = session.current_address()
    if not addr:
        return 0
    n = clerk.sweep(addr, sid)
    if n and not args.quiet:
        print(f"{n} new postcard(s) staged")
    return 0


def _cmd_clerk_pending(args: argparse.Namespace) -> int:
    from . import clerk, session

    sid = session.current_session_id()
    if args.count:
        print(clerk.pending_count(sid))
        return 0
    cards = clerk.pending(sid)
    if args.json:
        print(json.dumps([asdict(c) for c in cards], indent=2, ensure_ascii=False))
        return 0
    if not cards:
        print("(no pending postcards)")
        return 0
    for c in cards:
        print(f"{c.id[:8]}  {c.sent_at}  from {c.sender}  {c.title}")
    return 0


def _reader_identity() -> tuple[str, str] | None:
    from . import session

    sid = session.current_session_id()
    addr = session.current_address()
    if not addr:
        return None
    return sid, addr


def _cmd_clerk_file(args: argparse.Namespace) -> int:
    from . import clerk

    ident = _reader_identity()
    if ident is None:
        print("error: no session address (run session-init first)", file=sys.stderr)
        return 1
    sid, addr = ident
    todo = Path(args.todo) if args.todo else None
    card = clerk.file_to_todo(sid, addr, args.id, todo_path=todo)
    if card is None:
        print(f"error: no pending postcard matching {args.id}", file=sys.stderr)
        return 1
    print(f"filed {card.id[:8]} ({card.title}) to TODO")
    return 0


def _cmd_clerk_surface(args: argparse.Namespace) -> int:
    from . import clerk

    ident = _reader_identity()
    if ident is None:
        print("error: no session address (run session-init first)", file=sys.stderr)
        return 1
    sid, addr = ident
    card = clerk.surface(sid, addr, args.id)
    if card is None:
        print(f"error: no pending postcard matching {args.id}", file=sys.stderr)
        return 1
    print(f"surfaced {card.id[:8]} ({card.title})")
    return 0


def _cmd_receipts(args: argparse.Namespace) -> int:
    from . import ledger

    rs = ledger.receipts(limit=args.limit)
    if not rs:
        print("(no receipts)")
        return 0
    for r in rs:
        print(
            f"{r.read_at}  {r.reader_address:<24}  {r.action:<7}  {r.postcard_id[:8]}"
        )
    return 0


def _cmd_session_init(args: argparse.Namespace) -> int:
    from . import ledger, session

    ledger.init_ledger()
    addr = session.init_session(
        session_id=args.session_id,
        cwd=Path(args.cwd) if args.cwd else None,
        pid=args.pid,
    )
    if not args.quiet:
        print(addr)
    return 0


def _cmd_session_end(args: argparse.Namespace) -> int:
    from . import session

    session.end_session(session_id=args.session_id)
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    from . import project

    target = project.resolve_target(
        Path(args.path) if args.path else None,
        Path.cwd(),
    )
    result = project.init_doc(target, force=args.force)
    if result is project.InitResult.CREATED:
        print(f"created {target}")
    elif result is project.InitResult.APPENDED:
        print(f"appended oat-postcard block to {target}")
    elif result is project.InitResult.REPLACED:
        print(f"replaced oat-postcard block in {target}")
    else:
        print(
            f"oat-postcard block already present in {target} (use --force to rewrite)"
        )
    return 0


def _cmd_cleanup(args: argparse.Namespace) -> int:
    from . import session

    r = session.cleanup(dry_run=args.dry_run)
    label = "would remove" if args.dry_run else "removed"
    print(
        f"{label}: {r.directory} directory, {r.sidecars} sidecars, "
        f"{r.pending} pending, {r.inbox} inbox, {r.dropbox} dropbox ({r.total()} total)"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oat-postcard")
    parser.add_argument(
        "--version", action="version", version=f"oat-postcard {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="send a postcard to an address")
    p_send.add_argument("address")
    p_send.add_argument("title")
    p_send.add_argument("body")
    p_send.add_argument(
        "--force",
        action="store_true",
        help="send even if the recipient is not in the live directory",
    )
    p_send.set_defaults(func=_cmd_send)

    p_reply = sub.add_parser(
        "reply",
        help="reply to a postcard (title auto = 'Re: <parent>', recipient = parent sender)",
    )
    p_reply.add_argument("parent_id", help="parent postcard id (full or 8-char prefix)")
    p_reply.add_argument("body")
    p_reply.add_argument(
        "--force",
        action="store_true",
        help="reply even if the parent sender is no longer active",
    )
    p_reply.set_defaults(func=_cmd_reply)

    p_inbox = sub.add_parser(
        "inbox",
        help="list postcards addressed to this session (passive; use --watch to tail)",
    )
    p_inbox.add_argument(
        "--limit", type=int, default=20, help="number of entries (default 20)"
    )
    p_inbox.add_argument(
        "--watch",
        action="store_true",
        help="tail mode: print new arrivals as they land",
    )
    p_inbox.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="poll interval in seconds when --watch (default 2.0)",
    )
    p_inbox.set_defaults(func=_cmd_inbox)

    p_dir = sub.add_parser("directory", help="list active agents")
    p_dir.set_defaults(func=_cmd_directory)

    p_log = sub.add_parser(
        "log",
        help="show postcard history (passive; use --watch to tail the full ledger)",
    )
    p_log.add_argument("--limit", type=int, default=None)
    p_log.add_argument(
        "--since",
        default=None,
        help="only show postcards newer than this (e.g. 1h, 24h, 7d, or ISO timestamp)",
    )
    p_log.add_argument(
        "--until",
        default=None,
        help="only show postcards older than this (e.g. 1h, 24h, 7d, or ISO timestamp)",
    )
    p_log.add_argument(
        "--watch",
        action="store_true",
        help="tail mode: print new arrivals across the full ledger as they land",
    )
    p_log.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="poll interval in seconds when --watch (default 2.0)",
    )
    p_log.set_defaults(func=_cmd_log)

    p_who = sub.add_parser("whoami", help="print this session's address")
    p_who.set_defaults(func=_cmd_whoami)

    p_sweep = sub.add_parser(
        "clerk-sweep",
        help="move new inbox mail into this session's pending staging (hook use)",
    )
    p_sweep.add_argument("--quiet", action="store_true")
    p_sweep.set_defaults(func=_cmd_clerk_sweep)

    p_pending = sub.add_parser(
        "clerk-pending", help="list pending postcards for this session"
    )
    p_pending.add_argument("--json", action="store_true", help="emit full JSON records")
    p_pending.add_argument("--count", action="store_true", help="print only the count")
    p_pending.set_defaults(func=_cmd_clerk_pending)

    p_file = sub.add_parser(
        "clerk-file", help="file a pending postcard into TODO.md and archive it"
    )
    p_file.add_argument("id", help="postcard id (full or 8-char prefix)")
    p_file.add_argument(
        "--todo", default=None, help="path to TODO.md (default: ./TODO.md)"
    )
    p_file.set_defaults(func=_cmd_clerk_file)

    p_surf = sub.add_parser(
        "clerk-surface", help="mark a pending postcard as surfaced to the main agent"
    )
    p_surf.add_argument("id", help="postcard id (full or 8-char prefix)")
    p_surf.set_defaults(func=_cmd_clerk_surface)

    p_rec = sub.add_parser("receipts", help="show read receipts from the ledger")
    p_rec.add_argument("--limit", type=int, default=None)
    p_rec.set_defaults(func=_cmd_receipts)

    p_init = sub.add_parser(
        "session-init", help="initialize this session in the directory (hook use)"
    )
    p_init.add_argument("--session-id", default=None)
    p_init.add_argument("--cwd", default=None)
    p_init.add_argument(
        "--pid",
        type=int,
        default=None,
        help="PID to record in the directory entry (default: ppid of this process)",
    )
    p_init.add_argument("--quiet", action="store_true")
    p_init.set_defaults(func=_cmd_session_init)

    p_end = sub.add_parser(
        "session-end", help="remove this session from the directory (hook use)"
    )
    p_end.add_argument("--session-id", default=None)
    p_end.set_defaults(func=_cmd_session_end)

    p_clean = sub.add_parser(
        "cleanup",
        help="prune stale state (dead directory entries, orphan sidecars/pending/inbox, old dropbox temps)",
    )
    p_clean.add_argument("--dry-run", action="store_true")
    p_clean.set_defaults(func=_cmd_cleanup)

    p_proj = sub.add_parser(
        "init",
        help="append a coordination hint to this project's CLAUDE.md (or AGENTS.md)",
    )
    p_proj.add_argument(
        "--path", default=None, help="target file (default: ./CLAUDE.md or ./AGENTS.md)"
    )
    p_proj.add_argument(
        "--force", action="store_true", help="rewrite the block if already present"
    )
    p_proj.set_defaults(func=_cmd_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (RuntimeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
