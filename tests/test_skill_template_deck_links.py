"""Regression guard: no shipped template cites a card in goc's own deck.

Two predicates enforce one rule. `deck_links` catches a markdown link whose
target routes through `.game-of-cards/deck/`; `card_paths` catches a `deck/`
path that names a concrete card directory and promises a file inside it, in
any syntax. Both sweep the six skill trees and the four project-state template
trees.

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

`installed-files-point-readers-at-a-deck-folder-install-never-creates` is why
the second predicate exists. That card found two survivors of the link-only
rule — `game_of_cards/README.md` citing
``deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md`` (renamed
since, and under the pre-move deck root) and `refine-deck/reference.md` citing
``deck/auto-validate-card-titles-summaries-and-dods/log.md`` (no card of that
name ever existed). The second sat inside `goc/templates/skills`, a tree this
file already swept: it escaped on syntax alone, being inline code rather than a
link. Guards written from one instance inherit that instance's shape, so widen
here rather than adding a twelfth guard file.

`card_paths` rests on two discriminators, both checked below rather than
assumed. A card slug is always hyphenated (all 764 dirs in goc's own deck are,
and `test_card_slugs_are_hyphenated` re-derives it from the tree), which keeps
running prose like `deck/methodology/workflow` out; and the match must promise
a *file* inside the directory, which keeps the `deck/<title>/` placeholder —
19 sites per skill tree — legal. The residual gap is a bare inline-code
directory reference with no filename; that shape has never shipped, and
`deck_links` already covers it in link form.

The rule has no false-positive surface to trade against: goc's cards are goc's,
so there is no consuming repo in which such a citation could be correct. Cite a
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

# `goc install` copies this tree into a consuming repo's `.game-of-cards/`,
# so a card citation here ships exactly as far as one in a skill body. Held
# separately from the skill trees only because its liveness floor differs.
PROJECT_STATE_TREES = (
    "goc/templates/game_of_cards",
    "claude-plugin/goc/templates/game_of_cards",
    "codex-plugin/goc/templates/game_of_cards",
    "openclaw-plugin/goc/templates/game_of_cards",
)

SWEPT_TREES = SHIPPED_SKILL_TREES + PROJECT_STATE_TREES

# A markdown link whose target routes through a `.game-of-cards/deck/` path.
# Anchored on the link syntax `](…)` rather than the bare path so that prose,
# shell snippets and `ls .game-of-cards/deck/` examples stay legal — the defect
# is promising a file, not naming the directory.
DECK_LINK_RE = re.compile(r"\]\(([^)\s]*\.game-of-cards/deck/[^)\s]*)\)")

# A URL is not a filesystem promise: an `https://…/.game-of-cards/deck/…` target
# resolves for every reader or none, independent of which repo the skill was
# installed into, so it is outside this guard's rule.
_URL_SCHEME_RE = re.compile(r"\A[a-z][a-z0-9+.-]*:", re.IGNORECASE)

# A `deck/` path naming a concrete card directory AND a file inside it.
# `([a-z0-9]+(?:-[a-z0-9]+)+)` requires the hyphen every real slug carries;
# the trailing group requires a filename, so `deck/<title>/README.md` — whose
# slug is the literal placeholder — cannot match on either count.
CARD_PATH_RE = re.compile(
    r"(?<![\w./-])(?:\.game-of-cards/)?deck/"
    r"([a-z0-9]+(?:-[a-z0-9]+)+)/"
    r"([\w.-]+\.[a-z]{2,4})\b"
)

# The line that shipped in `card-schema/reference.md` until this card closed.
HISTORICAL_OFFENDER = (
    "[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`]"
    "(../../../.game-of-cards/deck/"
    "advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)"
)


# The two lines that survived the link-only rule, verbatim as they shipped.
HISTORICAL_CARD_PATH_OFFENDERS = (
    "  audit catalogue (`deck/goc-package-pyproject-and-pypi-release/"
    "audit_catalogue.md`).",
    "tracked in `deck/auto-validate-card-titles-summaries-and-dods/log.md`.",
)


def card_paths(text: str) -> list[str]:
    """Return every concrete `deck/<slug>/<file>` citation in `text`."""
    return [f"deck/{slug}/{name}" for slug, name in CARD_PATH_RE.findall(text)]


def deck_links(text: str) -> list[str]:
    """Return every markdown link target in `text` that points into a deck."""
    return [t for t in DECK_LINK_RE.findall(text) if not _URL_SCHEME_RE.match(t)]


def sweep() -> list[tuple[str, int, str]]:
    """Return (repo-relative path, line number, target) for every citation."""
    hits: list[tuple[str, int, str]] = []
    for tree in SWEPT_TREES:
        base = ROOT / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for target in deck_links(line) + card_paths(line):
                    hits.append((str(path.relative_to(ROOT)), lineno, target))
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

    def test_card_path_predicate_flags_both_historical_offenders(self) -> None:
        """Each line that survived the link-only rule must now fire."""
        for line, expected in zip(
            HISTORICAL_CARD_PATH_OFFENDERS,
            (
                "deck/goc-package-pyproject-and-pypi-release/audit_catalogue.md",
                "deck/auto-validate-card-titles-summaries-and-dods/log.md",
            ),
        ):
            with self.subTest(line=line[:48]):
                self.assertEqual(
                    card_paths(line),
                    [expected],
                    "the guard must flag the exact line this repo shipped; if "
                    "this fails the concrete-card-path rule is unenforced again",
                )

    def test_card_path_predicate_flags_every_deck_root_and_file_kind(self) -> None:
        """Recall does not depend on which deck root or file the author named."""
        for label, line in (
            ("legacy root", "see `deck/some-real-card/README.md` for detail"),
            ("canonical root", "see `.game-of-cards/deck/some-real-card/log.md`"),
            ("reproduce script", "run .game-of-cards/deck/some-real-card/reproduce.py"),
            ("sibling artifact", "the grid in deck/some-real-card/options.html"),
            ("inside a link", "see [x](.game-of-cards/deck/some-real-card/README.md)"),
        ):
            with self.subTest(case=label):
                self.assertTrue(card_paths(line), f"{label}: {line!r} should be flagged")

    def test_card_path_predicate_leaves_the_placeholder_convention_alone(self) -> None:
        """Precision: `deck/<title>/` is house shorthand at 19 sites per tree.

        Naming the directory, or the placeholder card inside it, is how the
        shipped skills describe card layout. Flagging those would make the
        guard unusable — the defect is naming a card that only goc has.
        """
        for label, line in (
            ("placeholder readme", "Rewrite `deck/<title>/README.md` body to document"),
            ("placeholder script", "Run via `uv run python deck/<title>/reproduce.py`"),
            ("placeholder log", "section to `deck/<title>/log.md`, leave status"),
            ("short placeholder", "| Scaffold under `.game-of-cards/deck/<t>/`. |"),
            ("prose slash phrase", "references the deck/methodology/workflow, or at"),
            ("bare directory", 'ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS"'),
            ("sibling card link", "see [other-card](../other-card/) for the rationale"),
        ):
            with self.subTest(case=label):
                self.assertEqual(card_paths(line), [], f"{label}: {line!r} must stay clean")

    def test_card_slugs_are_hyphenated(self) -> None:
        """Re-derive the discriminator `CARD_PATH_RE` rests on from the deck.

        The predicate tells a card slug apart from a prose phrase like
        `deck/methodology/workflow` by requiring a hyphen. That holds for every
        card goc has ever filed; if a hyphenless slug ever lands, this fails
        loudly instead of the predicate silently going blind to it.
        """
        deck = ROOT / ".game-of-cards" / "deck"
        slugs = [d.name for d in deck.iterdir() if d.is_dir()]
        self.assertGreater(len(slugs), 100, "deck did not load — assertion would be vacuous")
        self.assertEqual(
            [s for s in slugs if "-" not in s],
            [],
            "a hyphenless card slug makes CARD_PATH_RE blind to citations of it",
        )

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
        for tree in PROJECT_STATE_TREES:
            base = ROOT / tree
            with self.subTest(tree=tree):
                self.assertTrue(base.is_dir(), f"{tree} is missing — sweep would skip it")
                # README + 5 content stubs + 6 workflow-hook stubs + config.yaml.
                self.assertGreater(
                    len(list(base.rglob("*"))), 10, f"{tree} holds too few shipped files"
                )


class SkillTemplateDeckLinkTest(unittest.TestCase):
    def test_no_shipped_skill_body_links_into_a_deck(self) -> None:
        hits = sweep()
        self.assertEqual(
            hits,
            [],
            "shipped templates must not cite a card in `.game-of-cards/deck/` — a "
            "consuming repo has none of goc's cards, so the citation is dead on "
            f"install. Cite the card by bare backticked title instead. Found: {hits}",
        )


if __name__ == "__main__":
    unittest.main()
