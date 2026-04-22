from oat_postcard import project


def test_init_creates_new_file(tmp_path):
    target = tmp_path / "CLAUDE.md"
    result = project.init_doc(target)
    assert result is project.InitResult.CREATED
    text = target.read_text()
    assert project.BEGIN_MARKER in text
    assert project.END_MARKER in text


def test_init_appends_to_existing_file(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# My project\n\nExisting notes.\n")
    result = project.init_doc(target)
    assert result is project.InitResult.APPENDED
    text = target.read_text()
    assert "Existing notes." in text
    assert project.BEGIN_MARKER in text


def test_init_is_idempotent(tmp_path):
    target = tmp_path / "CLAUDE.md"
    project.init_doc(target)
    result = project.init_doc(target)
    assert result is project.InitResult.UNCHANGED
    assert target.read_text().count(project.BEGIN_MARKER) == 1


def test_init_force_replaces_block_content(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        f"# My project\n\n{project.BEGIN_MARKER}\nOLD content\n{project.END_MARKER}\n"
    )
    result = project.init_doc(target, force=True)
    assert result is project.InitResult.REPLACED
    text = target.read_text()
    assert "OLD content" not in text
    assert "Agent-to-agent messaging" in text
    assert text.count(project.BEGIN_MARKER) == 1


def test_init_force_preserves_surrounding_content(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        f"# Project\n\nIntro.\n\n{project.BEGIN_MARKER}\nX\n{project.END_MARKER}\n\nTrailing notes.\n"
    )
    project.init_doc(target, force=True)
    text = target.read_text()
    assert "Intro." in text
    assert "Trailing notes." in text


def test_resolve_target_prefers_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("")
    (tmp_path / "AGENTS.md").write_text("")
    assert project.resolve_target(None, tmp_path) == tmp_path / "CLAUDE.md"


def test_resolve_target_falls_back_to_agents_md(tmp_path):
    (tmp_path / "AGENTS.md").write_text("")
    assert project.resolve_target(None, tmp_path) == tmp_path / "AGENTS.md"


def test_resolve_target_defaults_to_claude_md_when_neither_exists(tmp_path):
    assert project.resolve_target(None, tmp_path) == tmp_path / "CLAUDE.md"


def test_resolve_target_respects_explicit_path(tmp_path):
    explicit = tmp_path / "custom.md"
    assert project.resolve_target(explicit, tmp_path) == explicit
