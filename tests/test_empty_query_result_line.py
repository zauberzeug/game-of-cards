"""A zero-match queue query must say so — regression guard for
`empty-queue-view-prints-nothing-instead-of-saying-no-cards-match`.

`render_table` returns "" for an empty card list and `_cmd_default` used to
drop the print entirely, so the table view was the one read surface that could
not express "the query ran and matched nothing". Three states rendered
byte-identically at exit 0: a genuinely drained `--ready` queue, a status
filter no card satisfies, and a mistyped `--worker` value — the last of which
input validation cannot catch, because `worker` is deliberately unregistered.

The non-empty case is asserted in the same tests as the empty one so the two
shapes cannot drift, and `--json` / `--board` are pinned unchanged: a prose
line leaking into either would break a machine-readable or grid consumer.
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from goc import engine  # noqa: E402

CARD = """---
title: {title}
summary: "Summary for {title}."
status: {status}
stage: null
contribution: medium
created: "2026-08-01T00:00:00Z"
closed_at: null
human_gate: {gate}
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: something
---

# {title}
"""


class _Args:
    """Stand-in for the argparse namespace `_cmd_default` reads."""

    def __init__(self, **kw):
        defaults = dict(
            done_flag=False, status_flag=None, closed_since=None, waiting=False,
            board=False, as_json=False, slim=False, since=None, stage_flag=None,
            contribution=None, human_gate=None, tags=[], advances=None,
            advanced_by=None, worker=None, ready=False, verbose=0,
            no_color=True, max_rows=20,
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


def _render(**kw) -> str:
    """Run `_cmd_default` against the active `engine.DECK_DIR` and capture stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        engine._cmd_default(_Args(**kw))
    return buf.getvalue()


class EmptyQueryResultLineTest(unittest.TestCase):
    """The table path states an empty result, and names what it filtered on."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        deck = Path(self._tmp.name) / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        # Every card is gate-parked, so `--ready` is legitimately empty while
        # the plain open queue is not — the two halves of each assertion.
        for title in ("alpha", "beta"):
            card = deck / title
            card.mkdir()
            (card / "README.md").write_text(
                CARD.format(title=title, status="open", gate="decision")
            )
        self._prev = engine.DECK_DIR
        engine.DECK_DIR = deck
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        engine.DECK_DIR = self._prev
        self._tmp.cleanup()

    _run = staticmethod(_render)

    def test_drained_ready_queue_says_so(self) -> None:
        out = self._run(ready=True)
        self.assertIn("No cards match", out)
        self.assertIn("ready: status open, gate none, no active impediment", out)

    def test_zero_match_status_filter_says_so(self) -> None:
        out = self._run(status_flag="disproved")
        self.assertIn("No cards match (status: disproved).", out)

    def test_non_empty_query_renders_the_table_and_no_message(self) -> None:
        """The other half of the contract: a real result is untouched."""
        out = self._run()
        self.assertIn("alpha", out)
        self.assertIn("beta", out)
        self.assertIn("TITLE", out)
        self.assertNotIn("No cards match", out)

    def test_unmatched_worker_is_distinguishable_from_a_drained_queue(self) -> None:
        """`worker` is unregistered, so echoing the value is the only signal.

        Without this the two states are byte-identical and a typo in
        `GOC_WORKER` reads exactly like an empty queue.
        """
        drained = self._run(ready=True)
        typo = self._run(ready=True, worker="no-such-worker")
        self.assertNotEqual(drained, typo)
        self.assertIn("worker: 'no-such-worker'", typo)

    def test_every_active_filter_is_named(self) -> None:
        out = self._run(
            status_flag="done", stage_flag="alpha", contribution="high",
            human_gate="session", tags=["bug", "infra"], since="2026-01-01",
            advances="alpha", advanced_by="beta", worker="rodja",
        )
        for fragment in (
            "status: done", "stage: alpha", "contribution: high", "gate: session",
            "tag: bug, infra", "since: 2026-01-01", "advances: alpha",
            "advanced-by: beta", "worker: 'rodja'",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, out)

    def test_json_path_still_emits_exactly_an_empty_array(self) -> None:
        """The message must not leak into the machine-readable surface."""
        out = self._run(status_flag="disproved", as_json=True)
        self.assertEqual(out.strip(), "[]")
        self.assertNotIn("No cards match", out)

    def test_board_path_still_emits_only_its_header(self) -> None:
        out = self._run(status_flag="disproved", board=True)
        self.assertIn("OPEN", out)
        self.assertNotIn("No cards match", out)

    def test_render_table_still_returns_empty_string(self) -> None:
        """The message belongs to the command, not the renderer.

        Pins where the fix lives: any caller of `render_table` other than
        `_cmd_default` must keep getting "" for an empty list.
        """
        self.assertEqual(engine.render_table([], verbose=0, no_color=True), "")


class ReadyPlusExplicitStatusTest(unittest.TestCase):
    """`--ready` ADDS a conjunct — it must not hide an explicit `--status`.

    Regression guard for
    `empty-result-line-reports-a-drained-ready-queue-that-still-has-cards`.
    `filter_cards` applies `--ready` and the status filter independently, and
    `card_is_ready` requires `status == open`, so pairing `--ready` with any
    other status is unsatisfiable. `render_empty_query_line` used to treat
    `--ready` as *replacing* the status clause, so the one filter that emptied
    the result was the one filter the message omitted.

    The deck here holds a genuinely pullable card, which is what makes the old
    output a *false* statement rather than an incomplete one: it asserted the
    ready predicate matched nothing while that predicate matched `pullable`.
    The sibling class above cannot catch this — its every card is gate-parked,
    so a claim of "drained" is true there whatever the message omits.
    """

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        deck = Path(self._tmp.name) / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        card = deck / "pullable"
        card.mkdir()
        (card / "README.md").write_text(
            CARD.format(title="pullable", status="open", gate="none")
        )
        self._prev = engine.DECK_DIR
        engine.DECK_DIR = deck
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        engine.DECK_DIR = self._prev
        self._tmp.cleanup()

    _run = staticmethod(_render)

    def test_the_ready_queue_is_not_actually_drained(self) -> None:
        """Discriminator: without this the rest of the class proves nothing."""
        out = self._run(ready=True)
        self.assertIn("pullable", out)
        self.assertNotIn("No cards match", out)

    def test_contradictory_status_filter_is_named(self) -> None:
        out = self._run(ready=True, status_flag="done")
        self.assertIn("ready: status open, gate none, no active impediment", out)
        self.assertIn("status: done", out)

    def test_done_shortcut_is_named(self) -> None:
        """`--done` reaches the same resolved status by a different flag."""
        out = self._run(ready=True, done_flag=True)
        self.assertIn("status: done", out)

    def test_plain_ready_gains_no_redundant_status_clause(self) -> None:
        """The auto-resolved default must stay unnamed.

        With no explicit `--status`, `status` is the `"open"` default that the
        ready sentence already covers, so repeating it would be noise. Drained
        here via `--gate session`, which no card in this deck satisfies.
        """
        out = self._run(ready=True, human_gate="session")
        self.assertIn("No cards match", out)
        self.assertIn("gate: session", out)
        self.assertNotIn("status: open", out)


class HiddenDraftConjunctTest(unittest.TestCase):
    """The draft exclusion is a conjunct too — and the only one no flag reveals.

    Regression guard for
    `empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card`.
    `filter_cards` drops unauthored scaffolds from every status filter but
    `all`, with nothing on the command line asking it to, so a deck whose only
    open cards are the ones `goc new` just wrote printed the drained-deck
    sentence verbatim — `install → new → goc`, the shortest path through the
    tool, ending in "nothing here".

    The count is the point: an unconditional "excludes drafts" clause would
    still render identically on a genuinely empty deck, which is the exact
    collapse this whole surface exists to undo. So the clause must appear with
    a number when drafts were dropped, and must NOT appear otherwise.
    """

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._prev = engine.DECK_DIR
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        engine.DECK_DIR = self._prev
        self._tmp.cleanup()

    def _deck(self, name: str, cards: dict[str, dict]) -> None:
        """Point the engine at a fresh deck of `{title: {status, gate, draft}}`."""
        deck = self._root / name / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for title, spec in cards.items():
            card = deck / title
            card.mkdir()
            text = CARD.format(
                title=title,
                status=spec.get("status", "open"),
                gate=spec.get("gate", "none"),
            )
            if spec.get("draft"):
                text = text.replace("tags: [bug]\n", "tags: [bug]\ndraft: true\n")
            (card / "README.md").write_text(text)
        engine.DECK_DIR = deck

    _run = staticmethod(_render)

    def test_a_deck_of_scaffolds_does_not_read_as_a_drained_deck(self) -> None:
        self._deck("empty", {})
        drained = self._run()
        self._deck("drafts", {
            "alpha": {"draft": True},
            "beta": {"draft": True},
        })
        with_drafts = self._run()

        self.assertNotEqual(
            drained, with_drafts,
            msg="a deck of unauthored scaffolds still prints the drained-deck sentence",
        )
        self.assertIn("2 unauthored draft scaffolds hidden", with_drafts)
        self.assertIn("goc publish", with_drafts)

    def test_the_count_is_singular_for_one_scaffold(self) -> None:
        self._deck("one", {"alpha": {"draft": True}})
        out = self._run()
        self.assertIn("1 unauthored draft scaffold hidden", out)
        self.assertNotIn("scaffolds", out)

    def test_a_genuinely_empty_deck_gains_no_draft_clause(self) -> None:
        """The discriminator: the clause is evidence, not decoration."""
        self._deck("empty", {})
        out = self._run()
        self.assertIn("No cards match (status: open).", out)
        self.assertNotIn("draft", out)

    def test_a_user_filter_that_no_draft_satisfies_gains_no_clause(self) -> None:
        """Drafts dropped by the *rest* of the predicate are not "hidden by draft".

        `--tag infra` matches neither draft, so the draft exclusion removed
        nothing from this query and claiming otherwise would misattribute the
        empty result.
        """
        self._deck("drafts", {"alpha": {"draft": True}})
        out = self._run(tags=["infra"])
        self.assertIn("tag: infra", out)
        self.assertNotIn("draft", out)

    def test_status_all_gains_no_clause_because_it_hides_nothing(self) -> None:
        """`--status all` does not exclude drafts, so none were hidden."""
        self._deck("drafts", {"alpha": {"draft": True}})
        out = self._run(status_flag="all", contribution="high")
        self.assertIn("No cards match", out)
        self.assertNotIn("draft", out)

    def test_ready_queue_names_hidden_scaffolds_too(self) -> None:
        """`--ready` is the pull-card/next-card surface — the costly one.

        `card_is_ready` drops drafts on its own axis, so naming the conjunct in
        `filter_cards` alone would leave the autonomous path still reading a
        deck of scaffolds as a drained queue.
        """
        self._deck("drafts", {"alpha": {"draft": True, "gate": "none"}})
        out = self._run(ready=True)
        self.assertIn("ready: status open, gate none, no active impediment", out)
        self.assertIn("1 unauthored draft scaffold hidden", out)

    def test_gate_parked_scaffold_is_not_counted_against_the_ready_queue(self) -> None:
        """The gate, not the draft flag, is why `--ready` is empty here."""
        self._deck("parked", {"alpha": {"draft": True, "gate": "decision"}})
        out = self._run(ready=True)
        self.assertIn("No cards match", out)
        self.assertNotIn("draft", out)

    def test_a_visible_card_suppresses_the_message_entirely(self) -> None:
        """Non-empty results are untouched — the clause rides the empty path."""
        self._deck("mixed", {
            "alpha": {"draft": True},
            "visible": {},
        })
        out = self._run()
        self.assertIn("visible", out)
        self.assertNotIn("No cards match", out)
        self.assertNotIn("alpha", out)

    def test_json_and_board_paths_stay_free_of_the_clause(self) -> None:
        self._deck("drafts", {"alpha": {"draft": True}})
        as_json = self._run(as_json=True)
        self.assertEqual(as_json.strip(), "[]")
        board = self._run(board=True)
        self.assertNotIn("unauthored draft scaffold", board)

    def test_card_is_ready_still_rejects_drafts_by_default(self) -> None:
        """The suppression flag is opt-in; readiness itself did not change."""
        self._deck("drafts", {"alpha": {"draft": True, "gate": "none"}})
        card = engine.load_all_cards()[0]
        lookup = {card.title: card}
        self.assertTrue(engine.card_is_draft(card))
        self.assertFalse(engine.card_is_ready(card, lookup))
        self.assertTrue(engine.card_is_ready(card, lookup, include_drafts=True))


if __name__ == "__main__":
    unittest.main()
