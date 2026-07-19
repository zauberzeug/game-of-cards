#!/usr/bin/env python3
"""install-overwrites-authored-deck-journal-when-version-sentinel-is-missing

`goc install`'s only already-installed guard is the `.goc-version` sentinel
(`_find_installed_deck_dir`, goc/install.py:453-461, consumed at :1538-1544).
When a real deck exists but the sentinel file is absent, install() proceeds
and unconditionally rewrites `.game-of-cards/deck/log.md`
(goc/install.py:1562), destroying the authored deck journal.

Exits ZERO when the authored journal survives (defect fixed);
exits NONZERO while the defect fires.
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


ROOT = _repo_root()
AUTHORED_LINE = "- 2026-01-01: sprint retro notes we must not lose."


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        deck = target / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        (deck / "log.md").write_text(f"# Deck Log\n\n{AUTHORED_LINE}\n")
        # No .goc-version sentinel — the shape of a hand-adopted deck or a
        # copy that skipped dotfiles (glob cp, rsync exclude, archive export).
        env = {**os.environ, "PYTHONPATH": str(ROOT)}
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "install", "--codex"],
            cwd=target, env=env, capture_output=True, text=True,
        )
        after = (deck / "log.md").read_text()
        print(f"goc install rc: {result.returncode}")
        print("deck/log.md after install:")
        print(after)
        if AUTHORED_LINE in after:
            print("PASS: authored deck journal survived `goc install`")
            return 0
        print(
            "FAIL: `goc install` overwrote the authored deck journal "
            "(sentinel-less deck was treated as a fresh target)"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
