"""Reproducer: `render_json` passes bare-string edge fields through as JSON
strings instead of coercing to lists.

Builds a tempdir deck with one card whose `advances` / `advanced_by` /
`supersedes` / `superseded_by` are bare-string scalars (the loader-tolerated
hand-edit shape, also produced by closed-sibling `goc unadvance` /
`_remove_from_list_field` bugs in the same family). Invokes `render_json`
directly and asserts the JSON record carries lists; currently the assertion
fails because each field round-trips as the bare string.

Exits 1 on observed defect, 0 if the fix has landed.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import goc.engine as e


CARD = """\
---
title: bare-edge-victim
status: open
contribution: medium
created: 2026-05-30
human_gate: none
advances: a-card
advanced_by: b-card
supersedes: c-card
superseded_by: d-card
tags: [bug]
definition_of_done: |
  - [ ] test
---

# bare-edge-victim
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        card_dir = root / ".game-of-cards" / "deck" / "bare-edge-victim"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(CARD)

        e.DECK_DIR = card_dir.parent
        e.REPO_ROOT = root

        cards = e.load_all_cards()
        record = json.loads(e.render_json(cards))[0]

        failures = []
        for field in ("advances", "advanced_by", "supersedes", "superseded_by"):
            value = record[field]
            if not isinstance(value, list):
                failures.append(f"{field!r} -> {value!r} (type {type(value).__name__})")

        if failures:
            print("DEFECT — render_json emits bare-string edge fields as strings:")
            for f in failures:
                print(f"  {f}")
            print(
                "\nExpected: each of advances/advanced_by/supersedes/superseded_by "
                "is a JSON list. Actual: each is the bare string verbatim."
            )
            return 1
        print("OK — render_json coerces bare-string edge fields to lists.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
