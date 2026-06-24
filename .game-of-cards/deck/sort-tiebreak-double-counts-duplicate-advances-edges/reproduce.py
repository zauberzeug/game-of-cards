"""Reproduce: `sort_default`'s near-term-flow tiebreak double-counts a
duplicate `advances` edge as if it were distinct downstream flow.

The tiebreak (engine.py:2637-2649) increments its counter once per list
element of `advances`, not once per distinct workable target. So a card
with `advances: [B, B]` scores the same on the tiebreak as a card with
`advances: [B, C]`, even though the first unblocks one downstream card
and the second unblocks two.

This script builds three clean-validating cards of equal value (all
`low` contribution, all `human_gate: none`):

  a-dup : advances: [bb-leaf, bb-leaf]   (one distinct target, listed twice)
  a-two : advances: [bb-leaf, cc-leaf]   (two distinct targets)

plus the two open leaves. With equal computed value, the tiebreak is the
only thing separating a-dup and a-two. Correct behavior: a-two (two
distinct downstream cards) sorts ahead of a-dup (one). Buggy behavior:
they tie on `live_direct == 2`, and `a-dup` — created first — wins the
final age tiebreak, landing ahead of the card that genuinely unblocks
more flow.

Exits 1 if a-dup sorts at or before a-two (defect present), 0 if a-two
sorts strictly ahead of a-dup (fix in place).
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


def card(title, *, advances, created):
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": "open",
            "contribution": "low",
            "human_gate": "none",
            "advances": list(advances),
            "advanced_by": [],
            "created": created,
        },
        body="",
        dod_open=1,
        dod_done=0,
    )


cards = [
    card("a-dup", advances=["bb-leaf", "bb-leaf"], created="2026-01-01"),
    card("a-two", advances=["bb-leaf", "cc-leaf"], created="2026-01-02"),
    card("bb-leaf", advances=[], created="2026-01-03"),
    card("cc-leaf", advances=[], created="2026-01-04"),
]

ordered = [c.title for c in engine.sort_default(cards)]
print("sort_default order:", ordered)

i_dup = ordered.index("a-dup")
i_two = ordered.index("a-two")
print(f"a-dup at index {i_dup}, a-two at index {i_two}")

if i_two < i_dup:
    print()
    print("a-two (two distinct downstream cards) sorts ahead of a-dup")
    print("(one distinct target listed twice). Tiebreak deduplicates. Fix in place.")
    sys.exit(0)
else:
    print()
    print("DEFECT CONFIRMED: a-dup ties or beats a-two on the near-term-flow")
    print("tiebreak — a duplicated `advances` edge is counted as distinct flow.")
    sys.exit(1)
