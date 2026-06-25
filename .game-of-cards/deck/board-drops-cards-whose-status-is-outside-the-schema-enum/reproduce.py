"""Proof that `goc --board` silently drops a card whose status is not in
the schema's status enum, while the default `goc` table keeps it.

Run from a clean checkout:

    uv run python .game-of-cards/deck/board-drops-cards-whose-status-is-outside-the-schema-enum/reproduce.py

Exits non-zero while the defect is present (board drops the off-enum
card); exits zero once the fix lands (board surfaces it).
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

import goc.engine as e  # noqa: E402


def _mk(title: str, status: str) -> "e.Card":
    fm = {
        "title": title,
        "status": status,
        "contribution": "medium",
        "human_gate": "none",
        "created": "2026-01-01",
    }
    return e.Card(title=title, path=None, frontmatter=fm, body="", dod_open=0, dod_done=0)


def main() -> int:
    cards = [_mk("alpha-open", "open"), _mk("legacy-blocked", "blocked")]

    # Simulate an enum migration that dropped `blocked` from schema.yaml.
    class _Schema:
        status_values = ["open", "active", "done", "disproved", "superseded"]

    orig = e.load_schema
    e.load_schema = lambda: _Schema()
    try:
        board = e.render_board(cards, max_rows=20, no_color=True)
        table = e.render_table(cards, verbose=0, no_color=True)
    finally:
        e.load_schema = orig

    in_board = "legacy-blocked" in board
    in_table = "legacy-blocked" in table

    print("schema enum:", _Schema.status_values)
    print("legacy-blocked in BOARD?", in_board)
    print("legacy-blocked in TABLE?", in_table)
    print()
    print("--- BOARD ---")
    print(board)

    if in_table and not in_board:
        print()
        print("DEFECT: render_table shows the off-enum card but render_board drops it.")
        return 1
    if in_board:
        print()
        print("OK: render_board surfaces the off-enum card.")
        return 0
    print()
    print("UNEXPECTED: render_table also dropped the card.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
