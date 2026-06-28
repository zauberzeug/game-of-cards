"""Reproduce: the verbose table prints `awaiting: ... (you may start)`
for an `active` card with an open prereq, while the board (the other
human-facing renderer) suppresses the marker for the same card.

Exits non-zero while the defect is present, zero once the table is
gated to open cards (matching the board's documented open-only slice).
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


def _card(title: str, status: str, advanced_by: list[str]) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": status,
            "contribution": "medium",
            "human_gate": "none",
            "created": "2026-06-18",
            "summary": f"{title} summary",
            "tags": [],
            "advances": [],
            "advanced_by": advanced_by,
            "supersedes": [],
            "superseded_by": [],
            "definition_of_done": "- [x] done\n",
        },
        body="body",
        dod_open=0,
        dod_done=1,
    )


def _awaiting_lines_for(out: str, title: str) -> list[str]:
    found: list[str] = []
    in_block = False
    for line in out.splitlines():
        if line.startswith(title + " ") or line == title:
            in_block = True
            continue
        if in_block:
            if line.startswith("    "):
                if line.strip().startswith("awaiting:"):
                    found.append(line.strip())
            else:
                in_block = False
    return found


def main() -> int:
    prereq = _card("prereq-open", "open", [])
    active = _card("active-dep", "active", ["prereq-open"])
    open_ = _card("open-dep", "open", ["prereq-open"])
    cards = [active, open_, prereq]

    table = engine.render_table(cards, verbose=1, no_color=True)
    board = engine.render_board(cards, no_color=True, max_rows=100)

    print("=== TABLE (verbose) ===")
    print(table)
    print("=== BOARD ===")
    print(board)
    print()

    active_table = _awaiting_lines_for(table, "active-dep")
    open_table = _awaiting_lines_for(table, "open-dep")
    # The board flags not-ready cards with a hourglass; locate the
    # active card's cell and confirm it carries no marker.
    active_board_flagged = "active-dep [m] ⏳" in board
    open_board_flagged = "open-dep [m] ⏳" in board

    print(f"table awaiting on active card: {active_table}")
    print(f"table awaiting on open card:   {open_table}")
    print(f"board flags active card (⏳):   {active_board_flagged}")
    print(f"board flags open card (⏳):     {open_board_flagged}")
    print()

    ok = True
    if active_table:
        print("FAIL: table shows the 'you may start' advisory on an ACTIVE card")
        ok = False
    if not open_table:
        print("FAIL: table dropped the advisory on an OPEN card (regression)")
        ok = False
    if active_board_flagged:
        print("FAIL: board flagged the active card (unexpected)")
        ok = False
    if not open_board_flagged:
        print("FAIL: board dropped the marker on the open card (regression)")
        ok = False

    if ok:
        print("PASS: table and board agree — active card carries no dependency advisory")
        return 0
    print(
        "Defect present: the table and board disagree on the active card's "
        "dependency advisory."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
