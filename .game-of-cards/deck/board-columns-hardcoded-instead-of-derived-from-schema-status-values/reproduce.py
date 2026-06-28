#!/usr/bin/env python3
"""Demonstrate that the board must derive its columns from the schema's
status enum, not a hardcoded literal.

When `schema.status_values` declares a status the renderer's old literal
list did not name (a consuming repo's custom workflow status, or a status
introduced by an enum migration), the hardcoded board silently drops every
card in that status; the schema-derived board renders it.

Run: uv run python .game-of-cards/deck/board-columns-hardcoded-instead-of-derived-from-schema-status-values/reproduce.py
"""
from dataclasses import replace
from pathlib import Path

import goc.engine as e


def mk(title, status):
    return e.Card(
        title=title,
        path=Path("/tmp") / title,
        frontmatter={
            "title": title,
            "status": status,
            "contribution": "medium",
            "human_gate": "none",
        },
        body="",
        dod_open=0,
        dod_done=0,
    )


# Simulate a consuming repo whose schema.yaml declares an extra workflow
# status `review` (the support-custom-card-workflows-and-statuses feature).
_real_load_schema = e.load_schema
_custom = replace(_real_load_schema(), status_values=[
    "open", "active", "review", "blocked", "done", "disproved", "superseded"
])


def main():
    e.load_schema = lambda: _custom  # patch the single source of truth
    try:
        print("schema.status_values =", e.load_schema().status_values)
        cards = [mk("alpha", "open"), mk("beta", "review"), mk("gamma", "active")]
        board = e.render_board(cards, max_rows=20, no_color=True)
        print(board)
        print()
        present = "beta" in board
        print(f"beta (status=review) present in board output: {present}")
        print(
            "EXPECT after fix: True (column derived from schema.status_values). "
            f"BEFORE fix (hardcoded literal): False — silently dropped. Observed: {present}"
        )
    finally:
        e.load_schema = _real_load_schema


if __name__ == "__main__":
    main()
