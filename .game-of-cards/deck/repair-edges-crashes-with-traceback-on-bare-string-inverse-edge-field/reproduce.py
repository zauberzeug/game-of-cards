#!/usr/bin/env python3
"""Reproduce: goc repair-edges crashes with an uncaught ValueError traceback
on a bare-string inverse edge field — the exact corruption `goc validate`
tells the user to run `goc repair-edges --apply` to fix.

The half-edge DETECTOR (`find_half_edges`) tolerates a bare-string inverse
field by coercing it to [] and emitting a half-edge. The half-edge REPAIRER
(`_add_to_list_field`) rejects that same bare string with `raise ValueError`,
which is uncaught all the way up through `_repair_edge_diff` /
`_cmd_repair_edges` (and `_mutate_pair` for `goc advance`). So the repair tool
dies on the corruption it is pointed at.

Run: uv run python .game-of-cards/deck/.../reproduce.py
"""
import sys
import tempfile
import traceback
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD_A = """\
---
title: card-a
summary: "A card that advances card-b."
status: open
contribution: medium
created: "2026-06-23T00:00:00Z"
human_gate: none
advances:
- card-b
advanced_by: []
supersedes: []
superseded_by: []
tags: [infra]
definition_of_done: |
  - [ ] x
---

## Goal
Body.
"""

# card-b.advanced_by is a bare STRING scalar, not a list. The value (`card-a`)
# is semantically correct; only the YAML shape is wrong — exactly what a hand
# edit or a one-shot-authored card produces.
CARD_B = """\
---
title: card-b
summary: "A card advanced by card-a, but advanced_by is a bare string."
status: open
contribution: medium
created: "2026-06-23T00:00:00Z"
human_gate: none
advances: []
advanced_by: card-a
supersedes: []
superseded_by: []
tags: [infra]
definition_of_done: |
  - [ ] x
---

## Goal
Body.
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        deck = Path(td) / "deck"
        (deck / "card-a").mkdir(parents=True)
        (deck / "card-b").mkdir(parents=True)
        (deck / "card-a" / "README.md").write_text(CARD_A)
        (deck / "card-b" / "README.md").write_text(CARD_B)
        (deck / "card-a" / "log.md").write_text("")
        (deck / "card-b" / "log.md").write_text("")

        # Point the engine at our temp deck.
        engine.DECK_DIR = deck

        cards = engine.load_all_cards()
        half_edges = engine.find_half_edges(cards)
        print(f"DETECTOR: find_half_edges reports {len(half_edges)} half-edge(s)")
        for he in half_edges:
            print(f"  repair_title={he.repair_title!r} "
                  f"repair_field={he.repair_field!r} "
                  f"repair_value={he.repair_value!r}")

        print()
        print("REPAIRER: _repair_edge_diff on that same half-edge:")
        try:
            diff = engine._repair_edge_diff(half_edges[0])
            print("  produced a diff (no crash):")
            for line in diff:
                print("    " + line)
            print("\nUNEXPECTED: repairer did NOT crash — bug may be fixed.")
            return 1
        except ValueError as exc:
            print("  CRASHED with uncaught ValueError:")
            traceback.print_exc()
            print(f"\nCONFIRMED: the validator-recommended repair path raises "
                  f"{exc!r} instead of repairing the bare-string field.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
