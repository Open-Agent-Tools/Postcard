from __future__ import annotations

import random

from . import words


def generate_address(seed: int | None = None) -> str:
    """Return a random ``word-word-word`` address.

    Unseeded calls draw from ``random.SystemRandom`` so that repeated calls
    within one process yield different addresses; the previous PID-based
    seed made the collision-retry loop in ``session.init_session`` a no-op
    whenever two sessions were registered from the same process. ``seed``
    is for deterministic tests only.
    """
    rng: random.Random = (
        random.Random(seed) if seed is not None else random.SystemRandom()
    )
    return "-".join(rng.sample(words.WORDS, 3))


def session_address() -> str:
    raise NotImplementedError(
        "resolve the current session's address from the directory"
    )
