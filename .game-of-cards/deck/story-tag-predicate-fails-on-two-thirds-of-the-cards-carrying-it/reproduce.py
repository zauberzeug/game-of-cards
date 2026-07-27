#!/usr/bin/env python3
"""Reproduce: the `story` tag predicate does not fire on most cards carrying it.

`Skill(card-schema)` § Canonical tags defines the tag as:

    | `story` | part of an epic-grouping (carries the epic-grouping tag) |

and states the general rule "A tag is load-bearing iff its predicate fires on
the title, H1, or first ~2500 chars of body ... when in doubt, drop it."

The predicate has two branches, both checked here:

  A. the card carries an epic-grouping *tag* shared with an epic, and
  B. the card is linked into an epic-grouping by an `advances` /
     `advanced_by` edge to an `epic`-tagged card.

Run from the repo root:

    uv run python .game-of-cards/deck/story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/reproduce.py

Exits 1 while any `story`-tagged card satisfies neither branch, 0 once the
predicate and the deck agree.
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

from goc import engine  # noqa: E402

# The nine tags goc ships. Anything outside this set that a repo registers in
# `.game-of-cards/canonical-tags.md` is a candidate epic-grouping tag.
SHIPPED_TAGS = {
    "bug",
    "epic",
    "story",
    "unverified",
    "documentation",
    "test",
    "api-contract",
    "infra",
    "meta-fix",
}


def main() -> int:
    cards = engine.load_all_cards()
    by_title = {c.title: c for c in cards}

    def tags_of(title: str) -> set[str]:
        card = by_title.get(title)
        return set(card.tags or []) if card else set()

    def edges_of(card) -> list[str]:
        """Relationship endpoints; `Card` exposes these only on `frontmatter`.

        Guarded with isinstance the way `Card.tags` is — a bare-string edge
        field would otherwise iterate character by character.
        """
        out: list[str] = []
        for field in ("advances", "advanced_by"):
            v = card.frontmatter.get(field)
            if isinstance(v, list):
                out.extend(x for x in v if isinstance(x, str))
        return out

    epics = [c for c in cards if "epic" in (c.tags or [])]
    stories = [c for c in cards if "story" in (c.tags or [])]

    # Branch A: is there any epic-grouping tag at all? An epic-grouping tag is a
    # non-shipped tag carried by an epic, which stories can then also carry.
    grouping_tags: set[str] = set()
    for ep in epics:
        grouping_tags |= set(ep.tags or []) - SHIPPED_TAGS

    orphans = []
    for c in stories:
        by_tag = bool((set(c.tags or []) - SHIPPED_TAGS) & grouping_tags)
        by_edge = any("epic" in tags_of(x) for x in edges_of(c))
        if not (by_tag or by_edge):
            orphans.append(c)

    print(f"epic-tagged cards:            {len(epics)}")
    print(f"epic-grouping tags available: {sorted(grouping_tags) or '(none)'}")
    print(f"story-tagged cards:           {len(stories)}")
    print(f"  predicate fires:            {len(stories) - len(orphans)}")
    print(f"  predicate does NOT fire:    {len(orphans)}")

    if not orphans:
        print("\nOK — every `story`-tagged card satisfies the documented predicate.")
        return 0

    pct = 100 * len(orphans) / len(stories)
    print(
        f"\nFAIL — {len(orphans)}/{len(stories)} ({pct:.0f}%) `story`-tagged cards "
        "satisfy neither branch of the predicate."
    )
    print("\nNon-terminal offenders (the ones a hygiene sweep would strip):")
    for c in sorted(orphans, key=lambda c: c.title):
        if c.status in ("open", "active"):
            blockers = [
                x for x in (c.frontmatter.get("advanced_by") or []) if isinstance(x, str)
            ]
            note = (
                f"  <- {len(blockers)} cards block its closure; the `epic` predicate fires"
                if len(blockers) > 1
                else ""
            )
            print(f"  {c.status:7s} {c.title}{note}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
