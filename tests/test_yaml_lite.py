"""Tests for goc/_vendor/yaml_lite.py — the vendored YAML subset parser.

Covers:
  - Scalar types (null, bool, int, date string, plain/quoted strings)
  - Inline flow list and mapping
  - Block scalar ( | and |- )
  - Block sequence of scalars and of inline maps
  - Block mapping (nested)
  - Comments (own-line and inline)
  - Round-trip parity against the real deck: parse → emit → parse is byte-equal
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc._vendor.yaml_lite import ParseError, safe_load  # noqa: E402


class ScalarTest(unittest.TestCase):
    def _load(self, text: str):
        return safe_load(f"k: {text}\n")["k"]

    def test_null_keyword(self):
        self.assertIsNone(self._load("null"))
        self.assertIsNone(self._load("~"))
        self.assertIsNone(self._load(""))

    def test_bool(self):
        self.assertIs(self._load("true"), True)
        self.assertIs(self._load("yes"), True)
        self.assertIs(self._load("false"), False)
        self.assertIs(self._load("no"), False)

    def test_integer(self):
        self.assertEqual(self._load("42"), 42)
        self.assertEqual(self._load("-1"), -1)

    def test_date_string(self):
        self.assertEqual(self._load("2026-05-09"), "2026-05-09")

    def test_plain_string(self):
        self.assertEqual(self._load("hello"), "hello")
        self.assertEqual(self._load("ship-game-of-cards"), "ship-game-of-cards")

    def test_double_quoted(self):
        self.assertEqual(self._load('"hello"'), "hello")
        self.assertEqual(self._load('"a\\nb"'), "a\nb")
        self.assertEqual(self._load('"it\\"s"'), 'it"s')

    def test_single_quoted(self):
        self.assertEqual(self._load("'hello'"), "hello")
        self.assertEqual(self._load("''''"), "'")

    def test_inline_flow_list(self):
        self.assertEqual(self._load("[a, b, c]"), ["a", "b", "c"])
        self.assertEqual(self._load("[]"), [])
        self.assertEqual(self._load("[null, alpha]"), [None, "alpha"])

    def test_inline_flow_map(self):
        self.assertEqual(self._load("{who: alice, where: main}"), {"who": "alice", "where": "main"})
        self.assertEqual(self._load('{"who": "bob"}'), {"who": "bob"})


class BlockScalarTest(unittest.TestCase):
    def test_block_literal(self):
        text = "dod: |\n  - [ ] item one\n  - [ ] item two\n"
        self.assertEqual(safe_load(text)["dod"], "- [ ] item one\n- [ ] item two\n")

    def test_block_literal_strip(self):
        text = "dod: |-\n  line one\n  line two\n"
        self.assertEqual(safe_load(text)["dod"], "line one\nline two")

    def test_block_literal_blank_lines(self):
        text = "dod: |\n  first\n\n  second\n"
        self.assertEqual(safe_load(text)["dod"], "first\n\nsecond\n")

    def test_empty_block_literal_followed_by_sibling_key(self):
        text = "title: x\ndefinition_of_done: |\nworker: alice\n"
        self.assertEqual(
            safe_load(text),
            {"title": "x", "definition_of_done": "", "worker": "alice"},
        )

    def test_empty_block_literal_strip_followed_by_sibling_key(self):
        text = "title: x\nfoo: |-\nbar: baz\n"
        self.assertEqual(
            safe_load(text),
            {"title": "x", "foo": "", "bar": "baz"},
        )

    def test_empty_block_literal_at_end_of_document(self):
        text = "title: x\ndod: |\n"
        self.assertEqual(safe_load(text), {"title": "x", "dod": ""})

    def test_empty_block_literal_inside_nested_mapping(self):
        text = "outer:\n  dod: |\n  next: value\n"
        self.assertEqual(
            safe_load(text),
            {"outer": {"dod": "", "next": "value"}},
        )

    def test_interior_whitespace_only_line_preserved(self):
        # A whitespace-only content line between two content lines keeps the
        # spaces past the block indent (here: 2 indent + 3 interior spaces).
        text = "s: |-\n  first\n     \n  third\n"
        self.assertEqual(safe_load(text)["s"], "first\n   \nthird")

    def test_whitespace_only_line_shorter_than_block_indent(self):
        # A blank line with fewer characters than the block indent yields ""
        # (a genuine interior blank), not a slice past the string end.
        text = "s: |-\n  first\n \n  third\n"
        self.assertEqual(safe_load(text)["s"], "first\n\nthird")

    def test_trailing_genuine_blank_still_chomped(self):
        # No regression: a truly-empty trailing line is still dropped by clip/
        # strip chomping.
        self.assertEqual(safe_load("s: |-\n  content\n\n")["s"], "content")
        self.assertEqual(safe_load("s: |\n  content\n\n")["s"], "content\n")

    def test_trailing_whitespace_only_line_preserved(self):
        # A trailing line whose characters past the block indent are whitespace
        # is content (the spaces survive), matching the meaningful-trailing-
        # whitespace invariant of the non-blank content-line path.
        self.assertEqual(safe_load("s: |-\n  content\n     \n")["s"], "content\n   ")

    def test_explicit_indentation_indicator_pins_block_indent(self):
        # `|2` fixes the block indent at 2 regardless of the first content line
        # being more-indented, so leading whitespace on content survives instead
        # of being folded into the block indent or raising on a later line.
        text = "s: |2\n    indented first\n  second line\n"
        self.assertEqual(safe_load(text)["s"], "  indented first\nsecond line\n")

    def test_explicit_indentation_indicator_strip(self):
        text = "s: |2-\n    indented summary\n  flush\n"
        self.assertEqual(safe_load(text)["s"], "  indented summary\nflush")

    def test_explicit_indentation_indicator_shared_leading_indent(self):
        # Every content line shares a 2-space leading indent; the indicator
        # preserves it instead of silently stripping it.
        text = "s: |2\n    - [ ] nested\n    - [ ] second\n"
        self.assertEqual(safe_load(text)["s"], "  - [ ] nested\n  - [ ] second\n")


class FoldedScalarRejectionTest(unittest.TestCase):
    """Folded scalars (`>`) are unsupported and must raise — for every
    indicator variant, not just the bare `>`. The guard used to be an
    exact-string `rest == ">"` check, so `>-`/`>+`/`>2`/… slipped past and
    were returned as the literal header string, silently dropping every
    field that followed."""

    def test_bare_folded_raises(self):
        with self.assertRaises(ParseError):
            safe_load("s: >\n  folded text\n")

    def test_strip_folded_raises_not_misparse(self):
        # The headline defect: `>-` returned {'s': '>-'} and dropped `t`.
        with self.assertRaises(ParseError):
            safe_load("s: >-\n  x\nt: kept\n")

    def test_all_folded_variants_raise(self):
        for ind in (">", ">-", ">+", ">2", ">2-", ">2+", ">10-"):
            doc = f"s: {ind}\n  folded one\n  folded two\nt: kept\n"
            with self.assertRaises(ParseError, msg=f"{ind!r} should raise"):
                safe_load(doc)


class TabIndentationRejectionTest(unittest.TestCase):
    """Tabs as indentation are listed under the docstring's
    "Unsupported (raises ParseError)" contract, but `_indent()` counted a
    tab as one indentation char with no guard — so tab-indented structural
    lines parsed silently, and a tab+space-indented key was promoted to a
    top-level sibling (silent structure corruption) instead of failing loud.
    The guard lives at the one structural chokepoint (`_peek`), so it must
    reject structural tab indentation while leaving block-scalar content
    (read directly, not via `_peek`) untouched."""

    def test_tab_indented_nested_mapping_raises(self):
        with self.assertRaises(ParseError):
            safe_load("parent:\n\tchild: v\n")

    def test_tab_indented_sequence_raises(self):
        with self.assertRaises(ParseError):
            safe_load("items:\n\t- a\n\t- b\n")

    def test_tab_plus_space_indent_raises_not_promote(self):
        # The headline defect: `\t  b: 2` parsed to {'a': 1, 'b': 2},
        # silently promoting `b` to a top-level sibling.
        with self.assertRaises(ParseError):
            safe_load("a: 1\n\t  b: 2\n")

    def test_block_scalar_content_with_tab_not_rejected(self):
        # Tabs inside literal-block content are legitimate and must survive;
        # the guard only covers structural indentation.
        doc = "body: |\n  - [ ] item\n  \tindented continuation\n  - [ ] item2\n"
        self.assertEqual(
            safe_load(doc)["body"],
            "- [ ] item\n\tindented continuation\n- [ ] item2\n",
        )

    def test_tab_inside_value_not_rejected(self):
        # A tab in the value (not the leading indentation) is content, not
        # indentation, and must round-trip.
        self.assertEqual(safe_load("k: a\tb\n")["k"], "a\tb")


class OverIndentedMappingRejectionTest(unittest.TestCase):
    """A space-indented line *more* indented than its surrounding mapping is
    malformed: `_parse_block_mapping` only broke on a less-indented line, so a
    more-indented key was silently promoted to a top-level sibling, and a
    more-indented bare plain-scalar continuation silently truncated every
    following key. PyYAML raises (Case 1) or folds (Case 2). The guard mirrors
    the tab guard and the block-scalar ambiguous-indent guard: fail loud."""

    def test_over_indented_mapping_key_raises_not_promote(self):
        # The headline defect: `  human_gate: decision` parsed to
        # {'status': 'open', 'human_gate': 'decision'}, silently promoting the
        # nested key to a top-level sibling.
        with self.assertRaises(ParseError):
            safe_load("status: open\n  human_gate: decision\n")

    def test_over_indented_bare_continuation_raises_not_truncate(self):
        # `  world` parsed to {'summary': 'hello'} — the continuation line was
        # dropped AND `status: open` was silently truncated off the document.
        with self.assertRaises(ParseError):
            safe_load("summary: hello\n  world\nstatus: open\n")

    def test_valid_nested_mapping_still_parses(self):
        # A legitimately-nested mapping (key with empty value, children
        # indented under it) must still parse unchanged — the guard fires only
        # at the top of the mapping loop, after _resolve_value consumed nesting.
        self.assertEqual(
            safe_load("a:\n  b: 1\n  c: 2\nd: 3\n"),
            {"a": {"b": 1, "c": 2}, "d": 3},
        )

    def test_valid_deeply_nested_mapping_still_parses(self):
        self.assertEqual(
            safe_load("a:\n  b:\n    c: 1\n  d: 2\ne: 3\n"),
            {"a": {"b": {"c": 1}, "d": 2}, "e": 3},
        )


class OverIndentedSequenceRejectionTest(unittest.TestCase):
    """A `- item` line *more* indented than its surrounding sequence is
    malformed: `_parse_block_sequence` only broke on a less-indented line, so a
    more-indented item was silently absorbed as a same-level sibling. This is
    the block-sequence analogue of OverIndentedMappingRejectionTest; the guard
    mirrors the mapping guard, the tab guard, and the block-scalar
    ambiguous-indent guard: fail loud."""

    def test_over_indented_sequence_item_raises_not_absorb(self):
        # The headline defect: `      - second-target` parsed into the same
        # list as `  - first-target`, silently absorbing the over-indented item
        # as a same-level sibling instead of rejecting the ambiguous indent.
        with self.assertRaises(ParseError):
            safe_load(
                "advances:\n  - first-target\n      - second-target\n"
                "contribution: high\n"
            )

    def test_over_indented_top_level_sequence_item_raises(self):
        with self.assertRaises(ParseError):
            safe_load("- a\n    - b\n")

    def test_valid_sequence_still_parses(self):
        # Items at the same indent (the shape the emitter produces for the four
        # edge fields) must still parse unchanged — the guard fires only on a
        # strictly more-indented item.
        self.assertEqual(
            safe_load("advances:\n  - first\n  - second\nkey: v\n"),
            {"advances": ["first", "second"], "key": "v"},
        )

    def test_valid_nested_sequence_still_parses(self):
        # A legitimately-nested sequence (empty item whose content is a deeper
        # sequence) is consumed in full by the recursion before control returns
        # to the parent loop, so the guard does not fire on it.
        self.assertEqual(
            safe_load("- a\n-\n  - b\n  - c\n- d\n"),
            ["a", ["b", "c"], "d"],
        )

    def test_valid_inline_map_sequence_item_still_parses(self):
        self.assertEqual(
            safe_load("checks:\n  - name: foo\n    kind: derived\n")["checks"],
            [{"name": "foo", "kind": "derived"}],
        )


class BlockSequenceTest(unittest.TestCase):
    def test_sequence_of_scalars(self):
        text = "tags:\n  - story\n  - infra\n"
        self.assertEqual(safe_load(text)["tags"], ["story", "infra"])

    def test_sequence_of_maps(self):
        text = "checks:\n  - name: foo\n    kind: derived\n  - name: bar\n    kind: derived\n"
        self.assertEqual(safe_load(text)["checks"], [
            {"name": "foo", "kind": "derived"},
            {"name": "bar", "kind": "derived"},
        ])

    def test_empty_list(self):
        self.assertEqual(safe_load("items: []\n")["items"], [])


class CommentsTest(unittest.TestCase):
    def test_own_line_comment_skipped(self):
        text = "# top comment\nkey: value\n"
        self.assertEqual(safe_load(text)["key"], "value")

    def test_inline_comment_stripped(self):
        text = "key: value # inline\n"
        self.assertEqual(safe_load(text)["key"], "value")

    def test_comment_inside_quoted_preserved(self):
        text = 'key: "value # not a comment"\n'
        self.assertEqual(safe_load(text)["key"], "value # not a comment")

    def test_comment_inside_sequence_list(self):
        text = "tags:\n  # a comment\n  - bug\n"
        self.assertEqual(safe_load(text)["tags"], ["bug"])


class FullFrontmatterTest(unittest.TestCase):
    SAMPLE = """\
title: test-card
summary: "A card for testing"
status: open
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - parent-epic
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] item one
  - [ ] item two
worker: {who: "claude[bot]", where: main}
"""

    def test_full_parse(self):
        data = safe_load(self.SAMPLE)
        self.assertEqual(data["title"], "test-card")
        self.assertEqual(data["summary"], "A card for testing")
        self.assertEqual(data["status"], "open")
        self.assertIsNone(data["stage"])
        self.assertEqual(data["contribution"], "medium")
        self.assertEqual(data["created"], "2026-05-09")
        self.assertIsNone(data["closed_at"])
        self.assertEqual(data["human_gate"], "none")
        self.assertEqual(data["advances"], ["parent-epic"])
        self.assertEqual(data["advanced_by"], [])
        self.assertEqual(data["tags"], ["story", "infra"])
        self.assertEqual(data["definition_of_done"], "- [ ] item one\n- [ ] item two\n")
        self.assertEqual(data["worker"], {"who": "claude[bot]", "where": "main"})


class EscapedQuoteFlowSplitTest(unittest.TestCase):
    """_split_flow / _split_key must honor backslash escapes inside double
    quotes, so an emitter-produced `\\"` is not seen as a delimiting quote and
    the structural comma after it is not swallowed."""

    def test_flow_mapping_value_with_escaped_quote(self):
        # The `where` key must survive; `who` must dequote exactly.
        self.assertEqual(
            safe_load('worker: {who: "a\\"", where: b}\n')["worker"],
            {"who": 'a"', "where": "b"},
        )

    def test_flow_sequence_element_with_escaped_quote(self):
        self.assertEqual(
            safe_load('sample: ["a\\"", "b"]\n')["sample"],
            ['a"', "b"],
        )

    def test_block_key_with_escaped_quote_in_quoted_value(self):
        # _split_key shares the same quote loop; an escaped quote inside a
        # double-quoted value must not terminate quote mode early.
        self.assertEqual(safe_load('k: "a\\"b"\n')["k"], 'a"b')

    def test_strip_comment_honors_escaped_quote_before_hash(self):
        # _strip_comment is the third sibling sharing the quote loop. An
        # escaped quote inside a double-quoted scalar must not close quote
        # mode, or a later ` #` is misread as a comment and the value is
        # truncated. Regression for strip-comment-closes-double-quoted-
        # scalar-on-backslash-escaped-quote.
        self.assertEqual(safe_load('k: "a\\" b #c"\n')["k"], 'a" b #c')
        # Guard: a `#` inside a balanced double-quoted scalar (with an
        # escaped quote) is still preserved, and a bare unbalanced quote
        # still strips its trailing comment.
        self.assertEqual(safe_load('a: "x \\" y # z"\n')["a"], 'x " y # z')
        self.assertEqual(safe_load("title: don't  # note\n")["title"], "don't")

    def test_engine_round_trip_summary_with_quote_and_hash(self):
        from goc import engine as e

        summary = 'a " b #c'
        text = e.emit_frontmatter(
            {"title": "t", "status": "open", "summary": summary}, body="x"
        )
        self.assertEqual(e.parse_frontmatter(text)[0]["summary"], summary)

    def test_engine_round_trip_worker_with_quote(self):
        from goc import engine as e

        worker = {"who": 'a"', "where": "b"}
        text = e.emit_frontmatter(
            {"title": "t", "status": "open", "worker": worker}, body="x"
        )
        self.assertEqual(e.parse_frontmatter(text)[0]["worker"], worker)


class BlockScalarIndicatorRoundTripTest(unittest.TestCase):
    """emit_frontmatter must pick the chomp indicator from a multi-line string
    value's own trailing-newline state, so the emit->parse round-trip is
    faithful and an authored clip block (`summary: |`) is not silently flipped
    to strip (`|-`) with its trailing newline dropped. Regression for
    emit-frontmatter-always-strips-trailing-newline-from-multi-line-string-fields.
    """

    def test_authored_clip_block_summary_survives_reemit(self):
        from goc import engine as e

        authored = (
            "---\n"
            "title: x\n"
            "summary: |\n"
            "  line one\n"
            "  line two\n"
            "status: open\n"
            "---\n\nbody\n"
        )
        fm, body = e.parse_frontmatter(authored)
        self.assertEqual(fm["summary"], "line one\nline two\n")
        reemitted = e.emit_frontmatter(fm, body=body)
        # Indicator stays clip; value (with trailing newline) is preserved.
        self.assertIn("summary: |\n", reemitted)
        self.assertNotIn("summary: |-", reemitted)
        self.assertEqual(e.parse_frontmatter(reemitted)[0]["summary"], fm["summary"])

    def test_value_without_trailing_newline_emits_strip(self):
        from goc import engine as e

        fm = {"title": "y", "status": "open", "summary": "alpha\nbeta"}
        out = e.emit_frontmatter(fm, body="x")
        # No trailing newline -> strip indicator, faithful round-trip.
        self.assertIn("summary: |-\n", out)
        self.assertEqual(e.parse_frontmatter(out)[0]["summary"], "alpha\nbeta")

    def test_reemit_is_idempotent_for_both_states(self):
        from goc import engine as e

        for summary in ("a\nb\n", "a\nb"):
            fm = {"title": "t", "status": "open", "summary": summary}
            once = e.emit_frontmatter(fm, body="x")
            twice = e.emit_frontmatter(e.parse_frontmatter(once)[0], body="x")
            self.assertEqual(once, twice, msg=f"non-idempotent for {summary!r}")

    def test_single_line_block_header_shaped_scalar_round_trips(self):
        # A single-line scalar whose whole value is a block/folded indicator —
        # literal (`|2`, `|3`, `|2-`, `|2+`, `|10`) OR folded (`>2`, `>3`,
        # `>10`, `>2-`, `>2+`) — must be quoted by the emitter so it round-trips
        # unchanged. The folded-with-digits family is the regression for
        # frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted: the
        # parser recognizes `>2` as a folded header and raises, so an unquoted
        # emit crashed on re-parse.
        from goc import engine as e

        headers = [
            "|2", "|3", "|2-", "|2+", "|10",
            ">2", ">3", ">10", ">2-", ">2+",
        ]
        for val in headers:
            fm = {"title": "t", "status": "open", "summary": val}
            out = e.emit_frontmatter(fm, body="x")
            parsed = e.parse_frontmatter(out)[0]
            self.assertEqual(
                parsed["summary"], val,
                msg=f"block-header-shaped scalar {val!r} did not round-trip",
            )


class NonLFLineBreakRefusalTest(unittest.TestCase):
    """A single-line scalar carrying a non-LF line-break character must never be
    emitted bare. The vendored parser splits the document with str.splitlines(),
    which breaks on nine characters beyond LF (CR, VT, FF, FS, GS, RS, NEL,
    U+2028, U+2029); emitting such a value bare truncates it on re-parse and
    silently drops every frontmatter field below it. Literal-block style can't
    rescue them either — it rewrites the break to LF — so the emitter refuses
    them at the boundary, the same posture as the LF and float branches.
    Regression for
    inline-emitter-writes-non-newline-line-breaks-bare-dropping-subsequent-frontmatter.
    """

    NON_LF_BREAKS = {
        "CR": "\r",
        "VT": "\x0b",
        "FF": "\x0c",
        "FS": "\x1c",
        "GS": "\x1d",
        "RS": "\x1e",
        "NEL": "\x85",
        "LS": " ",
        "PS": " ",
    }

    def test_yaml_inline_refuses_each_non_lf_break(self):
        from goc import engine as e

        for name, ch in self.NON_LF_BREAKS.items():
            with self.assertRaises(e.FrontmatterError, msg=f"{name} not refused"):
                e._yaml_inline(f"line one{ch}line two")

    def test_emit_frontmatter_refuses_summary_with_non_lf_break(self):
        from goc import engine as e

        for name, ch in self.NON_LF_BREAKS.items():
            fm = {
                "title": "t",
                "status": "open",
                "summary": f"line one{ch}line two",
                "tags": ["bug"],
            }
            with self.assertRaises(e.FrontmatterError, msg=f"{name} not refused"):
                e.emit_frontmatter(fm, body="x")

    def test_non_lf_break_alongside_lf_is_refused_not_block_emitted(self):
        # A value carrying BOTH an LF and a non-LF break must not be routed to
        # literal-block style: the block emitter would rewrite the non-LF break
        # to LF, silently corrupting the value. It must hit the boundary refusal.
        from goc import engine as e

        fm = {"title": "t", "status": "open", "summary": "a\nb\rc"}
        with self.assertRaises(e.FrontmatterError):
            e.emit_frontmatter(fm, body="x")

    def test_plain_lf_multiline_still_block_emits(self):
        # The fix must not regress the LF case: a pure-LF multi-line value still
        # round-trips through literal-block style.
        from goc import engine as e

        fm = {"title": "t", "status": "open", "summary": "alpha\nbeta"}
        out = e.emit_frontmatter(fm, body="x")
        self.assertIn("summary: |-\n", out)
        self.assertEqual(e.parse_frontmatter(out)[0]["summary"], "alpha\nbeta")

    def test_detection_derives_from_splitlines(self):
        # The dangerous set is derived from str.splitlines(), so the predicate
        # agrees with the parser's own line-splitting for every break character
        # and stays empty for an ordinary single-line scalar.
        from goc import engine as e

        for ch in self.NON_LF_BREAKS.values():
            self.assertTrue(e._contains_line_break(f"x{ch}y"))
        self.assertTrue(e._contains_line_break("x\ny"))
        self.assertFalse(e._contains_line_break("ordinary single line"))
        self.assertFalse(e._contains_line_break(""))


class DeckRoundTripTest(unittest.TestCase):
    """Parse every README.md in the real deck and verify key fields are present."""

    FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)

    def _deck_dir(self) -> Path:
        canonical = ROOT / ".game-of-cards" / "deck"
        if canonical.is_dir():
            return canonical
        legacy = ROOT / "deck"
        if legacy.is_dir():
            return legacy
        self.skipTest("no deck found")

    def test_all_cards_parse(self):
        deck = self._deck_dir()
        count = 0
        for readme in sorted(deck.rglob("README.md")):
            text = readme.read_text()
            m = self.FRONTMATTER_RE.match(text)
            if not m:
                continue
            data = safe_load(m.group(1))
            self.assertIn("title", data, msg=f"{readme}: missing title")
            self.assertIn("status", data, msg=f"{readme}: missing status")
            count += 1
        self.assertGreater(count, 0, "no card frontmatter found")


class NonMappingFrontmatterTest(unittest.TestCase):
    """Frontmatter that parses to a non-mapping YAML value must raise a
    coherent FrontmatterError, not a raw AttributeError from a downstream
    `fm.get(...)`."""

    def test_top_level_list_raises_frontmatter_error(self):
        from goc import engine as e

        with self.assertRaises(e.FrontmatterError) as ctx:
            e.parse_frontmatter("---\n- a\n- b\n---\nbody\n")
        self.assertIn("not a mapping", str(ctx.exception))
        self.assertIn("list", str(ctx.exception))

    def test_load_card_on_list_frontmatter_raises_frontmatter_error(self):
        import tempfile
        from goc import engine as e

        d = Path(tempfile.mkdtemp())
        (d / "README.md").write_text("---\n- a\n- b\n---\nbody\n")
        with self.assertRaises(e.FrontmatterError):
            e.load_card(d)

    def test_empty_frontmatter_still_yields_empty_dict(self):
        from goc import engine as e

        data, body = e.parse_frontmatter("---\n\n---\nbody\n")
        self.assertEqual(data, {})
        self.assertEqual(body, "body\n")
