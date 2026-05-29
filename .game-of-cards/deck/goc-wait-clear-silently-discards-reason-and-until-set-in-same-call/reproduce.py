"""Reproduce: `goc wait --clear --reason X --until Y` silently discards the set.

Expected after fix: either the second invocation exits non-zero (Option A),
or the frontmatter ends with `waiting_on: resource, waiting_until: 2027-06-30`
(Option B). Either outcome makes this reproducer exit 0 (the BUG branch
exits 1).
"""

from __future__ import annotations

import os
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


def main() -> int:
    repo = _repo_root()
    # Run goc as `python -m goc.cli`, pinning the source tree on
    # PYTHONPATH so we don't need to install a wheel into the sandbox.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")

    with tempfile.TemporaryDirectory() as td:
        sandbox = Path(td) / "sandbox"
        sandbox.mkdir()
        deck = sandbox / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)

        def goc(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *args],
                cwd=sandbox,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        title = "demo"
        r = goc("new", title, "--contribution", "low", "--tag", "api-contract")
        assert r.returncode == 0, f"goc new failed: {r.stderr}"

        r = goc("wait", title, "--reason", "external", "--until", "2026-12-31", "--no-commit")
        assert r.returncode == 0, f"first wait failed: {r.stderr}"

        # The conflict invocation: --clear + --reason + --until in one call.
        r = goc("wait", title, "--clear", "--reason", "resource", "--until", "2027-06-30", "--no-commit")
        fm = (deck / title / "README.md").read_text()

        print("=== second invocation ===")
        print(f"exit code: {r.returncode}")
        print(f"stdout: {r.stdout.strip()}")
        print(f"stderr: {r.stderr.strip()}")
        print()
        print("=== frontmatter overlay fields after conflict call ===")
        overlay_lines = [line for line in fm.splitlines() if line.startswith("waiting_")]
        for line in overlay_lines:
            print(line)
        if not overlay_lines:
            print("(no waiting_* keys present)")
        print()

        has_reason = any(line.startswith("waiting_on:") and "resource" in line for line in fm.splitlines())
        has_until = any(line.startswith("waiting_until:") and "2027-06-30" in line for line in fm.splitlines())

        print("=== diagnosis ===")
        if r.returncode != 0:
            print("FIXED (Option A): conflict rejected with non-zero exit.")
            return 0
        if has_reason and has_until:
            print("FIXED (Option B): clear-then-set applied; overlay matches the explicit args.")
            return 0
        print("BUG: exit 0 AND requested overlay (waiting_on=resource, waiting_until=2027-06-30) was silently dropped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
