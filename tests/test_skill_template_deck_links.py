"""Regression guard: no shipped skill body links into a `.game-of-cards/deck/` path.

`goc/templates/skills/` is package data. `goc install --local-skills` copies it
into a consuming repo's `.claude/skills/`, and the Claude, Codex and OpenClaw
plugin payloads ship it verbatim. A markdown link whose target routes through
`.game-of-cards/deck/` therefore points at a card in *goc's own* deck — which no
consuming repo has ever contained, so the link is dead the moment it ships.

Card `card-schema-reference-links-to-a-deck-card-no-consumer-repo-has` is the
instance this guard was written from: `card-schema/reference.md` cited the
value-chain decision as

    [`advanced-by-…-mostly-loose`](../../../.game-of-cards/deck/advanced-by-…-mostly-loose/)

The line survived review because the five mirror trees all sit exactly three
directories below this repo's root, so the relative target resolved in a clone
of this repo. Only the source-of-truth template — four deep, so `../../../`
reaches `goc/` — was visibly broken, and only from a path nobody clicks. Hence
the sweep covers the mirrors too: a hit there is real breakage for consumers
even while it renders green here.

Per `static-source-guards-never-prove-they-can-catch-an-offender`, this suite
also feeds the historical offending line to the predicate and asserts it fires,
so a guard that silently stopped matching fails rather than passing quietly on a
clean tree.

The rule has no false-positive surface to trade against: goc's cards are goc's,
so there is no consuming repo in which such a link could be correct. Cite a
decision by its bare backticked title instead — the convention
`card-schema/reference.md` already uses eight lines below the offender.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Every tree that hands a skill body to a reader: the source of truth, the two
# in-repo dogfood mirrors, and the three plugin payloads.
SHIPPED_SKILL_TREES = (
    "goc/templates/skills",
    ".claude/skills",
    ".codex/skills",
    "claude-plugin/skills",
    "codex-plugin/skills",
    "openclaw-plugin/skills",
)

# A markdown link whose target routes through a `.game-of-cards/deck/` path.
# Anchored on the link syntax `](…)` rather than the bare path so that prose,
# shell snippets and `ls .game-of-cards/deck/` examples stay legal — the defect
# is promising a file, not naming the directory.
DECK_LINK_RE = re.compile(r"\]\(([^)\s]*\.game-of-cards/deck/[^)\s]*)\)")

# A URL is not a filesystem promise: an `https://…/.game-of-cards/deck/…` target
# resolves for every reader or none, independent of which repo the skill was
# installed into, so it is outside this guard's rule.
_URL_SCHEME_RE = re.compile(r"\A[a-z][a-z0-9+.-]*:", re.IGNORECASE)

# The line that shipped in `card-schema/reference.md` until this card closed.
HISTORICAL_OFFENDER = (
    "[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`]"
    "(../../../.game-of-cards/deck/"
    "advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)"
)


def deck_links(text: str) -> list[str]:
    """Return every markdown link target in `text` that points into a deck."""
    return [t for t in DECK_LINK_RE.findall(text) if not _URL_SCHEME_RE.match(t)]


def sweep() -> list[tuple[str, int, str]]:
    """Return (repo-relative path, line number, target) for every deck link."""
    hits: list[tuple[str, int, str]] = []
    for tree in SHIPPED_SKILL_TREES:
        base = ROOT / tree
        if not base.is_dir():
            continue
        for md in sorted(base.rglob("*.md")):
            for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
                for target in deck_links(line):
                    hits.append((str(md.relative_to(ROOT)), lineno, target))
    return hits


class SkillTemplateDeckLinkSensitivityTest(unittest.TestCase):
    """The guard can catch an offender — not just report a clean tree."""

    def test_predicate_flags_the_historical_offender(self) -> None:
        self.assertEqual(
            deck_links(HISTORICAL_OFFENDER),
            [
                "../../../.game-of-cards/deck/"
                "advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/"
            ],
            "the guard must flag the exact line this repo shipped to consumers; "
            "if this fails the deck-link rule is unenforced again",
        )

    def test_predicate_flags_every_depth_and_shape(self) -> None:
        """Recall does not depend on how the author spelled the path."""
        for label, line in (
            ("installed frame", "see [x](../../../.game-of-cards/deck/some-card/)"),
            ("template frame", "see [x](../../../../.game-of-cards/deck/some-card/)"),
            ("repo-root relative", "see [x](.game-of-cards/deck/some-card/README.md)"),
            ("absolute-from-root", "see [x](/.game-of-cards/deck/some-card/)"),
            ("deep file target", "see [x](../../.game-of-cards/deck/c/reproduce.py)"),
        ):
            with self.subTest(case=label):
                self.assertTrue(deck_links(line), f"{label}: {line!r} should be flagged")

    def test_predicate_leaves_non_link_deck_mentions_alone(self) -> None:
        """Precision: naming the directory is legal; promising a file is not.

        Several shipped skills legitimately print `.game-of-cards/deck/` in
        preflight checks and command examples. Flagging those would make the
        guard unusable, so it is anchored on markdown link syntax.
        """
        for label, line in (
            ("preflight probe", 'ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS"'),
            ("verb table", "| `goc new <t>` | Scaffold under `.game-of-cards/deck/<t>/`. |"),
            ("sibling card link", "see [other-card](../other-card/) for the rationale"),
            ("http link", "see [docs](https://example.com/.game-of-cards/deck/x)"),
        ):
            with self.subTest(case=label):
                self.assertEqual(deck_links(line), [], f"{label}: {line!r} must stay clean")

    def test_the_trees_are_actually_being_swept(self) -> None:
        """Guard the guard: a clean result must come from real skill bodies.

        Without this, renaming a skill tree would turn the sweep below into a
        vacuous pass over an empty glob.
        """
        for tree in SHIPPED_SKILL_TREES:
            base = ROOT / tree
            with self.subTest(tree=tree):
                self.assertTrue(base.is_dir(), f"{tree} is missing — sweep would skip it")
                self.assertGreater(
                    len(list(base.rglob("*.md"))), 10, f"{tree} holds too few skill bodies"
                )


class SkillTemplateDeckLinkTest(unittest.TestCase):
    def test_no_shipped_skill_body_links_into_a_deck(self) -> None:
        hits = sweep()
        self.assertEqual(
            hits,
            [],
            "shipped skill bodies must not link into `.game-of-cards/deck/` — a "
            "consuming repo has none of goc's cards, so the link is dead on "
            f"install. Cite the card by bare backticked title instead. Found: {hits}",
        )


if __name__ == "__main__":
    unittest.main()
