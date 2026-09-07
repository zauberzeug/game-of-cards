"""Regression guard: card frontmatter must be readable by a strict YAML parser.

`goc` reads cards through `goc/_vendor/yaml_lite.py`, scoped on purpose as a
superset of `emit_frontmatter`'s output, and `engine.validate_card` checks
parsed field *values* rather than the block's YAML legality. Two hand-authored
cards therefore sat in this repo's deck reporting `OK` under `goc validate`
while PyYAML refused both — one for an unquoted `: ` inside a plain scalar, one
for a plain scalar opening with a backtick, which YAML reserves.

`scripts/check_card_frontmatter_yaml.py` closes the gap; this suite is where it
is enforced, so a card whose frontmatter strict YAML rejects turns the build red
on the commit that files it.

It also carries the requirement inherited from
`static-source-guards-never-prove-they-can-catch-an-offender`: a static guard
must demonstrate it can catch an offender, not merely report a clean tree.
`HISTORICAL_OFFENDERS` holds the two `summary` lines exactly as they sat on
disk, so a guard that silently stopped matching fails here rather than passing
quietly on a deck that happens to be clean.

PyYAML is deliberately absent from this project's dependencies
(`drop-third-party-runtime-dependencies-from-goc`), so the guard reproduces a
strict-YAML verdict statically. The calibration that licenses that substitution
lives in the card's `reproduce.py`, which runs the detector and PyYAML side by
side across the whole deck: zero false positives, zero false negatives.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_guard():
    """Import scripts/check_card_frontmatter_yaml.py without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_goc_card_frontmatter_yaml_guard",
        ROOT / "scripts" / "check_card_frontmatter_yaml.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load_guard()

# The two `summary` lines this repo's deck actually carried, byte-for-byte, each
# paired with the strict-YAML error it produced.
HISTORICAL_OFFENDERS = [
    (
        "nested ': ' (mapping values are not allowed here)",
        "summary: When `workflow.closure_on_integration: true`, `goc done` refuses to "
        "close unless HEAD is reachable from origin/main, but `goc status <title> "
        "disproved` and `goc status <title> superseded --by <other>` skip the check "
        "entirely.",
    ),
    (
        "leading backtick (cannot start any token)",
        "summary: `goc repair-edges --help` and the verb's docstrings claim the verb "
        "only handles `advances/advanced_by` half-edges, but the implementation walks "
        "every entry in `INVERSE_REL`.",
    ),
]

# Every remaining YAML indicator that is illegal or meaning-changing at position
# 0 of a plain scalar. Enumerated so dropping one from the guard's tuple fails
# here instead of going quiet.
LEADING_INDICATOR_CASES = [
    "summary: @reserved-in-yaml means the scalar must be quoted",
    "summary: &anchor-name would be read as an anchor",
    "summary: *alias-name would be read as an alias",
    "summary: !tag would be read as a tag",
    "summary: |block would be read as a block scalar",
    "summary: >folded would be read as a folded scalar",
    "summary: %directive is reserved",
    "summary: , leading comma is a flow indicator",
    "summary: # this whole value would be read as a comment",
    "summary: - dash-space starts a block sequence",
    "summary: ? question-space starts an explicit key",
    "summary: : colon-space starts a mapping value",
]

# Frontmatter shapes the deck legitimately uses. The guard's value depends on it
# staying quiet on every one of these.
PRECISION_LINES = [
    "title: card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it",
    "status: open",
    "stage: null",
    "contribution: medium",
    'created: "2026-08-16T04:50:03Z"',
    "closed_at: null",
    "human_gate: none",
    "advances: []",
    "advanced_by: []",
    "tags: [bug, infra, api-contract]",
    "draft: true",
    "worker: {who: rodja, where: main}",
    "definition_of_done: |",
    "summary: |",
    # A quoted scalar may hold anything the guard flags when unquoted.
    'summary: "Holds a nested `: ` and opens with a backtick — quoted, so legal."',
    # Indicator characters are only special at position 0 or after whitespace.
    "summary: emails like a@b.c and flags like -v are ordinary plain scalars",
    "summary: a hyphen-led-word is not a block sequence",
]


class CardFrontmatterYamlSensitivityTest(unittest.TestCase):
    """The guard can catch an offender — not just report a clean tree."""

    def test_flags_every_historical_offender(self) -> None:
        for label, line in HISTORICAL_OFFENDERS:
            with self.subTest(case=label):
                self.assertTrue(
                    guard.flag_frontmatter(line),
                    f"{label}: this line sat in the deck and strict YAML refused it; "
                    "if this fails the guard has stopped catching real offenders",
                )

    def test_each_hazard_shape_fires_on_its_own(self) -> None:
        """One nested-colon case and one leading-indicator case, so a dead shape shows."""
        nested = guard.flag_frontmatter("summary: a scalar with key: value inside")
        self.assertTrue([r for _l, _k, r in nested if "unquoted" in r], nested)

        leading = guard.flag_frontmatter("summary: `backtick-led scalar`")
        self.assertTrue([r for _l, _k, r in leading if "indicator" in r], leading)

    def test_every_leading_indicator_is_covered(self) -> None:
        for line in LEADING_INDICATOR_CASES:
            with self.subTest(line=line):
                self.assertTrue(
                    guard.flag_frontmatter(line),
                    f"{line!r} opens with a YAML indicator and must be flagged",
                )

    def test_reports_the_line_number_within_the_block(self) -> None:
        block = "title: a-card\nstatus: open\nsummary: holds a nested key: value\n"
        self.assertEqual([(3, "summary")], [(l, k) for l, k, _r in guard.flag_frontmatter(block)])

    def test_scan_deck_reports_a_planted_offender(self) -> None:
        """End-to-end: the deck scan, not just the predicate, surfaces a bad card."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp)
            good = deck / "cache-expires-too-soon"
            good.mkdir()
            good.joinpath("README.md").write_text(
                "---\ntitle: cache-expires-too-soon\n"
                'summary: "The cache expires before the first read."\n---\n\n# body\n',
                encoding="utf-8",
            )
            bad = deck / "retry-budget-is-never-reset"
            bad.mkdir()
            bad.joinpath("README.md").write_text(
                "---\ntitle: retry-budget-is-never-reset\n"
                "summary: `goc done` refuses to close.\n---\n\n# body\n",
                encoding="utf-8",
            )

            flagged = {card for card, _l, _k, _r in guard.scan_deck(deck)}
            self.assertEqual({"retry-budget-is-never-reset"}, flagged)

    def test_check_exits_nonzero_on_an_offending_deck(self) -> None:
        """The contract the `card-frontmatter-yaml` pre-commit hook depends on.

        Also pins `main`'s two reads of `DECK_DIR` to the same directory: the
        card count was a late-bound global while the scan rode `scan_deck`'s
        default argument, which binds once at definition. Repointing the module
        attribute therefore counted the planted deck and scanned the real one,
        reporting "clean (1 cards scanned)" on an offender.
        """
        import contextlib
        import io
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp)
            card = deck / "retry-budget-is-never-reset"
            card.mkdir()
            card.joinpath("README.md").write_text(
                "---\ntitle: retry-budget-is-never-reset\n"
                "summary: `goc done` refuses to close.\n---\n\n# body\n",
                encoding="utf-8",
            )
            original = guard.DECK_DIR
            guard.DECK_DIR = deck
            try:
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = guard.main(["--check"])
            finally:
                guard.DECK_DIR = original

            self.assertEqual(1, code, f"stdout was: {out.getvalue()!r}")
            self.assertIn("retry-budget-is-never-reset", out.getvalue())
            self.assertNotIn("clean", out.getvalue())


class CardFrontmatterYamlPrecisionTest(unittest.TestCase):
    """The guard stays quiet on the frontmatter the deck actually writes."""

    def test_no_false_positive_on_legitimate_lines(self) -> None:
        for line in PRECISION_LINES:
            with self.subTest(line=line):
                self.assertEqual(
                    [],
                    guard.flag_frontmatter(line),
                    f"{line!r} is legal YAML and must not be flagged",
                )

    def test_block_scalar_and_sequence_continuations_are_not_scanned(self) -> None:
        """Indented content is opaque to YAML's plain-scalar rules.

        A DoD item routinely holds `: ` and backticks; flagging those would make
        the guard unusable on every card in the deck.
        """
        block = (
            "definition_of_done: |\n"
            "  - [ ] TDD: `goc done` refuses to close with an unchecked box\n"
            "  - [ ] MECHANICAL: docs updated\n"
            "advances:\n"
            "  - some-other-card: with a colon in the slug-ish text\n"
        )
        self.assertEqual([], guard.flag_frontmatter(block))

    def test_unterminated_frontmatter_is_not_this_guards_finding(self) -> None:
        """`goc validate` owns the malformation; the exit code stays YAML-only."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp)
            card = deck / "retry-budget-is-never-reset"
            card.mkdir()
            card.joinpath("README.md").write_text(
                "---\ntitle: retry-budget-is-never-reset\n", encoding="utf-8"
            )
            self.assertEqual([], guard.scan_deck(deck))

    def test_live_deck_is_strict_yaml_clean(self) -> None:
        findings = guard.scan_deck()
        self.assertEqual(
            [],
            findings,
            "every card's frontmatter must be readable by a strict YAML parser — "
            "goc's own kickoff briefing promises consumers that each card is a "
            f"Markdown file with YAML frontmatter; found {len(findings)} violation(s)",
        )

    def test_live_deck_is_actually_being_scanned(self) -> None:
        """Guard the guard: a clean result must come from real cards, not an
        empty glob. Without this, moving or renaming the deck would turn
        `test_live_deck_is_strict_yaml_clean` into a vacuous pass."""
        self.assertGreater(len(list(guard.DECK_DIR.glob("*/README.md"))), 100)


if __name__ == "__main__":
    unittest.main()
