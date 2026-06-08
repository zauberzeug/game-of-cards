"""Reproduce/verify the local Codex GoC plugin cache selection.

Run:
    uv run python .game-of-cards/deck/codex-startup-loads-yaml-broken-plugin-cache/reproduce.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
CODEX_HOME = Path.home() / ".codex"
CONFIG = CODEX_HOME / "config.toml"
PLUGIN_CACHE = CODEX_HOME / "plugins" / "cache"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
NESTED_MAPPING_COLON = re.compile(r":(?:[ \t]|$)")


def _section(text: str, header: str) -> str:
    start = text.find(header)
    if start == -1:
        return ""
    body_start = start + len(header)
    next_header = text.find("\n[", body_start)
    if next_header == -1:
        return text[body_start:]
    return text[body_start:next_header]


def _plugin_enabled(config_text: str, key: str) -> bool:
    body = _section(config_text, f'[plugins."{key}"]')
    return re.search(r"(?m)^\s*enabled\s*=\s*true\s*$", body) is not None


def _is_quoted_or_structured(value: str) -> bool:
    return value.startswith(('"', "'", "|", ">", "[", "{")) or value in {"", "null"}


def _strict_yaml_hazards(skill_root: Path) -> list[str]:
    out: list[str] = []
    if not skill_root.exists():
        return [f"{skill_root}: missing skill root"]
    for path in sorted(skill_root.rglob("SKILL.md")):
        match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
        if not match:
            out.append(f"{path}: missing line-anchored frontmatter")
            continue
        for lineno, line in enumerate(match.group(1).splitlines(), start=1):
            if not line or line.startswith((" ", "\t", "#")):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if _is_quoted_or_structured(value):
                continue
            if NESTED_MAPPING_COLON.search(value):
                out.append(f"{path}:{lineno}: {key} contains unquoted ': '")
    return out


def _version_tuple(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in raw.split("."))


def _installed_versions(marketplace: str) -> list[tuple[tuple[int, ...], Path, str]]:
    root = PLUGIN_CACHE / marketplace / "game-of-cards"
    out: list[tuple[tuple[int, ...], Path, str]] = []
    for plugin_root in sorted(root.glob("*")):
        manifest = plugin_root / ".codex-plugin" / "plugin.json"
        if not manifest.exists():
            manifest = plugin_root / ".claude-plugin" / "plugin.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        version = str(data.get("version", "0.0.0"))
        out.append((_version_tuple(version), plugin_root, version))
    return out


def main() -> int:
    if not CONFIG.exists():
        print(f"FAIL - Codex config not found: {CONFIG}")
        return 1

    config_text = CONFIG.read_text(encoding="utf-8")
    old_enabled = _plugin_enabled(config_text, "game-of-cards@zauberzeug-claude")
    new_enabled = _plugin_enabled(config_text, "game-of-cards@game-of-cards")
    new_versions = _installed_versions("game-of-cards")

    print(f"old zauberzeug-claude plugin enabled: {old_enabled}")
    print(f"direct game-of-cards plugin enabled: {new_enabled}")

    if old_enabled:
        print("FAIL - Codex still enables game-of-cards@zauberzeug-claude")
        return 1
    if not new_enabled:
        print("FAIL - Codex does not enable game-of-cards@game-of-cards")
        return 1
    if not new_versions:
        print("FAIL - no direct game-of-cards plugin cache is installed")
        return 1

    _version, plugin_root, version_text = max(new_versions, key=lambda item: item[0])
    print(f"direct plugin cache: {plugin_root}")
    print(f"direct plugin version: {version_text}")
    if _version < (0, 0, 24):
        print("FAIL - direct plugin cache predates the strict-YAML fix")
        return 1

    hazards = _strict_yaml_hazards(plugin_root / "skills")
    if hazards:
        print("FAIL - strict-YAML hazards remain in active GoC plugin cache:")
        for hazard in hazards:
            print(f"  {hazard}")
        return 1

    print("OK - Codex GoC plugin uses the strict-YAML-safe direct 0.0.24+ cache.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
