"""`goc triage`'s zero-match line must name what emptied it — regression guard
for `triage-empty-line-omits-the-worker-filter-and-hidden-drafts-it-dropped`.

`_cmd_triage` selects on four conjuncts — `status == "open"`,
`human_gate != "none"`, `not card_is_draft`, and an optional `--worker`
substring — but reported a zero match with the constant
`No parked cards (gate ≠ none).`, naming only the second. Three unrelated deck
states then rendered byte-identically on the surface a human reads to decide
whether any card is waiting on them: an empty park queue, a mistyped `--worker`
value, and a deck whose parked cards are all unauthored `goc new` scaffolds.

The hidden-draft count is asserted worker-SCOPED in both directions, because
the queue line's own history has a defect on each side: leaving the count out
hides cards `goc publish` would surface here
(`empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card`),
and counting drafts the other filters exclude promises cards publishing would
not surface (`zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface`).

The non-empty render is pinned in the same class as the empty one so the two
shapes cannot drift, and `--json` is pinned to exactly `[]`: a prose line
leaking there would break a machine-readable consumer.
"""

from __future__ import annotations

import io
import json
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
worker: {worker}
draft: {draft}
definition_of_done: |
  - [ ] TDD: {dod}
---

# {title}

{body}
"""


class _Args:
    """Stand-in for the argparse namespace `_cmd_triage` reads."""

    def __init__(self, **kw):
        defaults = dict(as_json=False, worker=None)
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


class _DeckCase(unittest.TestCase):
    """Base: build a throwaway deck, point the engine at it, capture stdout."""

    #: (title, worker, draft) per card; `status`/`gate` default to parked.
    cards: tuple = ()

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        deck = Path(self._tmp.name) / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for spec in self.cards:
            title, worker, draft = spec[0], spec[1], spec[2]
            status = spec[3] if len(spec) > 3 else "open"
            gate = spec[4] if len(spec) > 4 else "decision"
            authored = draft == "false"
            card = deck / title
            card.mkdir()
            (card / "README.md").write_text(
                CARD.format(
                    title=title, status=status, gate=gate, worker=worker, draft=draft,
                    dod="real criteria" if authored else "(replace with real criteria)",
                    body="Authored body." if authored else "(write the design doc here)",
                )
            )
            (card / "log.md").write_text("")
        self._prev = engine.DECK_DIR
        engine.DECK_DIR = deck
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        engine.DECK_DIR = self._prev
        self._tmp.cleanup()

    def _run(self, **kw) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            engine._cmd_triage(_Args(**kw))
        return buf.getvalue()


class TriageEmptyLineNamesItsFiltersTest(_DeckCase):
    """One authored parked card and one draft, both `worker: rodja`."""

    cards = (
        ("authored-card", "rodja", "false"),
        ("draft-card", "rodja", "true"),
    )

    def test_non_empty_triage_render_is_unchanged(self) -> None:
        """The other half of the contract: a real result is untouched."""
        out = self._run()
        self.assertIn("## Waiting on you (gate ≠ none) — 1 card", out)
        self.assertIn("authored-card", out)
        self.assertNotIn("draft-card", out)
        self.assertNotIn("No parked cards", out)

    def test_unmatched_worker_is_distinguishable_from_an_empty_park_queue(self) -> None:
        """`worker` is unregistered, so echoing the value is the only signal.

        Nothing rejects a typo at parse time — any person slug, machine name or
        capability tag is legal — so without the echo, `goc triage --worker
        $GOC_WORKER` on a misspelled identity reads exactly like "nothing is
        waiting on you".
        """
        out = self._run(worker="nobdy")
        self.assertIn("No parked cards", out)
        self.assertIn("worker: 'nobdy'", out)

    def test_unmatched_worker_claims_no_draft_the_filter_also_excludes(self) -> None:
        """The count is worker-scoped: `goc publish` here would surface nothing.

        The only draft is `worker: rodja`, which `--worker nobdy` excludes on
        its own. Naming it would promise a card publishing would not put in
        this view — the queue line's
        `zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface`
        defect, on this surface.
        """
        out = self._run(worker="nobdy")
        self.assertNotIn("draft", out.lower())

    def test_the_status_open_conjunct_is_named(self) -> None:
        """Triage drops cards parked at `active`; the line has to say `open`.

        Whether it *should* drop them is the open question tracked by
        `parked-active-cards-are-missing-from-goc-triage`. Until that is
        decided, naming the conjunct is what makes the behaviour legible.
        """
        self.assertIn("status: open", self._run(worker="nobdy"))

    def test_json_path_still_emits_exactly_an_empty_array(self) -> None:
        out = self._run(as_json=True, worker="nobdy")
        self.assertEqual([], json.loads(out))
        self.assertNotIn("No parked cards", out)


class TriageEmptyLineCountsHiddenDraftsTest(_DeckCase):
    """Every parked card is an unauthored `goc new` scaffold."""

    cards = (
        ("first-scaffold", "rodja", "true"),
        ("second-scaffold", "rodja", "true"),
    )

    def test_drafts_only_deck_reports_the_count_not_a_drained_queue(self) -> None:
        """The shortest path through the tool must not end in a false negative.

        `goc new --gate decision` files a card that is parked AND `draft: true`,
        so the very next `goc triage` answered "nothing is waiting on you" about
        the card just filed.
        """
        out = self._run()
        self.assertIn("2 unauthored draft scaffolds hidden", out)
        self.assertIn("goc publish <title>", out)

    def test_matching_worker_still_counts_the_drafts_it_dropped(self) -> None:
        """Worker-scoped in the other direction: these drafts DO match.

        Publishing either one would put a card in this exact view, so the
        `--worker` filter must not suppress the disclosure.
        """
        out = self._run(worker="rodja")
        self.assertIn("worker: 'rodja'", out)
        self.assertIn("2 unauthored draft scaffolds hidden", out)


class TriageEmptyLineScopesTheDraftCountToTheWorkerTest(_DeckCase):
    """Two drafts, two different people — the count follows the filter."""

    cards = (
        ("rodjas-scaffold", "rodja", "true"),
        ("anas-scaffold", "ana", "true"),
    )

    def test_singular_noun_when_one_draft_is_hidden(self) -> None:
        out = self._run(worker="ana")
        self.assertIn("1 unauthored draft scaffold hidden", out)
        self.assertNotIn("scaffolds", out)

    def test_unfiltered_view_counts_both(self) -> None:
        self.assertIn("2 unauthored draft scaffolds hidden", self._run())


class TriageEmptyLineOnADrainedDeckTest(_DeckCase):
    """Nothing is parked at all — the one state that IS "nothing waiting"."""

    cards = (("claimed-card", "rodja", "false", "open", "none"),)

    def test_a_genuinely_empty_park_queue_names_no_draft_clause(self) -> None:
        out = self._run()
        self.assertIn("No parked cards (status: open; gate ≠ none).", out)

    def test_the_three_empty_states_render_differently(self) -> None:
        """The whole point: these must not be byte-identical any more."""
        drained = self._run()
        typo = self._run(worker="nobdy")
        self.assertNotEqual(drained, typo)


class HiddenDraftsClauseSharedWithTheQueueLineTest(unittest.TestCase):
    """Both zero-match surfaces build the draft clause from one helper.

    A reader who learns what the clause means under `goc` must read it the same
    way under `goc triage`, so the count, the noun and the next step live in
    `_hidden_drafts_clause` rather than in two format strings that can drift.
    """

    def test_clause_is_empty_when_no_draft_was_dropped(self) -> None:
        self.assertEqual("", engine._hidden_drafts_clause(0))
        self.assertEqual("", engine._hidden_drafts_clause(-1))

    def test_both_surfaces_emit_the_identical_clause(self) -> None:
        clause = engine._hidden_drafts_clause(3)
        self.assertIn(clause, engine.render_empty_triage_line(None, 3))

        queue_args = type("A", (), {})()
        for k, v in dict(
            ready=False, waiting=False, done_flag=False, status_flag=None,
            stage_flag=None, contribution=None, human_gate=None, since=None,
            closed_since=None, advances=None, advanced_by=None, tags=None, worker=None,
        ).items():
            setattr(queue_args, k, v)
        self.assertIn(clause, engine.render_empty_query_line(queue_args, "open", hidden_drafts=3))


if __name__ == "__main__":
    unittest.main()
