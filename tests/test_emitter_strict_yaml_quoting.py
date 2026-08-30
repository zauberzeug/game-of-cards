"""`emit_frontmatter` must write scalars a *strict* YAML reader accepts.

The emitter's quote trigger used to be scoped to "shapes the vendored parser
rejects" (`_YAML_INDICATOR_FIRST = frozenset("&*")`), and `validate_card` checks
parsed field *values* rather than the block's YAML legality. So seven ordinary
scalar shapes — a value opening with `!`, `%`, `- `, `? `, or a `|`/`>` that is
not a complete block header, plus any value holding a TAB — were emitted bare:
`yaml_lite` round-tripped all seven faithfully, `goc validate` reported `OK`, and
every reader outside goc refused the card. Six of them additionally turned this
repo's own `card-frontmatter-yaml` pre-commit hook red, whose remedy ("quote the
value") the next full-frontmatter re-emit undid.

The fix derives the trigger from YAML 1.2 §5.3's closed `c-indicator` list
instead of from observed bug reports, and `scripts/check_card_frontmatter_yaml.py`
imports those sets rather than restating them. This suite pins the three halves
of that contract:

* the seven shapes emit quoted and still round-trip through the vendored parser
  unchanged — widening the trigger must not break the side it was already
  correct for;
* the emitter and the guard agree on every character in the shared set, in both
  directions, so narrowing either alone turns the build red;
* the shared set is the spec's list, enumerated independently here so shrinking
  it in `goc/engine.py` cannot make the agreement test vacuous.

Filed and fixed on `goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse`.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from goc import engine
from goc._vendor import yaml_lite


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

# YAML 1.2 §5.3 `c-indicator`, transcribed from the spec. Independent of
# `engine._YAML_INDICATORS` on purpose: it is the fixed external reference the
# engine's set is supposed to be, so dropping a character there fails here
# rather than quietly shrinking every loop below.
SPEC_C_INDICATORS = frozenset("-?:,[]{}#&*!|>'\"%@`")

# The three indicators YAML binds only when they are followed by whitespace or
# stand alone (`ns-plain-first` admits `-`, `?` and `:` before an `ns-char`).
SPEC_SPACE_BOUND = frozenset("-?:")

# The seven values from the card's `reproduce.py`, each a plausible card summary
# and each refused by strict YAML as a plain scalar. Verified against PyYAML
# 6.0.3 (not a dependency of this repo — the errors are recorded, not re-run).
STRICT_YAML_REFUSED = [
    ("!important deck rewrite", "could not determine a constructor for the tag"),
    ("%-based progress metric", "while scanning for the next token"),
    ("- listed as a sub-item", "sequence entries are not allowed here"),
    ("? unclear which verb wrote it", "mapping keys are not allowed here"),
    ("|pipe-delimited output", "while scanning a block scalar"),
    (">greater-than in a diff", "while scanning a block scalar"),
    ("column\tseparated", "while scanning for the next token"),
]


def _emit(value: str) -> str:
    """Emit a minimal card carrying `value` as its summary, with a field below.

    The trailing `status` field is what makes a truncated scalar visible: a
    value the parser splits drops every field beneath it.
    """
    return engine.emit_frontmatter(
        {"title": "probe-card", "summary": value, "status": "open"}
    )


def _summary_line(block: str) -> str:
    return next(ln for ln in block.splitlines() if ln.startswith("summary:"))


def _frontmatter_block(text: str) -> str:
    """The raw text between the `---` delimiters, as the guard reads it."""
    return text[len("---\n") : text.rindex("\n---\n") + 1]


class StrictYamlIllegalShapesTest(unittest.TestCase):
    """The seven shapes emit quoted and survive the vendored parser."""

    def test_each_shape_emits_as_a_quoted_scalar(self) -> None:
        for value, yaml_error in STRICT_YAML_REFUSED:
            with self.subTest(value=value):
                rendered = _summary_line(_emit(value))[len("summary: ") :]
                self.assertTrue(
                    rendered.startswith('"'),
                    f"{value!r} is illegal as a YAML plain scalar (strict readers "
                    f"refuse it with {yaml_error!r}); the emitter must quote it, "
                    f"got {rendered!r}",
                )

    def test_each_shape_round_trips_through_the_vendored_parser(self) -> None:
        """Widening the quote trigger must not break the parser side.

        `yaml_lite` already read all seven back faithfully when they were
        emitted bare — that is exactly why a parser-derived trigger could not
        see them. The quoted form has to be just as faithful, including the
        field emitted after the summary.
        """
        for value, _yaml_error in STRICT_YAML_REFUSED:
            with self.subTest(value=value):
                parsed = yaml_lite.safe_load(_frontmatter_block(_emit(value)))
                self.assertEqual(value, parsed.get("summary"))
                self.assertEqual("open", parsed.get("status"))

    def test_a_hand_quoted_value_survives_re_emission(self) -> None:
        """The remedy the guard prints has to converge.

        A full-frontmatter re-emit (`goc advance`, `goc wait`, `goc decide`, …)
        used to strip the quote the guard demanded, so the operator's fix was
        undone by the next unrelated verb.
        """
        for value, _yaml_error in STRICT_YAML_REFUSED:
            with self.subTest(value=value):
                once = _emit(value)
                twice = _emit(yaml_lite.safe_load(_frontmatter_block(once))["summary"])
                self.assertEqual(once, twice)
                self.assertTrue(_summary_line(twice).startswith('summary: "'))

    def test_a_tab_anywhere_forces_a_quote(self) -> None:
        """TAB is illegal anywhere in a plain scalar, not just at the head."""
        for value in ["\tleading", "interior\ttab", "trailing\t", "\t"]:
            with self.subTest(value=value):
                rendered = _summary_line(_emit(value))[len("summary: ") :]
                self.assertTrue(rendered.startswith('"'), rendered)
                parsed = yaml_lite.safe_load(_frontmatter_block(_emit(value)))
                self.assertEqual(value, parsed.get("summary"))


class EmitterGuardAgreementTest(unittest.TestCase):
    """The emitter and the repo guard consult one set, in both directions."""

    def _probe_value(self, char: str) -> str:
        """A value opening with `char` that is a hazard for that character.

        The space-bound three need the space to bind at all — `-v` and `?query`
        are ordinary plain scalars and must stay unquoted.
        """
        if char in engine._YAML_SPACE_BOUND_INDICATORS:
            return f"{char} opens a structure here"
        return f"{char}opens a structure here"

    def test_the_shared_set_is_the_spec_list(self) -> None:
        """Anchor the set to the spec, so shrinking it fails here.

        Without this, dropping a character from `engine._YAML_INDICATORS` would
        merely shorten every loop below and pass.
        """
        self.assertEqual(SPEC_C_INDICATORS, set(engine._YAML_INDICATORS))
        self.assertEqual(SPEC_SPACE_BOUND, set(engine._YAML_SPACE_BOUND_INDICATORS))
        self.assertEqual(
            SPEC_C_INDICATORS - SPEC_SPACE_BOUND, set(engine._YAML_INDICATOR_FIRST)
        )

    def test_guard_reads_the_engine_set_rather_than_restating_it(self) -> None:
        """The coupling itself — a restated tuple in the guard is the defect."""
        self.assertEqual(
            set(engine._YAML_INDICATOR_FIRST), set(guard.LEADING_INDICATORS)
        )
        self.assertEqual(
            set(engine._YAML_SPACE_BOUND_INDICATORS), set(guard.SPACE_BOUND_INDICATORS)
        )

    def test_emitter_quotes_every_indicator_and_the_guard_goes_quiet(self) -> None:
        """Forward direction: what the emitter writes, the guard accepts."""
        for char in sorted(SPEC_C_INDICATORS):
            with self.subTest(char=char):
                value = self._probe_value(char)
                block = _frontmatter_block(_emit(value))
                self.assertTrue(
                    _summary_line(block).startswith('summary: "'),
                    f"a value opening with {char!r} must emit quoted, got "
                    f"{_summary_line(block)!r}",
                )
                self.assertEqual(
                    [],
                    guard.flag_frontmatter(block),
                    f"the guard must stay silent on what the emitter writes for {char!r}",
                )
                self.assertEqual(value, yaml_lite.safe_load(block).get("summary"))

    def test_guard_flags_the_bare_form_of_every_indicator(self) -> None:
        """Reverse direction: what the emitter would have written bare is a
        finding, so narrowing the guard alone fails here.

        The four already-structured prefixes are exempt because the guard skips
        any value opening with `"`, `'`, `[` or `{` as quoted or flow-structured
        — whether that skip is itself sound is the separate open card
        `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`,
        not this one. The emitter's side of those four is still asserted by
        `test_emitter_quotes_every_indicator_and_the_guard_goes_quiet`.
        """
        for char in sorted(SPEC_C_INDICATORS - set(guard.STRUCTURED_PREFIXES)):
            with self.subTest(char=char):
                bare = f"summary: {self._probe_value(char)}\n"
                self.assertTrue(
                    guard.flag_frontmatter(bare),
                    f"{bare!r} is not legal YAML and must be flagged",
                )

    def test_guard_flags_a_bare_tab_the_emitter_would_never_write(self) -> None:
        self.assertTrue(guard.flag_frontmatter("summary: column\tseparated\n"))

    def test_non_binding_indicator_heads_stay_unquoted(self) -> None:
        """Precision: the widening must not quote ordinary prose.

        `-v`, `?query` and `:ratio` are legal plain scalars, and quoting them
        would rewrite the `summary` line of cards nobody edited.
        """
        for value in ["-v is a flag", "?query-shaped", "-1000 is not a sequence"]:
            with self.subTest(value=value):
                rendered = _summary_line(_emit(value))[len("summary: ") :]
                self.assertFalse(
                    rendered.startswith('"'),
                    f"{value!r} is a legal plain scalar and must stay bare, got "
                    f"{rendered!r}",
                )
                self.assertEqual([], guard.flag_frontmatter(_frontmatter_block(_emit(value))))


if __name__ == "__main__":
    unittest.main()
