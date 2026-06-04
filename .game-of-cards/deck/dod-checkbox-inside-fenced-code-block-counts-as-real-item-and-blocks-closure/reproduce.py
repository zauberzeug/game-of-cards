"""Reproduce: a `- [ ]` checkbox shown inside a ```-fenced code block within a
card's `definition_of_done` is counted as a real, unchecked DoD item, which
hard-blocks `goc done` on an otherwise-complete card.

Run: uv run python .game-of-cards/deck/dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure/reproduce.py
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

from goc.engine import count_dod_boxes, untagged_dod_items  # noqa: E402

# A DoD whose single real item is checked, plus an illustrative checkbox shown
# inside a fenced code block (the kind of example a card about DoD parsing would
# naturally carry in its own DoD).
dod = (
    "- [x] MECHANICAL: the one real DoD item, completed\n"
    "For future authors, a DoD checkbox line looks like:\n"
    "```\n"
    "- [ ] write a failing test first\n"
    "```\n"
)

open_n, done_n = count_dod_boxes(dod)
print(f"count_dod_boxes -> open={open_n} done={done_n}")
print(f"untagged_dod_items -> {untagged_dod_items(dod)}")

expected_open, expected_done = 0, 1
if (open_n, done_n) == (expected_open, expected_done):
    print("PASS: fenced example line is not counted as a DoD checkbox")
    sys.exit(0)
else:
    print(
        f"FAIL: expected open={expected_open} done={expected_done}; "
        f"the fenced example line `- [ ] write a failing test first` is being "
        f"counted as a real unchecked box, so `goc done` refuses to close the card"
    )
    sys.exit(1)
