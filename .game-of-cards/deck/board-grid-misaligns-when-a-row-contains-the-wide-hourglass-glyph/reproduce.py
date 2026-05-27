"""Reproduce: `render_board` computes column widths and pads cells with
`len()` / `str.ljust()`, which count codepoints. The impediment marker
`⏳` (U+23F3) is East-Asian-width Wide — `len('⏳') == 1` but a terminal
renders it across 2 display columns. So a row bearing the marker is
padded one display column short, and its trailing `|` separator lands
one display column right of the header and of unmarked rows.

Exit 0 == the first `|` separator lands at the same DISPLAY column on
          the header, a marked row, and an unmarked row (defect fixed);
          unmarked rows stay aligned (no regression).
Exit 1 == the marked row's `|` is offset from the others (defect fires).
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

from goc.engine import Card, render_board  # noqa: E402


def dwidth(s: str) -> int:
    """Terminal display width: East-Asian Wide/Fullwidth count as 2."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def first_sep_display_col(row: str) -> int:
    """Display column of the first `|` cell separator on a rendered row."""
    idx = row.index("|")
    return dwidth(row[:idx])


def _card(title: str, **overlay) -> Card:
    fm = {"status": "open", "human_gate": "none", "contribution": "high"}
    fm.update(overlay)
    return Card(title=title, path=Path("."), frontmatter=fm, body="", dod_open=0, dod_done=0)


# An impeded card (waiting_on reason set) gets the ⏳ marker; a plain
# open card does not. Both land in the "open" column.
impeded = _card("impeded-card", waiting_on="external")
plain = _card("plain-card")

board = render_board([impeded, plain], max_rows=20, no_color=True)
lines = board.splitlines()

header = lines[0]
# lines[1] is the dashed separator rule; data rows start at lines[2:].
data_rows = lines[2:]

marked_row = next(r for r in data_rows if "⏳" in r)
unmarked_row = next(r for r in data_rows if r.strip() and "⏳" not in r)

header_col = first_sep_display_col(header)
marked_col = first_sep_display_col(marked_row)
unmarked_col = first_sep_display_col(unmarked_row)

print(f"  header   first-`|` display col: {header_col}")
print(f"  unmarked first-`|` display col: {unmarked_col}")
print(f"  marked   first-`|` display col: {marked_col}")
print()

if not (header_col == unmarked_col == marked_col):
    print(
        "DEFECT: the ⏳-bearing row's first `|` is offset from the header / "
        f"unmarked row ({marked_col} vs {header_col}) — grid skews."
    )
    sys.exit(1)
print("OK: all rows' first `|` separator align on the same display column")
sys.exit(0)
