"""Every host manifest and the package must agree on the release version."""

import json
import re
from pathlib import Path

from oat_postcard import __version__

ROOT = Path(__file__).resolve().parents[1]


def _json_version(rel: str, *keys: str) -> str:
    data = json.loads((ROOT / rel).read_text())
    for k in keys:
        data = data[k]
    return data


def test_manifest_versions_agree():
    versions = {
        "package": __version__,
        "pyproject": re.search(
            r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M
        ).group(1),
        "claude plugin": _json_version(".claude-plugin/plugin.json", "version"),
        "claude marketplace": _json_version(
            ".claude-plugin/marketplace.json", "metadata", "version"
        ),
        "claude marketplace entry": json.loads(
            (ROOT / ".claude-plugin/marketplace.json").read_text()
        )["plugins"][0]["version"],
        "codex plugin": _json_version(".codex-plugin/plugin.json", "version"),
        "codex marketplace": _json_version(
            ".agents/plugins/marketplace.json", "metadata", "version"
        ),
        "codex marketplace entry": json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text()
        )["plugins"][0]["version"],
        "copilot plugin": _json_version(".github/plugin/plugin.json", "version"),
        "antigravity plugin": _json_version(
            ".antigravity-plugin/plugin.json", "version"
        ),
    }
    assert len(set(versions.values())) == 1, versions


def test_hook_configs_point_at_the_unified_script():
    claude = (ROOT / "hooks/hooks.json").read_text()
    copilot = (ROOT / "hooks/copilot.json").read_text()
    agy = (ROOT / "hooks.json").read_text()
    for text in (claude, copilot, agy):
        json.loads(text)
        assert "scripts/hook.sh" in text
    assert "--host auto" in claude
    assert "--host copilot" in copilot and '"version": 1' in copilot
    assert "--host agy" in agy and "./scripts/hook.sh" in agy
    assert (ROOT / "scripts/hook.sh").exists()
    assert not (ROOT / "scripts/session-start.sh").exists()
