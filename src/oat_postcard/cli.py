import argparse
import sys
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


def _cmd_clerk_check(args: argparse.Namespace) -> int:
    from . import clerk, session

    address = args.address or session.current_address()
    if not address:
        return 0
    todo = Path(args.todo) if args.todo else None
    count = clerk.relay(address, todo_path=todo)
    if count:
        print(f"{count} new postcard(s) for {address}")
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

    p_clerk = sub.add_parser("clerk-check", help="relay new mail into the local TODO.md")
    p_clerk.add_argument("--address", default=None)
    p_clerk.add_argument("--todo", default=None, help="path to TODO.md (default: ./TODO.md)")
    p_clerk.set_defaults(func=_cmd_clerk_check)

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
