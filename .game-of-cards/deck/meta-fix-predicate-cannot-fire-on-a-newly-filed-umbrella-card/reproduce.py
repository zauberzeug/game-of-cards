"""Prove no live `meta-fix`-tagged card is exposed to a mechanical tag strip.

As filed, the `meta-fix` row was a scorable literal-plus-edge test, and
`Skill(refine-deck)` § "Tags without firing predicates" told the operator to
strip a tag whose row plainly fails. Applied to the live population, that
pointed the sweep at the umbrellas the tag exists to group: an umbrella is
named by shape rather than by writing `meta-fix` into its prose, and its family
roster is wired later or never, so it satisfied neither clause at filing time.

The resolution does not widen the row a third time. `meta-fix` is now a
`judgment` row — its satisfier is the card's scope, which an umbrella meets by
construction — and the sweep's action on any non-firing row is *report*, never
*strip*. Neither half is scorable card state, so this script checks the two
properties that make the failure impossible instead:

  1. `meta-fix` is classified `judgment` in the canonical-tags table, so no
     sweep scores it and finds it wanting.
  2. No surface in `Skill(refine-deck)` instructs a mechanical strip on a row
     that does not fire.

It still MEASURES the original predicate and prints the cards it cannot fire on
— that population is the evidence, and it is expected to stay non-empty. What
changed is that those cards now cost a line of output rather than their tag.

Run: uv run python .game-of-cards/deck/meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card/reproduce.py
"""

import re
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
SKILL = ROOT / "goc" / "templates" / "skills" / "card-schema" / "SKILL.md"
REFINE = [
    ROOT / "goc" / "templates" / "skills" / "refine-deck" / "SKILL.md",
    ROOT / "goc" / "templates" / "skills" / "refine-deck" / "reference.md",
]

# Wording that turned a non-firing predicate into a frontmatter edit.
STRIP_INSTRUCTIONS = [
    "strip only where a row plainly fails",
    "mistagged, strip",
    "→ stripped tag",
]


def edges(card) -> list[str]:
    """The original row's edge clause spanned both bidirectional fields."""
    out: list[str] = []
    for field in ("advances", "advanced_by"):
        value = card.frontmatter.get(field) or []
        if isinstance(value, list):
            out.extend(str(x) for x in value)
    return out


def check_class() -> str | None:
    """The `check` column of the `meta-fix` row, or None if unparseable."""
    text = SKILL.read_text()
    for line in text.splitlines():
        match = re.match(r"^\|\s*`" + LITERAL + r"`\s*\|(.*)\|([^|]*)\|\s*$", line)
        if match:
            return match.group(2).strip()
    return None


def main() -> int:
    cards = {c.title: c for c in engine.load_all_cards()}
    tagged = {t: c for t, c in cards.items() if LITERAL in (c.tags or [])}
    live = {t: c for t, c in tagged.items() if c.status in ("open", "active")}

    def fires_original(card):
        # `card.body` is the README with the frontmatter block already split
        # off, so a card cannot satisfy the row merely by carrying the tag —
        # the tautology that let the 2026-07-08 closure check pass 45 of 45.
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

    print(f"deck: {engine.DECK_DIR}")
    print(f"`{LITERAL}`-tagged cards: {len(tagged)} total, {len(live)} live (open/active)")
    print()

    failures = []
    if not live:
        failures.append(
            "no live tagged cards loaded — the measurement below would be vacuous"
        )

    unreachable = sorted(t for t, c in live.items() if fires_original(c) is None)
    print(
        f"{len(unreachable)} live card(s) the ORIGINAL literal-plus-edge predicate "
        "cannot fire on:"
    )
    for title in unreachable:
        card = live[title]
        print(
            f"  - {title}\n"
            f"      created={str(card.created)[:10]}  gate={card.human_gate}  "
            f"edges={len(edges(card))}"
        )
    print("  (expected non-empty: umbrellas acquire a literal or a roster "
          "incidentally, and one of these is a deliberately edgeless grouping)")
    print()

    row_check = check_class()
    print(f"canonical-tags table: `{LITERAL}` row declares check={row_check!r}")
    if row_check != "judgment":
        failures.append(
            f"the `{LITERAL}` row is check={row_check!r}, so a sweep scores it — and "
            f"{len(unreachable)} live card(s) above cannot satisfy any text-or-edge "
            "predicate. Scoring this row aims the sweep at the umbrella grouping."
        )

    for path in REFINE:
        text = path.read_text()
        for phrase in STRIP_INSTRUCTIONS:
            if phrase in text:
                failures.append(
                    f"{path.relative_to(ROOT)} instructs {phrase!r} — a non-firing "
                    "predicate deletes curated grouping instead of printing a line"
                )
    print(f"refine-deck surfaces checked for a mechanical strip: {len(REFINE)}")
    print()

    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1

    print(
        "`meta-fix` is a judgment row and the sweep reports rather than strips, so "
        "the cards above keep their tag."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
