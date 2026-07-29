"""Regression guard for AGENTS.md § "Card authoring rules" — the English-only rule.

Three of the four rules AGENTS.md states for cards filed in this repo had no
enforcement anywhere. `openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session`
proved it empirically: filed 2026-07-18, renamed by hand 2026-07-27, and clean
under `goc quality-pass` for all nine days in between, because every entry in
`engine.TITLE_ANTIPATTERNS` is a jargon shape or a character class that a
well-formed ASCII slug in German satisfies.

`scripts/check_card_language.py` closes the English-only rule. This suite is
where it is enforced — CI runs the regression tests on every push, so a
non-English card turns the build red on the commit that files it. It also
carries the requirement inherited from the card
`static-source-guards-never-prove-they-can-catch-an-offender`: a static guard
must demonstrate it can catch an offender, not merely report a clean tree.
`test_flags_the_historical_offender` and the `RECALL_CASES` table are that
demonstration; a guard that silently stopped matching would fail them rather
than passing quietly on a deck that happens to be clean.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_guard():
    """Import scripts/check_card_language.py without putting scripts/ on sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_goc_card_language_guard", ROOT / "scripts" / "check_card_language.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = _load_guard()

# The title this repo actually carried for nine days. German: "OpenClaw plugin
# skills force multiple reads per session."
HISTORICAL_OFFENDER = "openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session"

# Non-English text the guard must catch, one per language plus the two shapes
# that exercise each detection layer on its own.
RECALL_CASES = [
    ("historical offender (German, content words only)", HISTORICAL_OFFENDER),
    ("German with function words", "konfiguration-wird-nicht-geladen"),
    ("German, suffix layer alone", "berechtigung-check-schlaegt-fehl"),
    ("German -keit noun", "sichtbarkeit-toggle-is-ignored"),
    ("French", "le-cache-ne-se-vide-pas-apres-une-erreur"),
    ("Spanish", "el-validador-no-detecta-los-campos-vacios"),
    ("Italian", "gli-errori-non-sono-registrati-nel-log"),
    ("Dutch", "de-configuratie-wordt-niet-geladen"),
]

# English text the guard must NOT catch. Every entry is a homograph or an
# orthographic near-miss that a naive language heuristic would trip on: the
# guard's value depends on it staying quiet here.
PRECISION_CASES = [
    "auth-cookie-expires-too-soon",
    # The two false positives from
    # `card-language-guard-flags-legitimate-english-as-non-english`: `sprung`
    # and `strung` are the bare stems of four forms the old flat exception set
    # did exempt, and `des` lowercases the cipher acronym DES.
    "retry-loop-has-sprung-a-leak",
    "requests-are-strung-together-without-a-budget",
    "des-cipher-fallback-is-still-enabled",
    "triple-des-key-rotation-is-skipped",
    "schema-validation-fails-on-empty-tags",
    "todo-list-renderer-drops-completed-items",
    "per-user-rate-limit-is-off-by-one",
    "non-ascii-titles-are-silently-accepted",
    "war-room-dashboard-times-out",
    "tag-filter-ignores-case",
    "fast-path-skips-validation",
    "sin-and-cos-lookup-table-is-wrong",
    "die-cast-renderer-drops-a-frame",
    "com-example-package-name-collides",
    "sans-serif-fallback-font-is-missing",
    "pour-over-config-merge-drops-keys",
    "unsung-helper-is-dead-code",
    "unstrung-retry-loop-never-terminates",
    "release-notes-generator-skips-the-first-entry",
    "kitchen-sink-fixture-masks-a-real-failure",
]

# The English side of the `-ung` collision, spelled out: the participle stems and
# the prefixed forms built from them. The guard must read every one as English.
ENGLISH_UNG_FAMILY = [
    "hung", "rung", "sung", "dung", "lung", "clung", "flung", "slung",
    "stung", "swung", "wrung", "young", "sprung", "strung",
    "unhung", "unsung", "unslung", "unstrung", "unsprung",
    "restrung", "resprung", "overhung", "overstrung", "outflung", "upswung",
    "highstrung",
]

# German `-ung` nouns: the recall the suffix layer exists for. Exempting the
# English side must not cost any of these, which rules out "raise the length
# floor" and "drop the suffix layer" as fixes. Three of them (`Regelung`,
# `Rechnung`, `Reinigung`) start with the `re-` prefix, so they exercise the
# exact-stem requirement rather than a plain `startswith` test.
GERMAN_UNG_NOUNS = [
    "berechtigung", "aenderung", "pruefung", "loesung", "ordnung", "warnung",
    "rechnung", "regelung", "reinigung", "unterbrechung", "untersuchung",
    "umstellung", "buchung", "sammlung", "meinung",
]


class EnglishOnlyGuardSensitivityTest(unittest.TestCase):
    """The guard can catch an offender — not just report a clean tree."""

    def test_flags_the_historical_offender(self) -> None:
        reasons = guard.flag_text(HISTORICAL_OFFENDER)
        self.assertTrue(
            reasons,
            "the guard must flag the real title this repo carried for nine days; "
            "if this fails the English-only rule is unenforced again",
        )

    def test_flags_every_recall_case(self) -> None:
        for label, text in RECALL_CASES:
            with self.subTest(case=label):
                self.assertTrue(
                    guard.flag_text(text),
                    f"{label}: {text!r} should be flagged as non-English",
                )

    def test_each_detection_layer_fires_on_its_own(self) -> None:
        """A marker-word-only and a suffix-only case, so one dead layer is visible."""
        word_only = guard.flag_text("cache-wird-nicht-geleert")
        self.assertTrue(any("marker word" in r for r in word_only), word_only)

        suffix_only = guard.flag_text("berechtigung-check-fails")
        self.assertTrue(any("ending on token" in r for r in suffix_only), suffix_only)

    def test_scan_deck_reports_a_planted_offender(self) -> None:
        """End-to-end: the deck scan, not just the predicate, surfaces a bad card."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp)
            good = deck / "cache-expires-too-soon"
            good.mkdir()
            good.joinpath("README.md").write_text(
                "---\ntitle: cache-expires-too-soon\n"
                'summary: "The cache expires before the first read."\n---\n\n# body\n'
            )
            bad = deck / HISTORICAL_OFFENDER
            bad.mkdir()
            bad.joinpath("README.md").write_text(
                f"---\ntitle: {HISTORICAL_OFFENDER}\n"
                'summary: "Die Skills werden mehrfach gelesen."\n---\n\n# body\n'
            )

            findings = guard.scan_deck(deck)
            flagged = {card for card, _field, _reason in findings}
            self.assertIn(HISTORICAL_OFFENDER, flagged)
            self.assertNotIn("cache-expires-too-soon", flagged)

    def test_scan_deck_reads_the_definition_of_done(self) -> None:
        """DoD items are in scope per AGENTS.md, not only title and summary."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp)
            card = deck / "retry-budget-is-never-reset"
            card.mkdir()
            card.joinpath("README.md").write_text(
                "---\n"
                "title: retry-budget-is-never-reset\n"
                'summary: "The retry budget survives a reconnect."\n'
                "definition_of_done: |\n"
                "  - [ ] TDD: der Test schlaegt ohne den Fix fehl\n"
                "---\n\n# body\n"
            )
            fields = {field for _card, field, _reason in guard.scan_deck(deck)}
            self.assertEqual(fields, {"definition_of_done"})


class EnglishOnlyUngCollisionTest(unittest.TestCase):
    """The one marker suffix with an English collision, from both sides.

    Regression guard for
    `card-language-guard-flags-legitimate-english-as-non-english`: the exemption
    started life as a flat five-word set that missed nine members of the same
    family, so these tests pin the family and the German recall it must not cost.
    """

    def test_the_whole_english_ung_family_reads_clean(self) -> None:
        flagged = {w: guard.flag_text(w) for w in ENGLISH_UNG_FAMILY if guard.flag_text(w)}
        self.assertEqual(
            flagged,
            {},
            "these are English words; flagging one blocks a legitimate card at "
            f"pre-commit and turns CI red. Offenders: {flagged}",
        )

    def test_german_ung_nouns_are_still_caught(self) -> None:
        missed = [n for n in GERMAN_UNG_NOUNS if not guard.flag_text(n)]
        self.assertEqual(
            missed,
            [],
            "exempting the English side must not cost German recall; "
            f"the suffix layer stopped catching {missed}",
        )

    def test_exemption_composes_beyond_the_source_literals(self) -> None:
        """Derived, not enumerated — the property the original set lacked.

        Composes every prefix with every stem and keeps only the forms that
        appear nowhere in the guard's own source text. A hand-written exception
        list cannot exempt a token it does not contain, so this is the assertion
        that fails if anybody replaces the rule with another enumeration.
        """
        source = (ROOT / "scripts" / "check_card_language.py").read_text(encoding="utf-8")
        composed = [
            prefix + stem
            for prefix in guard.ENGLISH_UNG_PREFIXES
            for stem in guard.ENGLISH_UNG_STEMS
            if prefix + stem not in source
        ]
        self.assertTrue(
            composed, "expected some prefix+stem forms to be absent from the source text"
        )
        for token in composed:
            with self.subTest(token=token):
                self.assertEqual(
                    guard.flag_text(token),
                    [],
                    f"{token!r} is prefix+stem and must be exempt by derivation",
                )

    def test_des_is_not_a_marker_word(self) -> None:
        """`DES`/`3DES` is an English acronym, the category layer 1 excludes."""
        self.assertNotIn("des", guard.MARKER_WORDS)
        self.assertEqual(guard.flag_text("des"), [])

    def test_french_recall_survives_without_des(self) -> None:
        """Dropping `des` cost no recall: the French case flags on other words."""
        reasons = guard.flag_text("le-cache-ne-se-vide-pas-apres-une-erreur")
        self.assertTrue(reasons, "the French recall case must still be flagged")
        self.assertFalse(
            [r for r in reasons if "'des'" in r], f"no reason may cite 'des': {reasons}"
        )


class EnglishOnlyGuardPrecisionTest(unittest.TestCase):
    """The guard stays quiet on English — including the homographs it excludes."""

    def test_no_false_positive_on_english_cases(self) -> None:
        for text in PRECISION_CASES:
            with self.subTest(text=text):
                self.assertEqual(
                    guard.flag_text(text),
                    [],
                    f"{text!r} is English and must not be flagged",
                )

    def test_live_deck_is_clean(self) -> None:
        findings = guard.scan_deck()
        self.assertEqual(
            findings,
            [],
            "every card in this repo's deck must satisfy AGENTS.md's English-only "
            f"rule; found {len(findings)} violation(s)",
        )

    def test_live_deck_is_actually_being_scanned(self) -> None:
        """Guard the guard: a clean result must come from real cards, not an
        empty glob. Without this, moving or renaming the deck would turn
        `test_live_deck_is_clean` into a vacuous pass."""
        self.assertGreater(len(list(guard.DECK_DIR.glob("*/README.md"))), 100)


if __name__ == "__main__":
    unittest.main()
