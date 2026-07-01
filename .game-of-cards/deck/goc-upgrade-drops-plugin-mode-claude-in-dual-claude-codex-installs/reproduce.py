"""Reproduce: a no-flag `goc upgrade` silently drops plugin-mode Claude in a
dual claude+codex install.

`goc install --agents claude,codex` puts Claude in plugin mode (writes
`skills_source: plugin`, creates NO `.claude/skills/` tree) and vendors Codex
under `.codex/skills/`. `upgrade()` picks its default agent set from
`_detect_installed_surfaces`, which uses each harness's skill-tree directory as
the sole install marker. Plugin-mode Claude has no such directory, so it is
invisible; because Codex IS detected, the `installed or DEFAULT_AGENTS` fallback
never fires and Claude is dropped from the upgrade.

Run: uv run python .game-of-cards/deck/goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs/reproduce.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import install  # noqa: E402
from goc.install import _detect_installed_surfaces, _templates_root  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=target, check=True)

        prior = Path.cwd()
        os.chdir(target)
        try:
            # Documented default multi-agent install.
            install.install(agent_specs=("claude", "codex"))
        finally:
            os.chdir(prior)

        has_claude_skills = (target / ".claude" / "skills").is_dir()
        has_codex_skills = (target / ".codex" / "skills").is_dir()
        skills_source = ""
        cfg = target / ".game-of-cards" / "config.yaml"
        if cfg.exists():
            for line in cfg.read_text().splitlines():
                if line.strip().startswith("skills_source:"):
                    skills_source = line.strip()
                    break

        detected = _detect_installed_surfaces(target, _templates_root())

        print(f"installed_claude_in_plugin_mode = {skills_source!r} (no .claude/skills: {not has_claude_skills})")
        print(f".claude/skills present          = {has_claude_skills}")
        print(f".codex/skills present           = {has_codex_skills}")
        print(f"_detect_installed_surfaces      = {detected}")
        # upgrade() computes: default_agents = installed or DEFAULT_AGENTS
        upgrade_default = detected or ("claude",)
        print(f"no-flag upgrade would target    = {upgrade_default}")

        claude_dropped = "claude" not in upgrade_default
        print()
        if claude_dropped:
            print("DEFECT CONFIRMED: Claude was installed but a no-flag `goc upgrade` "
                  "silently drops it (Claude briefing/import wiring never refreshed).")
            return 0
        print("No defect: Claude retained in the upgrade default.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
