"""Score every `meta-fix`-tagged card against the row's own predicate.

The `meta-fix` row in the card-schema tag table reads:

    literal `meta-fix` / `family meta-fix` in title, `summary:`, or full
    body (no cutoff), OR an `advances`/`advanced_by` edge to a
    `meta-fix`-tagged card

Both clauses are properties a card acquires *incidentally*, and neither is
implied by being an umbrella. This script applies the row verbatim to the
live (non-terminal) tagged population and exits non-zero while any card
carrying the tag fails its own row — i.e. while `Skill(refine-deck)`'s
"Tags without firing predicates" sweep would mechanically strip it.

Run: uv run python .game-of-cards/deck/meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card/reproduce.py
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

LITERAL = "meta-fix"


def edges(card) -> list[str]:
    """The row's edge clause spans both bidirectional advance fields."""
    out: list[str] = []
    for field in ("advances", "advanced_by"):
        value = card.frontmatter.get(field) or []
        if isinstance(value, list):
            out.extend(str(x) for x in value)
    return out


def main() -> int:
    deck = engine.DECK_DIR
    cards = {c.title: c for c in engine.load_all_cards()}
    tagged = {t: c for t, c in cards.items() if LITERAL in (c.tags or [])}

    def fires(card):
        # `card.body` is the README with the frontmatter block already split
        # off, so a card cannot satisfy its own row merely by carrying the tag.
        if LITERAL in card.title:
            return "title"
        if LITERAL in (card.summary or ""):
            return "summary"
        if LITERAL in card.body:
            return "body"
        for neighbour in edges(card):
            other = cards.get(neighbour)
            if other and LITERAL in (other.tags or []):
                return f"edge -> {neighbour}"
        return None

    live = {t: c for t, c in tagged.items() if c.status in ("open", "active")}
    failing = sorted(t for t, c in live.items() if fires(c) is None)

    print(f"deck: {deck}")
    print(f"`{LITERAL}`-tagged cards: {len(tagged)} total, {len(live)} live (open/active)")
    print()
    if not failing:
        print("every live tagged card satisfies the row — nothing for the sweep to strip.")
        return 0

    print(f"{len(failing)} live card(s) carry `{LITERAL}` and fail the row's own predicate:")
    for title in failing:
        card = live[title]
        print(
            f"  - {title}\n"
            f"      created={str(card.created)[:10]}  gate={card.human_gate}  "
            f"edges={len(edges(card))}"
        )
    print()
    print(
        "FAIL: Skill(refine-deck) § 'Tags without firing predicates' strips a tag "
        "where its row plainly fails, so the sweep is pointed at the umbrella "
        "grouping the tag exists to provide."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
