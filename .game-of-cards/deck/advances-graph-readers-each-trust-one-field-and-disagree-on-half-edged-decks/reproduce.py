"""Reproduce: consumers of the advances relation each read one half of an edge.

Two open cards, `up` and `down`, joined by one edge up → down. Three
fixtures record it differently:

  advances only     up.advances = [down], down.advanced_by = []
  advanced_by only  up.advances = [],     down.advanced_by = [up]
  both halves       control: the shape a half-edge-free deck carries

Six consumers are asked whether they see the edge:

  value walk     compute_values: does up's priority path run through down?
  cycle guard    _would_create_advance_cycle: would down → up close a cycle?
  --advances     filter_cards(advances="down"): is up listed?
  readiness      dependency_blockers(down): is up an open prereq?
  closure check  advanced-by-closed on down: does it fail on open up?
  --advanced-by  filter_cards(advanced_by="up"): is down listed?

Exit codes follow the deck's reproducer contract:
  0 — the defect no longer fires (every consumer gives one answer per fixture)
  1 — the defect fires (consumers split on some fixture)
  2 — the harness or the control is broken (a consumer misses the full edge)
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir():
            return p
        p = p.parent
    raise RuntimeError(".game-of-cards/ not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402


def _deck(*, advances: bool, advanced_by: bool) -> list[engine.Card]:
    base = {"status": "open", "human_gate": "none", "advances": [], "advanced_by": []}
    up = {**base, "title": "up", "contribution": "low", "advances": ["down"] if advances else []}
    down = {**base, "title": "down", "contribution": "high", "advanced_by": ["up"] if advanced_by else []}
    return [
        engine.Card(title=fm["title"], path=None, frontmatter=fm, body="", dod_open=0, dod_done=0)
        for fm in (up, down)
    ]


def _probes(cards: list[engine.Card]) -> dict[str, bool]:
    by_title = {c.title: c for c in cards}
    down = by_title["down"]
    _, path = engine.compute_values(cards)["up"]
    closure_ok, _ = engine._run_derived_check({"name": "advanced-by-closed"}, down, cards, "2026-10-29")
    return {
        "value walk": path[:1] == ["down"],
        "cycle guard": engine._would_create_advance_cycle(cards, "up", "down"),
        "--advances": [c.title for c in engine.filter_cards(cards, status=None, advances="down")] == ["up"],
        "readiness": engine.dependency_blockers(down, by_title) == ["up"],
        "closure check": not closure_ok,
        "--advanced-by": [c.title for c in engine.filter_cards(cards, status=None, advanced_by="up")] == ["down"],
    }


def main() -> int:
    fixtures = [
        ("advances only", {"advances": True, "advanced_by": False}),
        ("advanced_by only", {"advances": False, "advanced_by": True}),
        ("both halves", {"advances": True, "advanced_by": True}),
    ]
    split: list[str] = []
    for name, fields in fixtures:
        seen = _probes(_deck(**fields))
        sees = [k for k, v in seen.items() if v]
        misses = [k for k, v in seen.items() if not v]
        print(f"{name}:")
        print(f"  sees the edge:   {', '.join(sees) or '-'}")
        print(f"  misses the edge: {', '.join(misses) or '-'}")
        if name == "both halves" and misses:
            print("\nHARNESS: a consumer misses an edge both halves record")
            return 2
        if sees and misses:
            split.append(name)
    print()
    if split:
        print(f"DEFECT: consumers disagree about one edge on: {', '.join(split)}")
        return 1
    print("OK: every consumer gives one answer per fixture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
