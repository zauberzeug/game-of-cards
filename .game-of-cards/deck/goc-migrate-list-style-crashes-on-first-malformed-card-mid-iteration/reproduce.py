"""Reproduce: `goc migrate-list-style` aborts mid-iteration on a malformed card.

Builds a temporary deck with two cards:
  - card-a: valid frontmatter, inline-flow `advances` that the migration verb
    would rewrite to block style.
  - card-b: opening `---` with no closing delimiter — parse_frontmatter raises
    FrontmatterError.

Then runs `python -m goc.cli migrate-list-style` (and `--dry-run`) against
that deck and prints exit code + stderr tail. The defect: the verb crashes
with a Python traceback instead of warning-and-continuing on card-b.

After the fix is applied (wrap parse_frontmatter in a FrontmatterError net
inside `_cmd_migrate_list_style`), both runs exit 0 and the broken card
surfaces as a single `WARNING:` line on stderr. This reproducer exits 0
when the fix is in place (no FrontmatterError traceback, both runs zero,
warning surfaced for the broken card, valid card-a reported as rewritten)
and exits 1 if any of those properties fail.
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


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))


CARD_A = """---
title: card-a
summary: ""
status: open
stage: null
contribution: low
created: "2026-05-29T00:00:00Z"
closed_at: null
human_gate: none
advances: [card-b-imaginary-peer]
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] (placeholder)
---

# card-a

Body.
"""


CARD_B_BROKEN = """---
title: card-b
summary: "unterminated frontmatter — opening --- with no closing delimiter"
status: open
"""


def _build_deck(root: Path) -> None:
    deck = root / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    (root / ".game-of-cards" / "config.yaml").write_text("skills_source: vendored\n")
    (deck / "card-a").mkdir()
    (deck / "card-a" / "README.md").write_text(CARD_A)
    (deck / "card-a" / "log.md").write_text("")
    (deck / "card-b").mkdir()
    (deck / "card-b" / "README.md").write_text(CARD_B_BROKEN)
    (deck / "card-b" / "log.md").write_text("")


def _run_migrate(cwd: Path, extra: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", "migrate-list-style", *extra],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _build_deck(root)

        print("== goc migrate-list-style --dry-run ==")
        rc, out, err = _run_migrate(root, ["--dry-run"])
        print(f"exit code: {rc}")
        print("stdout:")
        for line in out.splitlines()[-6:]:
            print(f"  {line}")
        print("stderr tail:")
        for line in err.splitlines()[-6:]:
            print(f"  {line}")
        print()

        print("== goc migrate-list-style ==")
        rc2, out2, err2 = _run_migrate(root, [])
        print(f"exit code: {rc2}")
        print("stdout:")
        for line in out2.splitlines()[-6:]:
            print(f"  {line}")
        print("stderr tail:")
        for line in err2.splitlines()[-6:]:
            print(f"  {line}")
        print()

        broken_traceback = "FrontmatterError" in err or "FrontmatterError" in err2
        both_zero = rc == 0 and rc2 == 0
        warning_surfaced = (
            "WARNING: card-b:" in err and "WARNING: card-b:" in err2
        )
        valid_rewritten = "card-a" in out and "card-a" in out2
        print(f"defect fires (FrontmatterError reached stderr): {broken_traceback}")
        print(f"both runs exit zero: {both_zero}")
        print(f"warning surfaced for card-b on both runs: {warning_surfaced}")
        print(f"valid card-a reported in both runs: {valid_rewritten}")
        ok = (
            not broken_traceback
            and both_zero
            and warning_surfaced
            and valid_rewritten
        )
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
