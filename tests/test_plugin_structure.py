"""The repository is a valid Claude Code plugin + marketplace, and its parts stay consistent.

Mirrors the rules in the Claude Code plugin, marketplace and skills references, so CI catches a
broken manifest or skill without needing the `claude` CLI (`claude plugin validate . --strict` is
the authoritative check; run it before releases).
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
MARKET = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED_PREFIXES = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")


def test_plugin_manifest():
    assert KEBAB.match(PLUGIN["name"]) and not PLUGIN["name"].startswith(RESERVED_PREFIXES)
    for key in ("version", "description", "author", "license", "homepage"):
        assert PLUGIN.get(key), key
    assert PLUGIN["author"].get("name")
    assert PLUGIN["homepage"].startswith("https://")
    # Only the manifest lives in .claude-plugin/; components sit at the plugin root.
    assert {p.name for p in (ROOT / ".claude-plugin").iterdir()} <= {"plugin.json", "marketplace.json"}
    assert not (ROOT / "CLAUDE.md").exists(), "a CLAUDE.md at the plugin root isn't loaded and draws a warning"


def test_mcp_server_launch():
    server = PLUGIN["mcpServers"]["aoe2-editor"]
    args = server["args"]
    # --project keeps the user's working directory (relative spec paths, build output);
    # --directory would run inside the plugin folder, which updates replace.
    assert "--directory" not in args and args[args.index("--project") + 1] == "${CLAUDE_PLUGIN_ROOT}"
    assert args[-1] in PYPROJECT["project"]["scripts"]
    assert server["env"]["UV_PROJECT_ENVIRONMENT"].startswith("${CLAUDE_PLUGIN_DATA}")


def test_marketplace():
    assert re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", MARKET["name"]) and ".." not in MARKET["name"]
    assert MARKET["owner"]["name"] and MARKET.get("description")
    (entry,) = MARKET["plugins"]
    assert entry["name"] == PLUGIN["name"] and entry["source"] == "./"
    assert "version" not in entry  # plugin.json owns the version


def test_versions_agree():
    import aoe2ed
    assert PLUGIN["version"] == PYPROJECT["project"]["version"] == aoe2ed.__version__


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)
def test_skill(skill: Path):
    text = skill.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "frontmatter must start on the first line"
    fm = yaml.safe_load(m.group(1))
    # Portable keys only, so the skill also works outside Claude Code (claude.ai, Skills API).
    assert set(fm) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    assert fm["name"] == skill.parent.name and KEBAB.match(fm["name"])
    assert 50 <= len(fm["description"]) <= 1024
    body = text[m.end():]
    assert body.count("\n") < 500
    # Installed plugins run from the user's project, so repo-relative paths don't resolve.
    bad = re.findall(r"`(?:src|examples|scripts|docs|tests)/[^`]*`", body)
    assert not bad, f"use ${{CLAUDE_PLUGIN_ROOT}}/... or a tool instead of {bad}"
    for link in re.findall(r"\]\(([^)#]+)\)", body):  # relative links inside the skill folder exist
        if not link.startswith(("http", "$")):
            assert (skill.parent / link).exists(), link
