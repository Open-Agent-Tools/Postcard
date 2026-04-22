from oat_postcard import addressing, words


def test_generate_address_shape():
    addr = addressing.generate_address(seed=1)
    parts = addr.split("-")
    assert len(parts) == 3
    assert all(p.isalpha() for p in parts)


def test_generate_address_parts_are_distinct():
    for s in range(50):
        parts = addressing.generate_address(seed=s).split("-")
        assert len(set(parts)) == 3


def test_generate_address_deterministic():
    assert addressing.generate_address(seed=42) == addressing.generate_address(seed=42)


def test_generate_address_varies():
    seen = {addressing.generate_address(seed=s) for s in range(50)}
    assert len(seen) > 5


def test_word_list_is_unique():
    assert len(words.WORDS) == len(set(words.WORDS))


def test_word_list_is_lowercase_alpha():
    for w in words.WORDS:
        assert w.isalpha() and w.islower()


def test_combination_space_at_least_50k():
    n = len(words.WORDS)
    total = n * (n - 1) * (n - 2)
    assert total >= 50_000, f"only {total} combinations"
