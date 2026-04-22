from __future__ import annotations

import os
import random

from . import words


def generate_address(seed: int | None = None) -> str:
    rng = random.Random(seed if seed is not None else os.getpid())
    return "-".join(rng.sample(words.WORDS, 3))


def session_address() -> str:
    raise NotImplementedError(
        "resolve the current session's address from the directory"
    )
