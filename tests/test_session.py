from oat_postcard import directory, session


def test_init_session_creates_address_and_directory_entry(tmp_root, session_env):
    addr = session.init_session(cwd=tmp_root)
    assert addr.count("-") == 2
    assert session.current_address() == addr
    entry = directory.resolve(addr)
    assert entry is not None
    assert entry.session_id == session_env


def test_init_session_is_idempotent(tmp_root, session_env):
    a = session.init_session()
    b = session.init_session()
    assert a == b


def test_end_session_removes_entry(tmp_root, session_env):
    addr = session.init_session()
    session.end_session()
    assert directory.resolve(addr) is None
    assert session.current_address() is None


def test_resolve_or_init(tmp_root, session_env):
    addr = session.resolve_or_init()
    assert session.current_address() == addr
    assert session.resolve_or_init() == addr
