#!/usr/bin/env python3
"""The queue table renders a draft scaffold exactly like an authored card.

`goc --status all` is the one table that lists unauthored scaffolds
(`filter_cards` hides `card_is_draft` cards from every other listing), and
`Skill(create-card)` dedups against it with `goc --status all | grep`. This
script builds a two-card deck in which the cards match in every rendered
field (status, contribution, gate, tags, created, summary, DoD, body). The
only differences are the title and the `draft: true` flag on one of them.
Both titles are 13 characters long, so the TITLE column is the same width
either way.

It runs the real CLI at `-v` 0, 1 and 2, takes each card's block (its row
plus any indented detail lines), replaces the title with a placeholder and
compares the two blocks. If they are identical, the table cannot tell the
draft from the authored card at that verbosity. The board and `--json`
renderings are printed for context: both already mark the draft.

Exits 0 once every verbosity tells the two cards apart; exits 1 while any
verbosity renders them identically.
"""

import json
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
DRAFT = "scaffold-card"
AUTHORED = "authored-card"
assert len(DRAFT) == len(AUTHORED)

CARD = """---
title: {title}
summary: "One summary shared by both cards."
status: open
stage: null
contribution: medium
created: "2026-09-28T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story]
definition_of_done: |
  - [ ] TDD: one criterion shared by both cards
{draft}---

# {title}

One body shared by both cards.
"""


def _write_deck(root: Path) -> None:
    deck = root / ".game-of-cards" / "deck"
    for title, draft in ((DRAFT, "draft: true\n"), (AUTHORED, "")):
        (deck / title).mkdir(parents=True)
        (deck / title / "README.md").write_text(CARD.format(title=title, draft=draft))


def _goc(root: Path, *args: str) -> str:
    env = os.environ.copy()
    env.pop("GOC_WORKER", None)
    env["NO_COLOR"] = "1"
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"goc {' '.join(args)} exited {result.returncode}:\n{result.stderr}")
    return result.stdout


def _block(table: str, title: str) -> list[str]:
    """The card's row plus the indented detail lines under it."""
    lines = table.splitlines()
    start = next(i for i, line in enumerate(lines) if line.split(" ", 1)[0] == title)
    block = [lines[start]]
    for line in lines[start + 1:]:
        if not line.startswith("    "):
            break
        block.append(line)
    return block


def _masked(block: list[str], title: str) -> list[str]:
    return [line.replace(title, "<TITLE>") for line in block]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_deck(root)

        print("=== goc --status all --board (OPEN column) ===")
        for line in _goc(root, "--status", "all", "--board", "--no-color").splitlines():
            print(f"  {line.split('|')[0].rstrip()}")

        print("\n=== goc --status all --json --slim (draft field) ===")
        for record in json.loads(_goc(root, "--status", "all", "--json", "--slim")):
            print(f"  {record['title']:<14} draft={record['draft']}")

        failures = []
        for verbose in (0, 1, 2):
            flags = ["-v"] * verbose
            label = " ".join(["goc --status all", *(["-" + "v" * verbose] if verbose else [])])
            table = _goc(root, "--status", "all", "--no-color", *flags)
            draft_block = _block(table, DRAFT)
            authored_block = _block(table, AUTHORED)
            same = _masked(draft_block, DRAFT) == _masked(authored_block, AUTHORED)
            print(f"\n=== {label} === draft distinguishable: {not same}")
            for line in table.splitlines():
                print(f"  {line}")
            if same:
                failures.append(label)

        print("\n=== verdict ===")
        if failures:
            print(
                f"DEFECT: {len(failures)} table view(s) render the draft and the authored "
                f"card identically once the titles are masked: {'; '.join(failures)}"
            )
            print("  the board marks the draft ✎ and --json carries draft: true")
            return 1
        print("OK: every --status all table verbosity tells the draft from the authored card")
        return 0


if __name__ == "__main__":
    sys.exit(main())
