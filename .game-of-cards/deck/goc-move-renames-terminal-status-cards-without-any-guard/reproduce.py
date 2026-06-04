"""Reproduce: `goc move` renames a card whose status is already terminal.

Constructs a throwaway deck containing a single `done` card, then invokes
`goc move` to rename it. The defect: the verb returns 0, performs the
directory rename, and rewrites every cross-reference across the tracked
tree — none of which is appropriate for a card whose slug is part of the
kanban record axis. The sibling state-flip verbs (`done`, `decide`,
`status`) all refuse terminal targets; `move` is one of the remaining
members of the family without a closed-card audit (alongside `wait`,
`attest`, and `quality-pass`, each tracked by its own card).

Run via `uv run python .game-of-cards/deck/goc-move-renames-terminal-status-cards-without-any-guard/reproduce.py`.
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


REPO_ROOT = _repo_root()


CARD_README = """\
---
title: dummy-closed-card
summary: "A closed card used to reproduce the goc-move closed-card defect."
status: done
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: "2026-01-02T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: closed
---

# dummy-closed-card

Closed for reproduction purposes.
"""

CARD_LOG = """\
## 2026-01-02T00:00:00Z: closure

Closed.
"""

CONFIG_YAML = """\
workflow:
  auto_commit: false
"""


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-move-repro-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.email", "x@y"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.name", "x"], cwd=workdir, check=True)
        (workdir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        deck_dir = workdir / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)
        (workdir / ".game-of-cards" / "config.yaml").write_text(CONFIG_YAML)
        old_slug = "dummy-closed-card"
        new_slug = "dummy-closed-card-renamed"
        old_card = deck_dir / old_slug
        old_card.mkdir()
        (old_card / "README.md").write_text(CARD_README)
        (old_card / "log.md").write_text(CARD_LOG)

        subprocess.run(["git", "add", "."], cwd=workdir, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "initial"], cwd=workdir, check=True
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "move", old_slug, new_slug],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )

        print("=" * 72)
        print(f"goc move {old_slug} {new_slug}  (card status: done)")
        print("=" * 72)
        print("exit code:", result.returncode)
        print()
        print("--- stdout ---")
        print(result.stdout)
        print("--- stderr ---")
        print(result.stderr)

        new_card = deck_dir / new_slug
        old_still_exists = old_card.exists()
        new_exists = new_card.exists()
        renamed = (not old_still_exists) and new_exists
        refused = (
            result.returncode != 0
            and "terminal" in (result.stderr + result.stdout).lower()
            and not renamed
        )

        print("=" * 72)
        print("DEFECT CHECK")
        print("=" * 72)
        print(f"  card status:                       done (closed 2026-01-02)")
        print(f"  directory renamed by move verb:    {renamed}")
        print(f"  verb refused with terminal-guard:  {refused}")
        if renamed:
            print(
                "\nDEFECT REPRODUCED: `goc move` silently retitled a closed "
                "card. The slug is part of the kanban record axis — every "
                "existing cross-reference (in other cards' bodies, log.md "
                "entries, this repo's tracked files) was rewritten to the "
                "new slug. Sibling mutation verbs (`done`, `decide`, "
                "`status`) refuse terminal targets; `move` does not."
            )
            return 0
        print("\nNo defect — `goc move` correctly refused to rename the closed card.")
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
