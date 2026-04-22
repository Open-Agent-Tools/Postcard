import os
import random

from . import words


def generate_address(seed: int | None = None) -> str:
    rng = random.Random(seed if seed is not None else os.getpid())
    return "-".join([
        rng.choice(words.ADJECTIVES_ONE),
        rng.choice(words.ADJECTIVES_TWO),
        rng.choice(words.NOUNS),
    ])


def session_address() -> str:
    raise NotImplementedError("resolve the current session's address from the directory")
