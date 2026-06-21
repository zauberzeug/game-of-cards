"""Reproduce: `goc repair-edges` dry-run overstates the repairs `--apply` makes.

The dry-run classifies every half-edge against ONE original snapshot, while
`--apply` re-loads before each edge so its cycle checks see earlier same-run
repairs. On a deck where repairing one half-edge creates the advances cycle
that makes a second half-edge structural, the dry-run promises N repairs but
`--apply` performs fewer and exits non-zero.

Exits non-zero while the bug is present (dry-run count > apply count); exits
zero once the two passes agree on the repair set (the fix has landed).
"""

import os
import re
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

CARD = """\
---
title: {title}
summary: "{title}"
status: open
stage: null
contribution: medium
created: 2026-06-21
closed_at: null
human_gate: none
advances: []
advanced_by:
  - {other}
tags: [bug]
definition_of_done: |
  - [ ] x
---
# {title}
"""


def _goc(args, cwd):
    env = dict(os.environ)
    return subprocess.run(
        ["uv", "run", "--project", str(REPO), "goc", *args],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q"], cwd=root, check=False)
        deck = root / ".game-of-cards" / "deck"
        # Two interacting half-edges: each card's advanced_by names the other,
        # but neither card has the matching advances entry. Repairing one adds
        # an advances forward edge that closes a cycle for the other.
        for title, other in (("card-a", "card-b"), ("card-b", "card-a")):
            d = deck / title
            d.mkdir(parents=True)
            (d / "README.md").write_text(CARD.format(title=title, other=other))
            (d / "log.md").write_text("")

        dry = _goc(["repair-edges"], root)
        apply = _goc(["repair-edges", "--apply"], root)

        m = re.search(r"would be repaired \((\d+)\)", dry.stdout)
        dry_count = int(m.group(1)) if m else 0
        apply_count = len(re.findall(r"^repaired: ", apply.stdout, re.M))

        print("=== DRY RUN (stdout) ===")
        print(dry.stdout.rstrip())
        print("=== APPLY (stdout) ===")
        print(apply.stdout.rstrip())
        if apply.stderr.strip():
            print("=== APPLY (stderr) ===")
            print(apply.stderr.rstrip())
        print(f"\ndry-run promised: {dry_count}")
        print(f"apply performed:  {apply_count}")
        print(f"apply exit:       {apply.returncode}")

        if dry_count > apply_count:
            print(
                f"\nFAIL (bug present): dry-run promised {dry_count} repairs but "
                f"apply performed {apply_count} — the preview overstates."
            )
            return 1
        print("\nPASS (fixed): dry-run and apply agree on the repair set.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
