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

    @staticmethod
    def _run(**kw) -> str:
        buf = io.StringIO()
        with redirect_stdout(buf):
            engine._cmd_default(_Args(**kw))
        return buf.getvalue()

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


if __name__ == "__main__":
    unittest.main()
