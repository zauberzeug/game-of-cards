"""Proof: render_board gives an impeded card (active waiting_on overlay)
no marker, so it is visually indistinguishable from a genuinely pullable
card — even though card_is_ready excludes it from the pull queue.

A clean board renderer should mark the impeded card the same way it
marks a dependency-blocked card (the ⏳ glyph), since both are "not
ready to pull" per the three-axis model.
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

from goc.engine import Card, card_is_ready, render_board  # noqa: E402


def _card(title: str, **fm) -> Card:
    base = {
        "title": title,
        "status": "open",
        "contribution": "high",
        "human_gate": "none",
        "advances": [],
        "advanced_by": [],
        "tags": [],
    }
    base.update(fm)
    return Card(
        title=title,
        path=Path(title),
        frontmatter=base,
        body="",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    plain = _card("plain-pullable-card")
    impeded = _card("impeded-card", waiting_on="external")
    cards = [plain, impeded]
    by_title = {c.title: c for c in cards}

    print("=== card_is_ready (the pull-queue predicate) ===")
    for c in cards:
        print(f"  {c.title:24s} ready={card_is_ready(c, by_title)}")

    board = render_board(cards, max_rows=20, no_color=True, by_title=by_title)
    print("\n=== render_board OPEN column cells ===")
    open_lines = []
    for line in board.splitlines():
        cell = line.split("|")[0].strip()
        if cell and cell != "OPEN" and not set(cell) <= {"-", "+"}:
            open_lines.append(cell)
            print(f"  {cell!r}")

    plain_cell = next((c for c in open_lines if c.startswith("plain-pullable")), "")
    impeded_cell = next((c for c in open_lines if c.startswith("impeded-card")), "")

    print("\n=== verdict ===")
    print(f"  plain_is_ready   = {card_is_ready(plain, by_title)}")
    print(f"  impeded_is_ready = {card_is_ready(impeded, by_title)}")
    print(f"  plain_board_marker   = {plain_cell[len('plain-pullable-card'):]!r}")
    print(f"  impeded_board_marker = {impeded_cell[len('impeded-card'):]!r}")

    impeded_has_marker = "⏳" in impeded_cell  # ⏳
    if not card_is_ready(impeded, by_title) and not impeded_has_marker:
        print(
            "\nDEFECT CONFIRMED: impeded card is hidden from the pull queue "
            "(ready=False) but the board renders it with no ⏳ overlay marker "
            "— indistinguishable from the pullable card."
        )
        return 1
    print("\nNo defect: impeded card carries a board marker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
