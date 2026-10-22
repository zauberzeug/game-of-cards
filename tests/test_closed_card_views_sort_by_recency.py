"""Regression: closed-card views list the most recently closed card first.

`sort_default` used to order every card by the scheduler key — value, then
live downstream count, then oldest-created — whatever its status. Value is a
scheduler-axis number with no meaning once a card is closed, so the board's
DONE / DISPROVED / SUPERSEDED columns froze on the oldest high-contribution
closures (the row cap then hid every recent one), and `--done` and
`--closed-since` listed the newest closure last. `standup` and
`retrospective` re-sorted the JSON by `closed_at` in Python to work around
it; the board had no such escape hatch.

The fixtures give each terminal status three closures whose contributions
run against their recency (the newest is `low`, the oldest `high`), so the
old value order and the recency order disagree on every row. See
`.game-of-cards/deck/board-done-column-and-closed-views-sort-by-scheduler-value-hiding-recent-closures/`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import Card, TERMINAL_STATUSES, sort_default  # noqa: E402

# (suffix, contribution, closed_at) oldest first; the board and the tables
# must list them in the reverse order.
CLOSURES = [
    ("old-high", "high", "2026-05-01"),
    ("mid-medium", "medium", "2026-06-01T09:00:00Z"),
    ("new-low", "low", "2026-07-01T10:00:00Z"),
]
NEWEST_FIRST = [suffix for suffix, _, _ in reversed(CLOSURES)]


def _card(title: str, status: str, contribution: str, closed_at=None,
          created: str = "2026-04-01T00:00:00Z") -> Card:
    return Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter={
            "title": title,
            "status": status,
            "contribution": contribution,
            "human_gate": "none",
            "advances": [],
            "advanced_by": [],
            "created": created,
            "closed_at": closed_at,
        },
        body="",
        dod_open=0,
        dod_done=1,
    )


class SortDefaultClosedOrderTest(unittest.TestCase):
    def test_terminal_cards_sort_most_recently_closed_first(self) -> None:
        cards = [_card(f"done-{s}", "done", c, closed) for s, c, closed in CLOSURES]
        self.assertEqual(
            [t.title for t in sort_default(cards)],
            [f"done-{s}" for s in NEWEST_FIRST],
            "a closed card must rank by closed_at, not by its scheduler value",
        )

    def test_same_instant_ties_break_on_title(self) -> None:
        stamp = "2026-06-01T09:00:00Z"
        cards = [_card(t, "done", c, stamp)
                 for t, c in (("zeta", "high"), ("alpha", "low"), ("mid", "medium"))]
        self.assertEqual([t.title for t in sort_default(cards)], ["alpha", "mid", "zeta"])

    def test_date_only_stamp_reads_as_midnight_utc(self) -> None:
        # A legacy date-only stamp and a datetime on the same day compare on
        # one timeline: midnight sorts before any later instant that day.
        cards = [
            _card("date-only", "done", "high", "2026-06-01"),
            _card("same-day-morning", "done", "low", "2026-06-01T08:00:00Z"),
        ]
        self.assertEqual(
            [t.title for t in sort_default(cards)], ["same-day-morning", "date-only"]
        )

    def test_missing_or_unparseable_closed_at_sorts_last(self) -> None:
        cards = [
            _card("no-stamp", "disproved", "high", None),
            _card("bad-stamp", "disproved", "high", "not-a-date"),
            _card("dated", "disproved", "low", "2020-01-01"),
        ]
        self.assertEqual(
            [t.title for t in sort_default(cards)], ["dated", "bad-stamp", "no-stamp"]
        )

    def test_mixed_set_lists_the_queue_then_the_record(self) -> None:
        # Live cards keep the scheduler order and lead; a closed card never
        # outranks a live one however much value it carries.
        live_high = _card("live-high", "open", "high", created="2026-04-02T00:00:00Z")
        live_low = _card("live-low", "active", "low", created="2026-04-01T00:00:00Z")
        closed = [_card(f"c-{s}", "superseded", c, at) for s, c, at in CLOSURES]
        order = [t.title for t in sort_default([*closed, live_low, live_high])]
        self.assertEqual(order, ["live-high", "live-low", *(f"c-{s}" for s in NEWEST_FIRST)])


class ClosedCardViewsCliTest(unittest.TestCase):
    """The rendered views, through the real CLI and its argument defaults."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = Path(self._tmp.name)
        self.write_card("live-low", "open", "low", None)
        for status in sorted(TERMINAL_STATUSES):
            for suffix, contribution, closed_at in CLOSURES:
                self.write_card(f"{status}-{suffix}", status, contribution, closed_at)

    def write_card(self, title: str, status: str, contribution: str, closed_at) -> None:
        card_dir = self.cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f'summary: "Fixture {title}."\n'
            f"status: {status}\n"
            "stage: null\n"
            f"contribution: {contribution}\n"
            'created: "2026-04-01T00:00:00Z"\n'
            + (f'closed_at: "{closed_at}"\n' if closed_at else "closed_at: null\n")
            + "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] TDD: fixture\n"
            "---\n\n"
            f"# {title}\n"
        )

    def run_goc(self, *args: str) -> str:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env.pop("GOC_WORKER", None)
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=self.cwd, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, result.returncode, msg=result.stderr)
        return result.stdout

    def table_titles(self, *args: str) -> list[str]:
        lines = self.run_goc(*args, "--no-color").splitlines()
        return [line.split()[0] for line in lines[2:] if line.strip()]

    def test_board_terminal_columns_keep_the_newest_closures_under_the_row_cap(self) -> None:
        lines = self.run_goc("--board", "--no-color", "--max-rows", "2").splitlines()
        header = [cell.strip() for cell in lines[0].split(" | ")]
        for status in sorted(TERMINAL_STATUSES):
            with self.subTest(column=status):
                i = header.index(status.upper())
                cells = [
                    row.split(" | ")[i].strip().split(" ")[0]
                    for row in lines[2:]
                ]
                self.assertEqual(
                    [c for c in cells if c],
                    [f"{status}-{s}" for s in NEWEST_FIRST[:2]] + ["…"],
                    f"the {status.upper()} column must show the two newest "
                    "closures and trim the oldest",
                )

    def test_done_table_and_json_lead_with_the_newest_closure(self) -> None:
        expected = [f"done-{s}" for s in NEWEST_FIRST]
        self.assertEqual(self.table_titles("--done"), expected)
        self.assertEqual(
            [c["title"] for c in json.loads(self.run_goc("--done", "--json", "--slim"))],
            expected,
        )

    def test_closed_since_lists_every_terminal_status_newest_first(self) -> None:
        titles = self.table_titles("--closed-since", "2026-05-15")
        # Each status's two closures inside the window, newest first; the
        # same-instant pairs across statuses tie-break on title.
        expected = [
            f"{status}-{suffix}"
            for suffix in NEWEST_FIRST[:2]
            for status in sorted(TERMINAL_STATUSES)
        ]
        self.assertEqual(titles, expected)

    def test_status_all_lists_the_queue_then_every_closure_newest_first(self) -> None:
        # `retrospective` Step 1 keeps the terminal rows of this listing and
        # takes the first N as "the last N closures" without re-sorting.
        titles = [c["title"] for c in json.loads(
            self.run_goc("--status", "all", "--json", "--slim"))]
        expected = ["live-low"] + [
            f"{status}-{suffix}"
            for suffix in NEWEST_FIRST
            for status in sorted(TERMINAL_STATUSES)
        ]
        self.assertEqual(titles, expected)


if __name__ == "__main__":
    unittest.main()
