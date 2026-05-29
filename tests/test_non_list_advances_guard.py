"""Regression: walkers must treat a non-list `advances`/`advanced_by`
frontmatter value as an empty edge set, matching `find_half_edges` and
`validate_card`.

A hand-edited bare-string scalar (e.g. `advances: bcard`) used to be
iterated character-by-character by `compute_values` and the cycle
detectors — emitting phantom dangling-edge warnings on the render path
and inflating priority values via a chance self-match on the
in-progress cycle branch.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr

from goc import engine


def _card(title: str, contribution: str = "low", **fm_extra) -> engine.Card:
    fm = {
        "title": title,
        "status": "open",
        "contribution": contribution,
        "advances": [],
        "advanced_by": [],
    }
    fm.update(fm_extra)
    return engine.Card(
        title=title, path=None, frontmatter=fm, body="", dod_open=0, dod_done=0
    )


class NonListAdvancesGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        engine._DANGLING_ADVANCES_WARNED.clear()

    def test_compute_values_treats_bare_string_advances_as_empty(self) -> None:
        """The render path is not gated by `goc validate`, so a hand-edited
        bare-string `advances` must not be walked character-by-character."""
        card = _card("a", advances="bcard")
        own = engine.CONTRIBUTION_RANK["low"]

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            values = engine.compute_values([card])
        value, path = values["a"]

        self.assertEqual(value, own, "leaf with non-list advances should value at own rank")
        self.assertEqual(path, ["self"])
        self.assertNotIn("dangling advances edge", stderr.getvalue())

    def test_compute_values_treats_other_non_list_advances_as_empty(self) -> None:
        for bad in (None, "string", 42, {"not": "a list"}):
            with self.subTest(bad=bad):
                engine._DANGLING_ADVANCES_WARNED.clear()
                card = _card("a", advances=bad)
                own = engine.CONTRIBUTION_RANK["low"]
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    values = engine.compute_values([card])
                value, _ = values["a"]
                self.assertEqual(value, own)
                self.assertNotIn("dangling advances edge", stderr.getvalue())

    def test_detect_advance_cycles_ignores_non_list_advanced_by(self) -> None:
        # Bare-string `advanced_by` must not crash or emit a spurious cycle.
        card = _card("a", advanced_by="abc")
        errors = engine.detect_advance_cycles([card])
        self.assertEqual(errors, [])

    def test_would_create_advance_cycle_ignores_non_list_advances(self) -> None:
        # _would_create_advance_cycle walks `advances` from a starting card;
        # a bare-string value must be treated as no outgoing edges.
        a = _card("a", advances="bcard")
        b = _card("b")
        self.assertFalse(engine._would_create_advance_cycle([a, b], "a", "b"))

    def test_find_half_edges_treats_non_list_inverse_as_empty(self) -> None:
        # `find_half_edges` walks the neighbour's inverse field after the
        # outer guard; a bare-string inverse must not fall back to Python's
        # substring `in` (which silently affirms a reverse edge that does
        # not structurally exist).
        a = _card("acard", advances=["bcard"])
        b = _card("bcard", advanced_by="acard-suffix-that-contains-acard")
        edges = engine.find_half_edges([a, b])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].src, "acard")
        self.assertEqual(edges[0].field, "advances")
        self.assertEqual(edges[0].ref, "bcard")
        self.assertEqual(edges[0].inverse, "advanced_by")

    def test_find_half_edges_treats_exact_match_bare_string_as_empty(self) -> None:
        # Even an exact-match bare string is not a list; the structural
        # invariant requires the inverse to be a list, not a scalar.
        a = _card("acard", advances=["bcard"])
        b = _card("bcard", advanced_by="acard")
        edges = engine.find_half_edges([a, b])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].ref, "bcard")


class TagsPropertyGuardTest(unittest.TestCase):
    """`Card.tags` must coerce a non-list frontmatter value to `[]` so the
    render path (`",".join(t.tags[:4])`) and the filter path
    (`tag in t.tags`) don't iterate characters or substring-match. Same
    root-cause family as `compute_values` / `find_half_edges` — see
    closed siblings `compute-values-iterates-non-list-advances-…` and
    `repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string`."""

    def test_bare_string_tags_renders_as_empty_not_character_by_character(self) -> None:
        card = _card("a", tags="bug")
        rendered = ",".join(card.tags[:4])
        self.assertEqual(rendered, "")

    def test_bare_string_tags_does_not_substring_match_in_filter(self) -> None:
        card = _card("a", tags="bug")
        # The filter site does `tag in t.tags`; with the guard, `tags` is
        # `[]` and no single-character query matches.
        self.assertFalse(all(tag in card.tags for tag in ["b"]))
        self.assertFalse(all(tag in card.tags for tag in ["bug"]))

    def test_other_non_list_tags_values_coerce_to_empty(self) -> None:
        for bad in (None, "bug", 42, {"not": "a list"}):
            with self.subTest(bad=bad):
                card = _card("a", tags=bad)
                self.assertEqual(card.tags, [])

    def test_list_tags_pass_through_unchanged(self) -> None:
        card = _card("a", tags=["bug", "api-contract"])
        self.assertEqual(card.tags, ["bug", "api-contract"])


class SupersedesWalkersGuardTest(unittest.TestCase):
    """Three engine walkers — `validate_supersedes_targets`,
    `detect_supersedes_cycles`, and `_would_create_supersedes_cycle` — must
    treat a non-list `supersedes` / `superseded_by` frontmatter value as
    structurally absent rather than iterating it character-by-character.
    Same root-cause family as the advances/tags guards above."""

    def test_validate_supersedes_targets_flags_bare_string_supersedes(self) -> None:
        # Card `a` has `supersedes: "nonexistent"` (bare string). Card `n`
        # has the single-character title that the buggy char-by-char walk
        # would silently match against. Post-fix: the validator reports
        # the bare-string shape with its value, naming 'nonexistent'.
        a = _card("a", supersedes="nonexistent")
        n = _card("n")
        n.frontmatter["status"] = "superseded"
        errors = engine.validate_supersedes_targets([a, n])
        self.assertTrue(
            any("nonexistent" in e for e in errors),
            f"expected bare-string value reported; got {errors!r}",
        )
        self.assertTrue(
            any("must be a list" in e for e in errors),
            f"expected list-shape error; got {errors!r}",
        )

    def test_validate_supersedes_targets_list_pass_through_unchanged(self) -> None:
        # Proper list shape with a dangling target that exists but isn't
        # `status: superseded` still reports the original integrity error.
        a = _card("a", supersedes=["b"])
        b = _card("b")  # status: open, not superseded
        errors = engine.validate_supersedes_targets([a, b])
        self.assertTrue(
            any("not status: superseded" in e for e in errors),
            f"expected typed-pointer integrity error; got {errors!r}",
        )

    def test_detect_supersedes_cycles_ignores_non_list_superseded_by(self) -> None:
        # Bare-string `superseded_by` must not crash or emit a spurious
        # cycle from char-by-char iteration.
        card = _card("a", superseded_by="abc")
        errors = engine.detect_supersedes_cycles([card])
        self.assertEqual(errors, [])

    def test_would_create_supersedes_cycle_ignores_non_list_superseded_by(self) -> None:
        # _would_create_supersedes_cycle walks `superseded_by` from the
        # successor; a bare-string value must be treated as no outgoing
        # edges, not as a sequence of single-character successors.
        a = _card("a")
        b = _card("b", superseded_by="aaa")
        self.assertFalse(
            engine._would_create_supersedes_cycle([a, b], "a", "b")
        )


class DependencyBlockersGuardTest(unittest.TestCase):
    """Four read-time consumers walk `advanced_by` / `advances` outside the
    `goc validate` gate: `dependency_blockers`, the `live_direct` closure
    inside `sort_default`, the `_run_derived_check` `advanced-by-closed`
    branch, and `validate_blocker_coherence`'s `unblocks` builder. Each must
    treat a non-list value as an empty edge set, matching `compute_values`
    and the supersession cycle walkers. Two `status: blocked`-only sites
    (the over-broad-epic detector and the blocker enumerator) receive the
    same guard for consistency."""

    def test_dependency_blockers_treats_bare_string_advanced_by_as_empty(self) -> None:
        victim = _card("victim", advanced_by="abc")
        self.assertEqual(engine.dependency_blockers(victim, by_title={}), [])
        self.assertFalse(engine.dependency_blocked(victim, by_title={}))

    def test_dependency_blockers_handles_other_non_list_shapes(self) -> None:
        for bad in (None, "abc", 42, {"not": "a list"}):
            with self.subTest(bad=bad):
                victim = _card("victim", advanced_by=bad)
                self.assertEqual(engine.dependency_blockers(victim, by_title={}), [])

    def test_sort_default_live_direct_ignores_bare_string_advances(self) -> None:
        # `live_direct` is the tiebreak counter inside `sort_default`. A
        # bare-string `advances` must not inflate the count via phantom
        # single-character matches against deck-resident titles.
        a = _card("a", advances="bc")
        b = _card("b")
        c = _card("c")
        # Sort is stable on ties; the assertion is that `a` does not get
        # bumped above `b`/`c` because of phantom live-edge counts.
        cards = engine.sort_default([a, b, c])
        # All three cards have the same value (no live edges) and same
        # created timestamp; the original list order is preserved.
        self.assertEqual([t.title for t in cards], ["a", "b", "c"])

    def test_run_derived_check_treats_bare_string_advanced_by_as_no_edges(self) -> None:
        # The `advanced-by-closed` derived check gates `goc done`. A
        # bare-string `advanced_by` must not silently pass via Python's
        # truthy-non-empty-string + character-by-character walk.
        victim = _card("victim", advanced_by="abc")
        ok, detail = engine._run_derived_check(
            {"name": "advanced-by-closed"}, victim, [victim], today="2026-05-29"
        )
        self.assertTrue(ok)
        self.assertIn("no advanced_by edges", detail)

    def test_validate_blocker_coherence_ignores_bare_string_advanced_by(self) -> None:
        # The `unblocks` reverse-adjacency builder iterates every card's
        # `advanced_by`. A bare-string value must not register phantom
        # single-character edges; the function must produce no warnings
        # for a deck where the only edge is bogus.
        a = _card("a", advanced_by="abc")
        warnings = engine.validate_blocker_coherence([a])
        self.assertEqual(warnings, [])

    def test_validate_epic_edge_direction_ignores_bare_string_advances(self) -> None:
        # The over-broad-epic detector iterates `advances`. A bare-string
        # value must produce no warnings from phantom single-character
        # resolved-target matches.
        a = _card("a", advances="bc")
        b = _card("b")
        c = _card("c")
        warnings = engine.validate_epic_edge_direction([a, b, c])
        self.assertEqual(warnings, [])


class FilterCardsEdgeGuardTest(unittest.TestCase):
    """`filter_cards` implements the public `goc --advances <title>` /
    `goc --advanced-by <title>` CLI surface. The two `in` membership
    tests must treat a non-list edge value as an empty edge set,
    matching the rest of the walker-fix family — otherwise Python's
    `in` silently switches to substring-matching on a bare-string
    scalar."""

    def test_advances_filter_treats_bare_string_as_no_membership(self) -> None:
        scalar = _card("scalar-card", advances="foo-card-extended")
        list_c = _card("list-card", advances=["foo-card-extended"])
        # Substring query that is NOT a real title: bare-string scalar
        # used to false-positive via Python substring `in`.
        self.assertEqual(
            engine.filter_cards(
                [scalar, list_c], status=None, advances="foo"
            ),
            [],
        )
        # Full-title query: only the list-shaped card matches; the
        # scalar shape is treated as structurally absent.
        match = engine.filter_cards(
            [scalar, list_c], status=None, advances="foo-card-extended"
        )
        self.assertEqual([c.title for c in match], ["list-card"])

    def test_advanced_by_filter_treats_bare_string_as_no_membership(self) -> None:
        scalar = _card("scalar-card", advanced_by="foo-card-extended")
        list_c = _card("list-card", advanced_by=["foo-card-extended"])
        self.assertEqual(
            engine.filter_cards(
                [scalar, list_c], status=None, advanced_by="foo"
            ),
            [],
        )
        match = engine.filter_cards(
            [scalar, list_c], status=None, advanced_by="foo-card-extended"
        )
        self.assertEqual([c.title for c in match], ["list-card"])

    def test_other_non_list_edge_shapes_coerce_to_empty(self) -> None:
        for bad in (None, "abc", 42, {"not": "a list"}):
            with self.subTest(bad=bad):
                card = _card("a", advances=bad, advanced_by=bad)
                self.assertEqual(
                    engine.filter_cards([card], status=None, advances="a"),
                    [],
                )
                self.assertEqual(
                    engine.filter_cards([card], status=None, advanced_by="a"),
                    [],
                )


if __name__ == "__main__":
    unittest.main()
