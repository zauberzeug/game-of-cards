"""Show the deck-tag guard failing on main, and why both of its exits are open.

`test_canonical_tag_rows.test_live_cards_satisfy_every_state_row` scores every
live card that carries a `state` tag against that row's predicate. One card
fails. This script reproduces the scoring and prints the evidence for each of
the two readings the guard tells a human to choose between.

Run: uv run python .game-of-cards/deck/regression-suite-red-on-main-over-the-unverified-tag-row/reproduce.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_canonical_tag_rows import STATE_SCORERS, live_cards  # noqa: E402

offenders = [
    (card, tag)
    for tag, scorer in sorted(STATE_SCORERS.items())
    for card in live_cards()
    if tag in (card.tags or []) and not scorer(card)
]

print(f"live cards scored: {len(live_cards())}")
print(f"state rows scored: {sorted(STATE_SCORERS)}")
print(f"offenders: {[(c.title, t) for c, t in offenders]}")
print()

for card, tag in offenders:
    script = Path(card.path) / "reproduce.py"
    size = script.stat().st_size if script.exists() else 0
    print(f"card    : {card.title}")
    print(f"tags    : {card.tags}")
    print(f"row     : `{tag}` scores as 'no working reproduce.py'")
    print(f"evidence: reproduce.py exists={script.exists()} size={size}B -> row FAILS")
    dod = str(card.frontmatter.get("definition_of_done", ""))
    for line in dod.splitlines():
        if "unverified" in line:
            print(f"card DoD: {line.strip()}")
    print()

print(
    "Both exits the guard names are open:\n"
    "  (a) the card is mistagged — it has a working reproduce.py, so drop the tag;\n"
    "  (b) the row is too narrow — the card's reproduce.py proves the code shape\n"
    "      but not the external premise the DoD says clears the tag.\n"
    "The guard forbids widening the row to make this pass, so a human picks."
)

if offenders:
    print("\nFAIL: the regression suite is red on main.")
    sys.exit(1)
print("\nPASS: every live card satisfies its state rows.")
