"""Reproduce: compute_values iterates a non-list `advances` value
character-by-character, emitting phantom dangling-edge warnings and
inflating the card's priority value.

Run: uv run python .game-of-cards/deck/compute-values-iterates-non-list-advances-character-by-character/reproduce.py
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

from goc import engine


def mk(title, contribution, advances):
    fm = {
        "title": title,
        "status": "open",
        "contribution": contribution,
        "advances": advances,
        "advanced_by": [],
    }
    return engine.Card(
        title=title, path=None, frontmatter=fm, body="", dod_open=0, dod_done=0
    )


# A single 'low' card whose `advances` was hand-edited to a bare string
# (the YAML scalar form `advances: bcard` instead of a list). No card named
# 'b'/'c'/'r'/'d' exists.
card = mk("a", "low", "bcard")
cards = [card]

print("=== Running compute_values on a deck with `advances: bcard` (a bare string) ===")
print("(stderr above shows the phantom per-character warnings)\n")

values = engine.compute_values(cards)
value, path = values["a"]

own = engine.CONTRIBUTION_RANK.get("low", 0.0)
print(f"contribution 'low' bare rank          : {own}")
print(f"compute_values value for card 'a'      : {value}")
print(f"value path                             : {path}")
print()

expected = own  # leaf card with no real descendants -> own rank, ['self']
if value != expected:
    print(f"DEFECT CONFIRMED: value is {value}, expected {expected} (a leaf with no")
    print("real advances edges). The character 'a' in the bare string 'bcard'")
    print("matched the card's own title, tripping the in_progress cycle branch")
    print("(own + gamma*own). The remaining chars 'b','c','r','d' were emitted as")
    print("phantom dangling-edge warnings above.")
    sys.exit(1)
else:
    print("No defect: value equals the leaf's own rank (bug is fixed).")
    sys.exit(0)
