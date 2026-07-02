"""Reproduce: a bare `title:` (parses to None) crashes queue/board renderers.

Before the fix, `Card.title` is `None` for a card whose frontmatter has a
bare `title:`, and `render_table` / `render_board` raise
`TypeError: 'NoneType' object is not iterable` while measuring the title
cell width — aborting the whole deck's queue, not just the one bad card.

After the fix, `Card.title` falls back to the directory name (mirroring the
status/contribution/human_gate coercions) and the deck renders.

Exits 0 when the defect is gone, 1 while it fires.
"""

import os
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


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD = """---
title:
status: open
contribution: medium
created: "2026-01-01"
human_gate: none
definition_of_done: |
  - [ ] do the thing
---
Body.
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        deck = Path(tmp) / ".game-of-cards" / "deck" / "card-with-empty-title"
        deck.mkdir(parents=True)
        (deck / "README.md").write_text(CARD)
        (deck / "log.md").write_text("")

        card = engine.load_card(deck)
        print("Card.title repr:", repr(card.title))
        print("Card.status repr:", repr(card.status))

        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            engine.DECK_DIR = Path(tmp) / ".game-of-cards" / "deck"
            cards = engine.load_all_cards()
            try:
                engine.render_table(cards, verbose=0, no_color=True)
                engine.render_board(cards, max_rows=20, no_color=True)
            except TypeError as e:
                print("DEFECT FIRES: renderer crashed:", e)
                return 1
        finally:
            os.chdir(cwd)

    if card.title is None:
        print("DEFECT FIRES: Card.title is None (should fall back to dir name)")
        return 1

    print("OK: bare title falls back to dir name; queue and board render")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
