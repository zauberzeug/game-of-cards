#!/usr/bin/env python3
"""Demonstrate that the `--ready` help text overstates its filter.

The `--ready` argparse help claims it excludes cards with "no non-terminal
advanced_by prereqs", but `card_is_ready` (the predicate `--ready` calls)
ignores `advanced_by` entirely. This script proves the drift two ways:

1. The actual `--ready` help string still contains the stale
   "advanced_by prereqs" claim.
2. A card the help would exclude (open, gate none, non-terminal
   advanced_by prereq) is in fact reported ready by `card_is_ready`.

Exits 0 when the drift is GONE (help no longer claims advanced_by filtering),
non-zero while the defect is live.
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


def _ready_help() -> str:
    parser = engine._build_parser()
    for action in parser._actions:
        if "--ready" in getattr(action, "option_strings", []):
            return action.help or ""
    raise RuntimeError("--ready action not found in parser")


def _card(title, frontmatter):
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter={"title": title, **frontmatter},
        body="",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    # --- Part 1: does the actual help string still make the stale claim? ---
    help_text = _ready_help()
    stale_claim = "advanced_by prereq" in help_text
    print(f"--ready help string: {help_text!r}")
    print(f"  mentions 'advanced_by prereq(s)': {stale_claim}")

    # --- Part 2: does card_is_ready actually ignore advanced_by? ---
    epic = _card("epic-child-prereq", {
        "status": "open", "human_gate": "none", "contribution": "medium",
        "advanced_by": [], "advances": [],
    })
    dependent = _card("depends-on-open-prereq", {
        "status": "open", "human_gate": "none", "contribution": "medium",
        # non-terminal (open) advanced_by prereq -> help claims this is filtered out
        "advanced_by": ["epic-child-prereq"], "advances": [],
    })
    by_title = {c.title: c for c in (epic, dependent)}
    ready = engine.card_is_ready(dependent, by_title)
    print(f"card_is_ready(dependent with open advanced_by prereq) = {ready}")
    print("  (help text implies this should be False / filtered out)")

    # The defect is live iff the help still claims advanced_by filtering
    # while card_is_ready returns True for such a card.
    defect_live = stale_claim and ready
    if defect_live:
        print("\nFAIL: --ready help promises advanced_by-prereq filtering that "
              "card_is_ready does not perform (doc/code drift).")
        return 1
    print("\nPASS: --ready help text matches card_is_ready behaviour.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
