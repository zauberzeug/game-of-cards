#!/usr/bin/env python3
"""Demonstrate that the deck skill's board legend contradicts the engine.

The legend at goc/templates/skills/deck/SKILL.md says a board `⏳` means
"not ready to pull" and "No ⏳ ⇒ pullable". But the engine paints `⏳` on a
dependency-blocked card (advisory only) while `card_is_ready` still reports
it as pullable. This script builds such a card pair and prints both signals.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from goc.engine import Card, card_is_ready, dependency_blocked  # noqa: E402


def make_card(title, **fm):
    base = {
        "title": title,
        "status": "open",
        "human_gate": "none",
        "contribution": "medium",
        "advances": [],
        "advanced_by": [],
        "tags": [],
        "waiting_on": None,
        "waiting_until": None,
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


# A still-open prerequisite ...
prereq = make_card("prereq-open")
# ... and a card that depends on it (advanced_by the open prereq).
child = make_card("dependent-card", advanced_by=["prereq-open"])
by_title = {"prereq-open": prereq, "dependent-card": child}

board_flagged = child.status == "open" and dependency_blocked(child, by_title)
pullable = card_is_ready(child, by_title)

print(f"board paints ⏳ (dependency_blocked): {board_flagged}")
print(f"card_is_ready (actually pullable):    {pullable}")
print()

legend_says_unpullable = board_flagged  # legend: "⏳ ⇒ not ready to pull"
if legend_says_unpullable and pullable:
    print("DEFECT CONFIRMED: legend says ⏳ ⇒ not-pullable, but the card IS pullable.")
    sys.exit(0)
else:
    print("No contradiction reproduced — legend and engine agree.")
    sys.exit(1)
