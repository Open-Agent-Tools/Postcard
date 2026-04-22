from oat_postcard import addressing, words


def test_generate_address_shape():
    addr = addressing.generate_address(seed=1)
    parts = addr.split("-")
    assert len(parts) == 3
    assert all(p.isalpha() for p in parts)


def test_generate_address_deterministic():
    assert addressing.generate_address(seed=42) == addressing.generate_address(seed=42)


def test_generate_address_varies():
    seen = {addressing.generate_address(seed=s) for s in range(50)}
    assert len(seen) > 5


def test_word_lists_are_unique():
    for bucket in (words.ADJECTIVES_ONE, words.ADJECTIVES_TWO, words.NOUNS):
        assert len(bucket) == len(set(bucket))


def test_word_lists_are_lowercase_alpha():
    for bucket in (words.ADJECTIVES_ONE, words.ADJECTIVES_TWO, words.NOUNS):
        for w in bucket:
            assert w.isalpha() and w.islower()


def test_combination_space_at_least_50k():
    total = len(words.ADJECTIVES_ONE) * len(words.ADJECTIVES_TWO) * len(words.NOUNS)
    assert total >= 50_000, f"only {total} combinations"
