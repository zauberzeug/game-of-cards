#!/usr/bin/env python3
"""Reproduce: `goc -vv` (render_table at verbose>=2) crashes on a card
whose `definition_of_done` frontmatter key is present but empty (None).

Exits 0 when the defect is FIXED (render survives), 1 while it is live.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from goc import engine  # noqa: E402


def make_card():
    return engine.Card(
        title="empty-dod-card",
        path=None,
        frontmatter={
            "title": "empty-dod-card",
            "status": "open",
            "contribution": "medium",
            "human_gate": "none",
            "definition_of_done": None,  # empty `definition_of_done:` line
        },
        body="",
        dod_open=0,
        dod_done=0,
    )


def main():
    card = make_card()

    # Sanity: the card loads and renders fine at lower verbosity.
    for v in (0, 1):
        engine.render_table([card], verbose=v, no_color=True)
        print(f"v{v}: renders OK")

    try:
        engine.render_table([card], verbose=2, no_color=True)
    except AttributeError as e:
        print(f"v2: AttributeError {e}")
        print("DEFECT PRESENT: -vv render crashes on empty definition_of_done")
        return 1

    print("v2: renders OK")
    print("DEFECT FIXED: -vv render survives empty definition_of_done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
