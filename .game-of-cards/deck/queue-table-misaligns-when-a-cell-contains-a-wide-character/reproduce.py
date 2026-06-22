"""Proof: `render_table` (the default `goc` queue view) computes column widths
with `len()` and pads with `str.ljust()` — both codepoint-based — so a cell
containing an East-Asian *wide* character (which occupies two terminal columns)
pushes every following column out of alignment.

`render_board` was fixed for exactly this (see the closed card
`board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph`) by
switching to `_display_width` / `_display_ljust`; `render_table` was left
untouched.

This script renders a two-card deck — one ASCII title, one with three CJK
glyphs (6 display columns, len()==3) — through both renderers and checks that
the second column starts at the same *display* column on the wide-title row as
on the ASCII row.
"""

import sys
import unicodedata
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


def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def second_col_start(line: str) -> int:
    """Display column at which the *second* column (STATUS) begins.

    Skips the leading title run, then the run of spaces (the title-column
    padding plus the inter-column separator), and reports the display column
    where the next non-space cell starts. Measuring the title text's own end
    is the wrong invariant: the widest title fills its column with zero
    trailing pad, so its text always runs to a different display column than a
    shorter title's — the grid is aligned iff the *next* column starts at the
    same display column on both rows.
    """
    i = 0
    while i < len(line) and line[i] != " ":
        i += 1
    while i < len(line) and line[i] == " ":
        i += 1
    return display_width(line[:i])


def make_card(title):
    fm = {
        "title": title,
        "status": "open",
        "stage": None,
        "contribution": "medium",
        "summary": "",
        "human_gate": "none",
        "created": "2026-01-01T00:00:00Z",
        "closed_at": None,
        "advances": [],
        "advanced_by": [],
        "tags": [],
    }
    return engine.Card(title=title, path=Path("/tmp") / title, frontmatter=fm, body="", dod_open=1, dod_done=0)


wide = make_card("日本語-title")  # 3 wide glyphs + "-title"
ascii_card = make_card("ascii-title")
cards = [wide, ascii_card]

table = engine.render_table(cards, verbose=0, no_color=True).splitlines()
# Data rows are after the header + separator (lines 0 and 1).
wide_row = next(ln for ln in table if ln.startswith("日本語"))
ascii_row = next(ln for ln in table if ln.startswith("ascii-title"))

wide_gap = second_col_start(wide_row)
ascii_gap = second_col_start(ascii_row)

print("TABLE rows:")
print("  " + wide_row)
print("  " + ascii_row)
print(f"  STATUS column starts at display col: wide-row={wide_gap}  ascii-row={ascii_gap}")

aligned = wide_gap == ascii_gap
print()
if aligned:
    print("no defect (columns aligned)")
    sys.exit(0)
print(
    f"DEFECT REPRODUCED: the STATUS column starts at display col {wide_gap} on the "
    f"wide-glyph row vs {ascii_gap} on the ASCII row — the grid is skewed by "
    f"{wide_gap - ascii_gap} columns."
)
sys.exit(1)
