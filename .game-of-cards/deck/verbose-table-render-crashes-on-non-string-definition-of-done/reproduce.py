"""Reproduce: `goc -vv` crashes on a card whose definition_of_done is a list.

Builds a Card whose `definition_of_done` frontmatter parsed to a YAML
list (a truthy non-string) exactly the way `load_card` does, then drives
`render_table` at three verbosity levels. Before the fix, verbose=2 raises
`AttributeError: 'list' object has no attribute 'splitlines'` while
verbose=0/1 render fine. After the fix, all three render.
"""

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import (  # noqa: E402
    Card,
    count_dod_boxes,
    parse_frontmatter,
    render_table,
)

CARD_TEXT = """---
title: list-dod-card
status: open
human_gate: none
contribution: medium
tags: [bug]
definition_of_done:
  - a
  - b
---

body
"""


def _build_card() -> Card:
    fm, body = parse_frontmatter(CARD_TEXT)
    dod_open, dod_done = count_dod_boxes(fm.get("definition_of_done", ""))
    return Card(
        title=fm.get("title") or "list-dod-card",
        path=Path("list-dod-card"),
        frontmatter=fm,
        body=body,
        dod_open=dod_open,
        dod_done=dod_done,
    )


def main() -> int:
    card = _build_card()
    assert isinstance(card.frontmatter["definition_of_done"], list), (
        "expected the YAML block list to parse to a Python list"
    )

    crashed = False
    for level in (0, 1, 2):
        try:
            render_table([card], verbose=level, no_color=True)
            print(f"v{level}: renders OK")
        except AttributeError as exc:
            crashed = True
            print(f"v{level}: AttributeError: {exc}")

    if crashed:
        print("\nDEFECT PRESENT: -vv render crashed on a non-string DoD.")
        return 1
    print("\nOK: all verbosity levels survived a non-string DoD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
