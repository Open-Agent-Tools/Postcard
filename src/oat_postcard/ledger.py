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


@dataclass
class Postcard:
    id: str
    sender: str
    recipient: str
    title: str
    body: str
    sent_at: str


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

    fd, tmp = tempfile.mkstemp(dir=paths.DROPBOX_DIR, prefix=".pc-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)

        relpath = _postcard_relpath(now, pc.id)
        dest = paths.POSTCARDS_DIR / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, dest)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise

    inbox = paths.inbox_for(recipient)
    inbox.mkdir(parents=True, exist_ok=True)
    inbox_entry = inbox / f"{pc.sent_at}-{pc.id[:8]}.json"
    try:
        os.link(dest, inbox_entry)
    except OSError:
        inbox_entry.write_text(payload)

    rel = str(relpath)
    _git("add", rel, cwd=paths.POSTCARDS_DIR)
    _git(
        "commit",
        "--quiet",
        "-m",
        f"{sender} -> {recipient}: {title[:72]}",
        cwd=paths.POSTCARDS_DIR,
    )
    return pc


def log(limit: int | None = None) -> list[Postcard]:
    init_ledger()
    args = ["log", "--name-only", "--pretty=format:", "--diff-filter=A"]
    if limit:
        args.append(f"-n{limit}")
    result = _git(*args, cwd=paths.POSTCARDS_DIR)
    cards: list[Postcard] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line == ".gitkeep":
            continue
        p = paths.POSTCARDS_DIR / line
        if not p.exists():
            continue
        try:
            cards.append(Postcard(**json.loads(p.read_text())))
        except (json.JSONDecodeError, OSError, TypeError):
            continue
        if limit and len(cards) >= limit:
            break
    return cards
