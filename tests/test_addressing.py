from oat_postcard import addressing


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
