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


OVERLAY_CARD = """---
title: {title}
summary: "Summary for {title}."
status: {status}
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
tags: [bug]
{extra}definition_of_done: |
  - [ ] TDD: something
---

# {title}
"""


class HiddenDraftCountSpansTheWholeQueryTest(unittest.TestCase):
    """The count must reflect the whole query, not just its first stage.

    Regression guard for
    `zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface`.
    `_cmd_default` narrows in three stages — `filter_cards`, the
    `--closed-since` window, then `--waiting`'s `live_impeded` gate — but the
    recount replayed only the first, so it answered "what would `filter_cards`
    have matched with drafts included?" instead of "what would this query have
    matched?". Drafts the other two conjuncts rejected on their own merits were
    reported as withheld by the draft flag, and the clause told the reader to
    run `goc publish` to reveal something that would still not appear.

    Each conjunct is pinned in BOTH directions. Suppressing the clause under
    `--waiting` / `--closed-since` wholesale would pass the false-positive
    halves while silently deleting the surface the predecessor card built, so
    the true-positive halves — a draft those queries really are hiding — are
    what make the guard discriminate rather than just go quiet.
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
        """Deck of `{title: {status, closed_at, waiting_on, draft}}`.

        Every card is authored (real DoD and body inherited from the template)
        so `card_is_draft` fires on the explicit flag alone — the placeholder
        half of that predicate would confound what is being measured here.
        """
        deck = self._root / name / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for title, spec in cards.items():
            card = deck / title
            card.mkdir()
            extra = ""
            if spec.get("waiting_on"):
                extra += f"waiting_on: {spec['waiting_on']}\n"
            if spec.get("draft", True):
                extra += "draft: true\n"
            (card / "README.md").write_text(OVERLAY_CARD.format(
                title=title,
                status=spec.get("status", "open"),
                closed_at=spec.get("closed_at", "null"),
                extra=extra,
            ))
        engine.DECK_DIR = deck

    _run = staticmethod(_render)

    CLAUSE = "unauthored draft scaffold"

    @staticmethod
    def _stamp(hours_ago: int) -> str:
        from datetime import datetime, timedelta, timezone
        moment = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
        return f'"{moment.strftime("%Y-%m-%dT%H:%M:%SZ")}"'

    # ---- --waiting -------------------------------------------------------

    def test_draft_without_an_overlay_is_not_counted_under_waiting(self) -> None:
        """Publishing it reveals nothing: `--waiting` wants an active overlay."""
        self._deck("no-overlay", {"alpha": {}})
        out = self._run(waiting=True, status_flag="open")
        self.assertIn("waiting: active impediment overlay", out)
        self.assertNotIn(self.CLAUSE, out)

    def test_actively_impeded_draft_is_still_counted_under_waiting(self) -> None:
        """The true positive: here the draft flag IS the only thing hiding it."""
        self._deck("impeded", {"alpha": {"waiting_on": "external"}})
        out = self._run(waiting=True, status_flag="open")
        self.assertIn("1 unauthored draft scaffold hidden", out)
        self.assertIn("goc publish", out)

    def test_the_two_waiting_shapes_do_not_render_identically(self) -> None:
        """The collapse itself — opposite situations, byte-identical sentence."""
        self._deck("no-overlay", {"alpha": {}})
        without = self._run(waiting=True, status_flag="open")
        self._deck("impeded", {"alpha": {"waiting_on": "external"}})
        impeded = self._run(waiting=True, status_flag="open")
        self.assertNotEqual(without, impeded)

    # ---- --closed-since --------------------------------------------------

    def test_draft_outside_the_closed_since_window_is_not_counted(self) -> None:
        """Publishing it reveals nothing: it closed long before the window."""
        self._deck("stale", {
            "alpha": {"status": "done", "closed_at": '"2026-01-02T00:00:00Z"'},
        })
        out = self._run(closed_since="1h", status_flag="done")
        self.assertIn("closed-since: 1h", out)
        self.assertNotIn(self.CLAUSE, out)

    def test_draft_inside_the_closed_since_window_is_still_counted(self) -> None:
        """The true positive for the window conjunct."""
        self._deck("fresh", {
            "alpha": {"status": "done", "closed_at": self._stamp(1)},
        })
        out = self._run(closed_since="30d", status_flag="done")
        self.assertIn("1 unauthored draft scaffold hidden", out)

    # ---- the helper the counterfactual needs -----------------------------

    def test_live_impeded_still_rejects_drafts_by_default(self) -> None:
        """The suppression flag is opt-in; what counts as impeded is unchanged.

        Mirrors `card_is_ready`'s pin one class up. `live_impeded` is the third
        and last axis the draft gate is inlined on, and the one the recount
        could not see past — but only the recount passes the flag.
        """
        self._deck("impeded", {"alpha": {"waiting_on": "external"}})
        card = engine.load_all_cards()[0]
        self.assertTrue(engine.card_is_draft(card))
        self.assertFalse(engine.live_impeded(card))
        self.assertTrue(engine.live_impeded(card, include_drafts=True))

    def test_include_drafts_does_not_widen_the_other_conjuncts(self) -> None:
        """It suppresses the draft clause alone — terminal and overlay hold.

        A closed card carries its overlay forever, and a card with no overlay
        was never impeded; neither becomes impeded just because the caller
        stopped caring about the draft flag.
        """
        self._deck("mixed", {
            "closed": {
                "status": "done", "closed_at": '"2026-01-02T00:00:00Z"',
                "waiting_on": "external",
            },
            "unimpeded": {},
        })
        by_title = {c.title: c for c in engine.load_all_cards()}
        self.assertFalse(
            engine.live_impeded(by_title["closed"], include_drafts=True),
            msg="a terminal card's stale overlay is not an active impediment",
        )
        self.assertFalse(
            engine.live_impeded(by_title["unimpeded"], include_drafts=True),
            msg="a card with no overlay is not impeded",
        )


class HiddenDraftCountSurvivesStatusAllTest(unittest.TestCase):
    """Widening the status filter to `all` must not delete a true clause.

    Regression guard for
    `zero-match-line-omits-hidden-drafts-whenever-the-status-filter-is-all`.
    The recount used to be skipped whenever `status == "all"`, on the premise
    that `--status all` does not exclude drafts. That holds for `filter_cards`
    and for nothing else: `card_is_ready` and `live_impeded` drop drafts
    without consulting the status filter at all. And `--waiting` /
    `--closed-since` / `--board` auto-extend an UNSET `--status` to `all`, so
    the flagless `goc --waiting` — the impediment review surface — took the
    skipped branch every time.

    Every case in the sibling class above passes `status_flag="open"`
    explicitly, which is exactly why this survived that card. These cases
    leave the status filter where the command line really leaves it, and pair
    each one against the `--status open` rendering of the same deck: widening
    a filter cannot make a hidden card less hidden, so the two must agree.
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
        """Deck of `{title: {status, closed_at, waiting_on, draft}}`."""
        deck = self._root / name / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for title, spec in cards.items():
            card = deck / title
            card.mkdir()
            extra = ""
            if spec.get("waiting_on"):
                extra += f"waiting_on: {spec['waiting_on']}\n"
            if spec.get("draft", True):
                extra += "draft: true\n"
            (card / "README.md").write_text(OVERLAY_CARD.format(
                title=title,
                status=spec.get("status", "open"),
                closed_at=spec.get("closed_at", "null"),
                extra=extra,
            ))
        engine.DECK_DIR = deck

    _run = staticmethod(_render)

    CLAUSE = "1 unauthored draft scaffold hidden"

    def test_flagless_waiting_names_the_scaffold_it_is_hiding(self) -> None:
        """`goc --waiting` with no `--status` — the shape that resolves to all."""
        self._deck("impeded", {"alpha": {"waiting_on": "external"}})
        out = self._run(waiting=True)
        self.assertIn("waiting: active impediment overlay", out)
        self.assertIn(self.CLAUSE, out)
        self.assertIn("goc publish", out)

    def test_widening_to_all_does_not_change_what_waiting_reports(self) -> None:
        """The discriminator: same deck, same query, one extra flag."""
        self._deck("impeded", {"alpha": {"waiting_on": "external"}})
        explicit_open = self._run(waiting=True, status_flag="open")
        explicit_all = self._run(waiting=True, status_flag="all")
        self.assertIn(self.CLAUSE, explicit_open)
        self.assertIn(self.CLAUSE, explicit_all)

    def test_ready_at_status_all_names_the_scaffold_too(self) -> None:
        """`--ready`'s draft conjunct lives in `card_is_ready`, not the status."""
        self._deck("queueable", {"alpha": {}})
        plain = self._run(ready=True)
        widened = self._run(ready=True, status_flag="all")
        self.assertIn(self.CLAUSE, plain)
        self.assertIn("status: all", widened)
        self.assertIn(self.CLAUSE, widened)

    def test_all_still_gains_no_clause_when_no_stage_hides_the_draft(self) -> None:
        """The true negative — the fix is not "always count under `all`".

        Without `--waiting` or `--ready`, `--status all` really does list
        drafts, so an empty result there was emptied by something else and
        publishing would reveal nothing.
        """
        self._deck("visible-draft", {"alpha": {}})
        out = self._run(status_flag="all", contribution="high")
        self.assertIn("No cards match", out)
        self.assertNotIn("draft", out)

    def test_unimpeded_draft_is_still_not_counted_under_flagless_waiting(self) -> None:
        """The other true negative, on the very query the guard used to skip.

        `--waiting` wants an active overlay; this draft has none, so publishing
        it would not put it in this result either.
        """
        self._deck("no-overlay", {"alpha": {}})
        out = self._run(waiting=True)
        self.assertIn("waiting: active impediment overlay", out)
        self.assertNotIn("draft", out)

    def test_the_two_flagless_waiting_shapes_do_not_render_identically(self) -> None:
        """The collapse itself, on the default invocation."""
        self._deck("no-overlay", {"alpha": {}})
        without = self._run(waiting=True)
        self._deck("impeded", {"alpha": {"waiting_on": "external"}})
        impeded = self._run(waiting=True)
        self.assertNotEqual(without, impeded)


if __name__ == "__main__":
    unittest.main()
