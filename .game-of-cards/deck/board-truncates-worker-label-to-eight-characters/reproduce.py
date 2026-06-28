"""Reproduce: goc --board truncates the worker label to 8 characters.

The board appends each card's worker as `@<who>` but slices `who[:8]`.
Since the closed card `board-active-card-worker-label-not-truncated`
switched the board to size columns to their widest rendered cell, that
slice no longer serves any layout purpose — it only hides coordination
information. This script builds a card whose worker `who` is
`claude[bot]` (11 chars), renders the board, and shows the label is cut
to `@claude[b` even though the column has ample room for the full value.

Run on a clean checkout:
    uv run python deck/board-truncates-worker-label-to-eight-characters/reproduce.py
Exit code 0 once the defect is fixed (full label present); 1 while it fires.
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


def main() -> int:
    who = "claude[bot]"
    card = engine.Card(
        title="short-title",
        path=Path("short-title"),
        frontmatter={
            "title": "short-title",
            "status": "active",
            "contribution": "medium",
            "created": "2026-01-01",
            "human_gate": "none",
            "worker": {"who": who},
        },
        body="body",
        dod_open=1,
        dod_done=0,
    )

    board = engine.render_board([card], max_rows=20, no_color=True)
    # The ACTIVE column cell is the line carrying the title.
    cell_line = next(line for line in board.splitlines() if "short-title" in line)
    active_cell = cell_line.split("|")[1].strip() if "|" in cell_line else cell_line.strip()

    active_col_width = max(len(line.split("|")[1]) for line in board.splitlines() if "|" in line)
    full_label = f"@{who}"
    present = full_label in board

    print(f"worker frontmatter who: {who}  ({len(who)} chars)")
    print(f"ACTIVE column width: {active_col_width} chars (room for the full label)")
    print(f"board cell: {active_cell!r}")
    print(f"full {full_label!r} present in cell? {present}")

    if not present:
        print("DEFECT: worker label truncated to 8 chars despite the column having room.")
        return 1
    print("OK: full worker label rendered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
