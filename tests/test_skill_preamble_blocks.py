"""Regression guard: skill `!` preamble blocks must survive a host without `goc` on PATH.

The Claude Code host executes inline `!`...`` fences at skill load time and
aborts the ENTIRE skill load when a fence exits non-zero — the body, including
its own `goc: command not found` Preflight recovery guidance, never reaches the
agent. Two properties keep the load alive:

1. Every fence that invokes `goc` routes through the vendored bootstrap wrapper
   (`.claude/skills/_goc-bootstrap.sh`) when it exists, falling back to bare
   `goc` for plugin-mode loads where the plugin's `bin/` is on PATH.
2. Every fence is guarded (`|| true`, `|| echo ...`, or a trailing pipe into a
   zero-exit consumer) so a missing CLI degrades into error text inside the
   loaded body instead of aborting the load.

This test enforces (1) statically and (2) empirically: each extracted fence is
executed with a `goc` stub that fails like command-not-found (exit 127), both
with and without the bootstrap wrapper present, and must exit 0.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "goc" / "templates" / "skills"
BOOTSTRAP = ROOT / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh"

_FENCE = re.compile(r"^\s*!`(.*)`\s*$")
# A bare `goc` command token — not part of `_goc-bootstrap.sh`, `.game-of-cards`,
# or an uppercase identifier like `GOC_WORKER`.
_GOC_TOKEN = re.compile(r"(?<![\w./-])goc(?![\w./-])")


def _iter_fences() -> list[tuple[str, int, str]]:
    fences: list[tuple[str, int, str]] = []
    for skill_md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        for lineno, line in enumerate(skill_md.read_text().splitlines(), start=1):
            match = _FENCE.match(line)
            if match:
                fences.append((str(skill_md.relative_to(ROOT)), lineno, match.group(1)))
    return fences


def _invokes_goc(fence: str) -> bool:
    stripped = fence.replace("_goc-bootstrap.sh", "").replace(".game-of-cards", "")
    return bool(_GOC_TOKEN.search(stripped))


class SkillPreambleBlockTest(unittest.TestCase):
    def test_fences_found(self) -> None:
        fences = _iter_fences()
        self.assertGreaterEqual(len(_iter_fences()), 15, fences)
        self.assertTrue(any(_invokes_goc(f) for _, _, f in fences))

    def test_goc_fences_route_through_bootstrap(self) -> None:
        offenders = [
            f"{path}:{lineno}: !`{fence}`"
            for path, lineno, fence in _iter_fences()
            if _invokes_goc(fence) and "_goc-bootstrap.sh" not in fence
        ]
        self.assertFalse(
            offenders,
            msg=(
                "Found `!` fence(s) invoking bare `goc` without routing through "
                ".claude/skills/_goc-bootstrap.sh. On hosts where `goc` is not on "
                "PATH (this dogfood repo, vendored installs before pipx install) "
                "the fence fails and Claude Code aborts the whole skill load. Use: "
                "b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b "
                "<args>; else goc <args>; fi 2>&1 || true\n  " + "\n  ".join(offenders)
            ),
        )

    def _run_fences(self, workdir: Path) -> list[str]:
        """Execute every fence in `workdir` with a failing `goc` stub on PATH."""
        stub_dir = workdir / "_stub-bin"
        stub_dir.mkdir(exist_ok=True)
        stub = stub_dir / "goc"
        stub.write_text('#!/bin/sh\necho "goc: command not found" >&2\nexit 127\n')
        stub.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{stub_dir}:{env.get('PATH', '/usr/bin:/bin')}"
        failures: list[str] = []
        for path, lineno, fence in _iter_fences():
            result = subprocess.run(
                ["/bin/bash", "-c", fence],
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                failures.append(
                    f"{path}:{lineno}: exit {result.returncode}\n"
                    f"    fence: !`{fence}`\n"
                    f"    stderr: {result.stderr.strip()[:200]}"
                )
        return failures

    def test_fences_exit_zero_without_goc_or_bootstrap(self) -> None:
        # Plugin-shaped host gone wrong: no vendored bootstrap, no working goc.
        with tempfile.TemporaryDirectory() as tmp:
            failures = self._run_fences(Path(tmp))
        self.assertFalse(
            failures,
            msg=(
                "Fence(s) exit non-zero on a host without goc — Claude Code would "
                "abort the skill load before the body's recovery guidance is "
                "delivered:\n  " + "\n  ".join(failures)
            ),
        )

    def test_fences_exit_zero_with_bootstrap_but_no_cli(self) -> None:
        # Vendored fresh-clone host: bootstrap present, CLI still missing.
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            skills = workdir / ".claude" / "skills"
            skills.mkdir(parents=True)
            shutil.copy2(BOOTSTRAP, skills / "_goc-bootstrap.sh")
            failures = self._run_fences(workdir)
        self.assertFalse(
            failures,
            msg=(
                "Fence(s) exit non-zero on a vendored host whose CLI is missing — "
                "the bootstrap's install hint must land in the loaded body, not "
                "abort the load:\n  " + "\n  ".join(failures)
            ),
        )


if __name__ == "__main__":
    unittest.main()
