"""Demonstrate that `goc new`'s "Next:" hint points at a non-existent path.

Runs `goc new` in a temp directory seeded with a minimal `.game-of-cards/`
state, captures stdout, and asserts that the path printed in the "Next:"
hint actually exists on disk. On current `main` the assertion fails:
the hint says `Next: edit deck/<title>/README.md ...` while the card was
written to `.game-of-cards/deck/<title>/README.md`.

Run from anywhere:
    uv run python .game-of-cards/deck/goc-new-next-hint-points-at-stale-deck-path-not-game-of-cards-deck/reproduce.py
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


REPO = _repo_root()


def main() -> int:
    title = "repro-hint-path-card"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Seed a minimal .game-of-cards/ scaffold so `goc new` runs without
        # tripping kickoff. The schema lives in the installed package.
        (tmp_path / ".game-of-cards" / "deck").mkdir(parents=True)
        (tmp_path / ".game-of-cards" / "config.yaml").write_text(
            "skills_source: vendored\n"
        )

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "goc.cli",
                "new",
                title,
                "--contribution",
                "low",
                "--gate",
                "none",
                "--tag",
                "bug",
                "--allow-jargon",
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )

        stdout = result.stdout
        print("--- goc new stdout ---")
        print(stdout, end="")
        print("--- end ---")

        match = re.search(r"^Next: edit (\S+)/README\.md", stdout, re.MULTILINE)
        if not match:
            print(f"FAIL: could not locate `Next: edit ...` hint in stdout", file=sys.stderr)
            return 2

        hint_dir = match.group(1)
        hint_readme = tmp_path / hint_dir / "README.md"
        actual_readme = tmp_path / ".game-of-cards" / "deck" / title / "README.md"

        print(f"hint says edit:    {hint_readme}")
        print(f"card actually at:  {actual_readme}")
        print(f"hint path exists?  {hint_readme.exists()}")
        print(f"actual path exists? {actual_readme.exists()}")

        if not actual_readme.exists():
            print("FAIL: goc new did not create the card at the expected path", file=sys.stderr)
            return 2

        if not hint_readme.exists():
            print(
                "DEFECT REPRODUCED: `Next:` hint points at a non-existent path "
                f"({hint_dir}/README.md) — the card lives at "
                f".game-of-cards/deck/{title}/README.md",
                file=sys.stderr,
            )
            return 1

        print("OK: hint path matches actual card path")
        return 0


if __name__ == "__main__":
    sys.exit(main())
