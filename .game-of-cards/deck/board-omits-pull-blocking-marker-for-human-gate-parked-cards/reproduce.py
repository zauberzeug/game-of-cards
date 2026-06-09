"""Reproduce: `goc --board` omits the ⏳ pull-blocking marker for
human-gate-parked open cards.

A card with `human_gate: decision` is not pullable (`card_is_ready` is
False) yet the board renders it with no marker — visually identical to a
freely-pullable card — while an equally-un-pullable `waiting_impedes`
card IS marked. The board's `not_ready` predicate honors the
dependency and waiting axes but omits the `human_gate` axis that both
`card_is_ready` and `card_is_workable_for_scheduler` reject on.

Run: uv run python deck/<this-card>/reproduce.py
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


def _mk(title: str, *, gate: str = "none", waiting: str | None = None,
        until: str | None = None) -> Card:
    fm: dict = {
        "title": title,
        "status": "open",
        "contribution": "medium",
        "human_gate": gate,
        "advances": [],
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [ ] X\n",
    }
    if waiting is not None:
        fm["waiting_on"] = waiting
    if until is not None:
        fm["waiting_until"] = until
    return Card(title=title, path=Path("/tmp/" + title), frontmatter=fm,
                body="", dod_open=1, dod_done=0)


def _open_cell(board: str, title: str) -> str:
    for line in board.splitlines():
        if line.startswith(title):
            return line.split("|")[0].rstrip()
    raise AssertionError(f"{title!r} not found on board")


def main() -> int:
    gated = _mk("gated-decision", gate="decision")
    impeded = _mk("impeded", waiting="external", until="2099-01-01")
    free = _mk("free")
    cards = [gated, impeded, free]
    by_title = {c.title: c for c in cards}

    print("card_is_ready(gated)   =", card_is_ready(gated, by_title))
    print("card_is_ready(impeded) =", card_is_ready(impeded, by_title))
    print("card_is_ready(free)    =", card_is_ready(free, by_title))

    board = render_board(cards, max_rows=20, no_color=True, by_title=by_title)
    gated_cell = _open_cell(board, "gated-decision")
    impeded_cell = _open_cell(board, "impeded")
    free_cell = _open_cell(board, "free")

    print("--- board cells ---")
    print(repr(gated_cell))
    print(repr(impeded_cell))
    print(repr(free_cell))

    gated_marked = "⏳" in gated_cell
    impeded_marked = "⏳" in impeded_cell

    # The gated card is not pullable, so it should carry the marker — just
    # like the equally-un-pullable impeded card.
    assert not card_is_ready(gated, by_title), "precondition: gated card is not pullable"
    assert impeded_marked, "precondition: impeded card carries ⏳"
    assert gated_marked, (
        "DEFECT: human-gate-parked card has no ⏳ marker on the board — "
        "it reads as freely pullable when it is not"
    )
    print("\nPASS: human-gate-parked card is marked not-pullable on the board")
    return 0


if __name__ == "__main__":
    sys.exit(main())
