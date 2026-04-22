import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__


def _cmd_send(args: argparse.Namespace) -> int:
    from . import ledger, session

    sender = session.resolve_or_init()
    pc = ledger.send(sender, args.address, args.title, args.body)
    print(f"sent {pc.id[:8]} to {args.address}")
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

    cards = ledger.log(limit=args.limit)
    if not cards:
        print("(ledger empty)")
        return 0
    for pc in cards:
        print(f"{pc.sent_at}  {pc.sender} -> {pc.recipient}  {pc.title}")
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


def _cmd_clerk_file(args: argparse.Namespace) -> int:
    from . import clerk, session

    sid = session.current_session_id()
    todo = Path(args.todo) if args.todo else None
    card = clerk.file_to_todo(sid, args.id, todo_path=todo)
    if card is None:
        print(f"error: no pending postcard matching {args.id}", file=sys.stderr)
        return 1
    print(f"filed {card.id[:8]} ({card.title}) to TODO")
    return 0


def _cmd_clerk_archive(args: argparse.Namespace) -> int:
    from . import clerk, session

    sid = session.current_session_id()
    card = clerk.archive(sid, args.id)
    if card is None:
        print(f"error: no pending postcard matching {args.id}", file=sys.stderr)
        return 1
    print(f"archived {card.id[:8]} ({card.title})")
    return 0


def _cmd_session_init(args: argparse.Namespace) -> int:
    from . import ledger, session

    ledger.init_ledger()
    addr = session.init_session(session_id=args.session_id, cwd=Path(args.cwd) if args.cwd else None)
    if not args.quiet:
        print(addr)
    return 0


def _cmd_session_end(args: argparse.Namespace) -> int:
    from . import session

    session.end_session(session_id=args.session_id)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oat-postcard")
    parser.add_argument("--version", action="version", version=f"oat-postcard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="send a postcard to an address")
    p_send.add_argument("address")
    p_send.add_argument("title")
    p_send.add_argument("body")
    p_send.set_defaults(func=_cmd_send)

    p_dir = sub.add_parser("directory", help="list active agents")
    p_dir.set_defaults(func=_cmd_directory)

    p_log = sub.add_parser("log", help="show postcard history")
    p_log.add_argument("--limit", type=int, default=None)
    p_log.set_defaults(func=_cmd_log)

    p_who = sub.add_parser("whoami", help="print this session's address")
    p_who.set_defaults(func=_cmd_whoami)

    p_sweep = sub.add_parser("clerk-sweep", help="move new inbox mail into this session's pending staging (hook use)")
    p_sweep.add_argument("--quiet", action="store_true")
    p_sweep.set_defaults(func=_cmd_clerk_sweep)

    p_pending = sub.add_parser("clerk-pending", help="list pending postcards for this session")
    p_pending.add_argument("--json", action="store_true", help="emit full JSON records")
    p_pending.add_argument("--count", action="store_true", help="print only the count")
    p_pending.set_defaults(func=_cmd_clerk_pending)

    p_file = sub.add_parser("clerk-file", help="file a pending postcard into TODO.md and archive it")
    p_file.add_argument("id", help="postcard id (full or 8-char prefix)")
    p_file.add_argument("--todo", default=None, help="path to TODO.md (default: ./TODO.md)")
    p_file.set_defaults(func=_cmd_clerk_file)

    p_arc = sub.add_parser("clerk-archive", help="archive a pending postcard without filing")
    p_arc.add_argument("id", help="postcard id (full or 8-char prefix)")
    p_arc.set_defaults(func=_cmd_clerk_archive)

    p_init = sub.add_parser("session-init", help="initialize this session in the directory (hook use)")
    p_init.add_argument("--session-id", default=None)
    p_init.add_argument("--cwd", default=None)
    p_init.add_argument("--quiet", action="store_true")
    p_init.set_defaults(func=_cmd_session_init)

    p_end = sub.add_parser("session-end", help="remove this session from the directory (hook use)")
    p_end.add_argument("--session-id", default=None)
    p_end.set_defaults(func=_cmd_session_end)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
