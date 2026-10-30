"""Reproduce: `goc new --tag X --tag X` writes duplicate tags to disk.

Runs `goc new` from this source tree in a fresh temp deck (this repo's deck
is untouched), passing `--tag bug --tag bug --tag documentation --tag bug`,
and reads the new card's `tags` back through the engine's frontmatter parser.

Expected behavior (after the fix): `tags: [bug, documentation]`.
Pre-fix behavior:                  `tags: [bug, bug, documentation, bug]`.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken. The positive control is that the tags read back are
one of those two lists: `goc new` failing, no card, no `tags` list or any
other value exits 2 rather than passing for a verdict. The script was filed
inverted (exit 0 while the defect fired) and was rewritten to this contract
when the fix landed.

Run with:  uv run python .game-of-cards/deck/goc-new-writes-duplicate-tags-when-tag-flag-is-repeated/reproduce.py
"""

from __future__ import annotations

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


REPO = _repo_root()
sys.path.insert(0, str(REPO))

from goc.engine import FrontmatterError, parse_frontmatter  # noqa: E402

REQUESTED = ["bug", "bug", "documentation", "bug"]
DEDUPED = ["bug", "documentation"]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("GOC_WORKTREE_DECK", None)
        flags = [arg for tag in REQUESTED for arg in ("--tag", tag)]
        res = subprocess.run(
            [sys.executable, "-m", "goc.cli", "new", "test-dedup-card", "--contribution", "low", *flags],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
        print(f"$ goc new test-dedup-card --contribution low {' '.join(flags)}")
        print(f"  exit {res.returncode}")
        if res.returncode != 0:
            print(f"HARNESS: goc new failed:\n{res.stderr}", file=sys.stderr)
            return 2

        readme = cwd / ".game-of-cards" / "deck" / "test-dedup-card" / "README.md"
        try:
            fm, _ = parse_frontmatter(readme.read_text())
        except (OSError, FrontmatterError) as exc:
            print(f"HARNESS: cannot read the new card's frontmatter: {exc}", file=sys.stderr)
            return 2
        tags = fm.get("tags")
        if not isinstance(tags, list):
            print(f"HARNESS: the new card has no tags list (got {tags!r})", file=sys.stderr)
            return 2

        print(f"tags written to disk: [{', '.join(map(str, tags))}]")
        if tags == DEDUPED:
            print("No duplicates — defect no longer fires.")
            return 0
        if tags == REQUESTED:
            print("DUPLICATES PRESENT — defect fires.")
            return 1
        print(f"HARNESS: tags are neither {DEDUPED} nor {REQUESTED}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
