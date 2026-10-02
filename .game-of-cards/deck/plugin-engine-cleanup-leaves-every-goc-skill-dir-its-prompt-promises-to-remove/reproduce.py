#!/usr/bin/env python3
"""The documented vendored -> plugin switch, run through the Claude plugin's bundled engine.

Scaffolds a scratch repo with the source engine's `goc install --local-skills`
(the bundled engine refuses that flag), adds one skill of the repo's own,
sets `skills_source: plugin`, then runs `claude-plugin/bin/goc upgrade` and
answers `y` to the cleanup — what a Claude Code session with the plugin
enabled runs for a bare `goc upgrade`.

Exits 0 when no GoC skill dir survives and the repo's own skill does, 1 while
the bundled engine keeps GoC's skill dirs despite promising to remove them.
"""

from __future__ import annotations

import os
import re
import shutil
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc.install import skill_for_agent  # noqa: E402

WRAPPER = ROOT / "claude-plugin" / "bin" / "goc"
GOC_SKILLS = sorted(
    p.name for p in (ROOT / "goc" / "templates" / "skills").iterdir() if p.is_dir() and skill_for_agent(p.name, "claude")
)


def main() -> int:
    if not WRAPPER.exists():
        print(f"[SKIP] no plugin wrapper at {WRAPPER}")
        return 0
    work = Path(tempfile.mkdtemp(prefix="goc-plugin-cleanup-"))
    try:
        repo = work / "consumer"
        repo.mkdir()
        subprocess.run(
            [sys.executable, "-m", "goc.cli", "install", "--local-skills", "--agents", "claude"],
            cwd=repo, env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, check=True,
        )
        (repo / ".claude" / "skills" / "my-own-skill").mkdir()
        (repo / ".claude" / "skills" / "my-own-skill" / "SKILL.md").write_text("# mine\n")
        config = repo / ".game-of-cards" / "config.yaml"
        config.write_text(re.sub(r"^skills_source:.*$", "skills_source: plugin", config.read_text(), flags=re.M))

        run = subprocess.run([str(WRAPPER), "upgrade"], cwd=repo, input="y\n", text=True, capture_output=True)
        promised = "Cleanup removes GoC-managed skill directories" in run.stdout
        left = [name for name in GOC_SKILLS if (repo / ".claude" / "skills" / name).is_dir()]
        own = (repo / ".claude" / "skills" / "my-own-skill" / "SKILL.md").is_file()
        hooks_left = (repo / ".claude" / "hooks").exists()
        print(f"bundled-engine upgrade exit={run.returncode}; prompt promised skill-dir removal={promised}")
        print(f"GoC skill dirs left: {len(left)} of {len(GOC_SKILLS)} {left}")
        print(f"repo's own skill kept: {own}; .claude/hooks/ left: {hooks_left}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if left or not own:
        print("\nFAIL: the bundled engine's cleanup kept GoC's skill dirs (or lost the repo's own skill).")
        return 1
    print("\nOK: the bundled engine's cleanup removed GoC's skill dirs and kept the repo's own.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
