"""Reproduce: render_board silently drops cards beyond --max-rows.

A status column holding more cards than `max_rows` is sliced down with
no "+N more" indicator, so a reader cannot tell the column was
truncated. This script builds a synthetic deck of N open cards, renders
the board with a small max_rows, and asserts that the truncated column
advertises the hidden count.

Exits 0 when the indicator is present (bug fixed), 1 otherwise.
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

from goc import engine  # noqa: E402


def _make_card(title: str) -> engine.Card:
    fm = {
        "title": title,
        "status": "open",
        "contribution": "medium",
        "human_gate": "none",
        "advances": [],
        "advanced_by": [],
        "tags": ["bug"],
    }
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter=fm,
        body="",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    total = 25
    max_rows = 5
    cards = [_make_card(f"card-{i:02d}") for i in range(total)]

    board = engine.render_board(cards, max_rows=max_rows, no_color=True)

    open_col_rows = 0
    for line in board.splitlines()[2:]:  # skip header + separator
        first_cell = line.split(" | ")[0]
        if first_cell.strip():
            open_col_rows += 1

    hidden = total - max_rows
    has_indicator = f"+{hidden} more" in board

    print(f"open cards filed       : {total}")
    print(f"max_rows               : {max_rows}")
    print(f"non-empty OPEN rows     : {open_col_rows}")
    print(f"expected hidden count  : {hidden}")
    print(f"'+{hidden} more' present: {has_indicator}")
    print("---- board ----")
    print(board)

    if not has_indicator:
        print(
            f"\nFAIL: OPEN column hid {hidden} cards with no '+N more' indicator.",
            file=sys.stderr,
        )
        return 1

    print(f"\nPASS: truncated OPEN column advertises '+{hidden} more'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
