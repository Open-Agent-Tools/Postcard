from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import paths

TITLE_MAX = 140
BODY_MAX = 1400
RECEIPTS_SUBDIR = "receipts"
RECEIPT_ACTIONS = ("file", "surface")


@dataclass
class Postcard:
    id: str
    sender: str
    recipient: str
    title: str
    body: str
    sent_at: str


@dataclass
class Receipt:
    postcard_id: str
    action: str
    read_at: str
    reader_address: str
    reader_session_id: str


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def init_ledger() -> None:
    paths.ensure_root()
    if (paths.POSTCARDS_DIR / ".git").exists():
        return
    _git("init", "--quiet", "--initial-branch=main", cwd=paths.POSTCARDS_DIR)
    _git("config", "user.email", "oat-postcard@localhost", cwd=paths.POSTCARDS_DIR)
    _git("config", "user.name", "oat-postcard", cwd=paths.POSTCARDS_DIR)
    _git("config", "commit.gpgsign", "false", cwd=paths.POSTCARDS_DIR)
    (paths.POSTCARDS_DIR / ".gitkeep").touch()
    _git("add", ".gitkeep", cwd=paths.POSTCARDS_DIR)
    _git("commit", "--quiet", "-m", "init ledger", cwd=paths.POSTCARDS_DIR)


def _validate_lengths(title: str, body: str) -> None:
    if len(title) > TITLE_MAX:
        raise ValueError(f"title exceeds {TITLE_MAX} chars ({len(title)})")
    if len(body) > BODY_MAX:
        raise ValueError(f"body exceeds {BODY_MAX} chars ({len(body)})")


def _postcard_relpath(sent_at: datetime, postcard_id: str) -> Path:
    return Path(
        f"{sent_at:%Y}",
        f"{sent_at:%m}",
        f"{sent_at:%d}",
        f"{sent_at:%Y%m%dT%H%M%SZ}-{postcard_id[:8]}.json",
    )


def _receipt_relpath(postcard_id: str) -> Path:
    return Path(RECEIPTS_SUBDIR, f"{postcard_id}.json")


def _atomic_write(payload: str, dest: Path, prefix: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=paths.DROPBOX_DIR, prefix=prefix, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)
        os.replace(tmp, dest)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def send(sender: str, recipient: str, title: str, body: str) -> Postcard:
    _validate_lengths(title, body)
    init_ledger()

    now = datetime.now(timezone.utc)
    pc = Postcard(
        id=uuid.uuid4().hex,
        sender=sender,
        recipient=recipient,
        title=title,
        body=body,
        sent_at=now.isoformat(timespec="seconds"),
    )
    payload = json.dumps(asdict(pc), indent=2, ensure_ascii=False)

    relpath = _postcard_relpath(now, pc.id)
    dest = paths.POSTCARDS_DIR / relpath
    _atomic_write(payload, dest, prefix=".pc-")

    inbox = paths.inbox_for(recipient)
    inbox.mkdir(parents=True, exist_ok=True)
    inbox_entry = inbox / f"{pc.sent_at}-{pc.id[:8]}.json"
    try:
        os.link(dest, inbox_entry)
    except OSError:
        inbox_entry.write_text(payload)

    _git("add", str(relpath), cwd=paths.POSTCARDS_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        f"{sender} -> {recipient}: {title[:72]}",
        cwd=paths.POSTCARDS_DIR,
    )
    return pc


def write_receipt(
    postcard_id: str,
    action: str,
    reader_address: str,
    reader_session_id: str,
) -> Receipt:
    if action not in RECEIPT_ACTIONS:
        raise ValueError(f"action must be one of {RECEIPT_ACTIONS}, got {action!r}")
    init_ledger()

    receipt = Receipt(
        postcard_id=postcard_id,
        action=action,
        read_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        reader_address=reader_address,
        reader_session_id=reader_session_id,
    )
    payload = json.dumps(asdict(receipt), indent=2, ensure_ascii=False)

    relpath = _receipt_relpath(postcard_id)
    dest = paths.POSTCARDS_DIR / relpath
    _atomic_write(payload, dest, prefix=".rc-")

    _git("add", str(relpath), cwd=paths.POSTCARDS_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        f"receipt: {reader_address} {action} {postcard_id[:8]}",
        cwd=paths.POSTCARDS_DIR,
    )
    return receipt


def _read_git_log_files(limit: int | None, *pathspecs: str) -> list[str]:
    args = ["log"]
    if limit:
        args.append(f"-n{limit}")
    args.extend(["--name-only", "--pretty=format:", "--diff-filter=A"])
    if pathspecs:
        args.append("--")
        args.extend(pathspecs)
    result = _git(*args, cwd=paths.POSTCARDS_DIR)
    return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]


def log(limit: int | None = None) -> list[Postcard]:
    init_ledger()
    cards: list[Postcard] = []
    for rel in _read_git_log_files(limit):
        if rel == ".gitkeep" or rel.startswith(f"{RECEIPTS_SUBDIR}/"):
            continue
        p = paths.POSTCARDS_DIR / rel
        if not p.exists():
            continue
        try:
            cards.append(Postcard(**json.loads(p.read_text())))
        except (json.JSONDecodeError, OSError, TypeError):
            continue
        if limit and len(cards) >= limit:
            break
    return cards


def receipts(limit: int | None = None) -> list[Receipt]:
    init_ledger()
    out: list[Receipt] = []
    for rel in _read_git_log_files(limit, f"{RECEIPTS_SUBDIR}/"):
        p = paths.POSTCARDS_DIR / rel
        if not p.exists():
            continue
        try:
            out.append(Receipt(**json.loads(p.read_text())))
        except (json.JSONDecodeError, OSError, TypeError):
            continue
        if limit and len(out) >= limit:
            break
    return out


def receipt_for(postcard_id: str) -> Receipt | None:
    p = paths.POSTCARDS_DIR / _receipt_relpath(postcard_id)
    if not p.exists():
        return None
    try:
        return Receipt(**json.loads(p.read_text()))
    except (json.JSONDecodeError, OSError, TypeError):
        return None
