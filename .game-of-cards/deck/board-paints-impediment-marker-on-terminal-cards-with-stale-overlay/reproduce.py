"""Proof: render_board paints the ⏳ impediment marker on terminal cards.

A card that carried a `waiting_on` overlay while it was live keeps that
overlay after it is closed — neither `goc done` nor
`goc status <t> disproved|superseded` clears it. `render_board`'s
`card_cell` predicate gates the *dependency-block* term on
`status == "open"` but leaves the *impediment* term ungated, so the
glyph fires in the done / disproved / superseded columns. A terminal
card cannot be impeded, so the marker is semantically wrong.

Exit 0 == defect reproduced (a terminal card got the ⏳).
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

from goc.engine import Card, render_board  # noqa: E402


def _card(title: str, status: str, *, waiting_on: str | None = None) -> Card:
    fm = {
        "title": title,
        "status": status,
        "contribution": "medium",
        "human_gate": "none",
        "tags": [],
        "advances": [],
        "advanced_by": [],
    }
    if waiting_on is not None:
        fm["waiting_on"] = waiting_on
    return Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter=fm,
        body="",
        dod_open=0,
        dod_done=1,
    )


def main() -> int:
    cards = [
        _card("done-clean", "done"),
        _card("done-with-stale-overlay", "done", waiting_on="external"),
        _card("disproved-with-stale-overlay", "disproved", waiting_on="resource"),
    ]
    board = render_board(cards, max_rows=20, no_color=True)
    print(board)
    print("-" * 60)

    def cell_has_marker(title: str) -> bool:
        # Columns are pipe-delimited; test only the cell that holds the title
        # so a ⏳ in a neighbouring column on the same row is not miscounted.
        for line in board.splitlines():
            for cell in line.split("|"):
                if title in cell:
                    return "⏳" in cell
        return False

    clean_marked = cell_has_marker("done-clean")
    stale_done_marked = cell_has_marker("done-with-stale-overlay")
    stale_disproved_marked = cell_has_marker("disproved-with-stale-overlay")

    print(f"done-clean              has ⏳: {clean_marked}   (expected False)")
    print(f"done-with-stale-overlay has ⏳: {stale_done_marked}   (expected False)")
    print(f"disproved-stale-overlay has ⏳: {stale_disproved_marked}   (expected False)")

    defect = stale_done_marked or stale_disproved_marked
    if defect:
        print("\nDEFECT REPRODUCED: a terminal (closed) card is painted impeded (⏳).")
        return 0
    print("\nNo defect: terminal cards carry no impediment marker.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
