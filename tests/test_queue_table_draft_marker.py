"""Regression: the queue table marks draft scaffolds, consistently with the
board and the `--json` `draft` field.

`goc --status all` is the one table that lists unauthored scaffolds, and
`Skill(create-card)` dedups against it with `goc --status all | grep`. The
board already suffixed drafts with `✎` and `--json` already carried
`draft: true`, but the table rendered a draft exactly like an authored card
at every verbosity. The table now suffixes the TITLE cell with the board's
glyph (`engine.DRAFT_MARKER`). All three views key it on `card_is_draft`,
so each marks the same cards.

Regression for queue-table-renders-draft-cards-identically-to-authored-ones.
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

from goc import engine  # noqa: E402


MARK = engine.DRAFT_MARKER


def write_card(
    deck: Path,
    title: str,
    *,
    status: str = "open",
    gate: str = "none",
    draft: bool = False,
) -> None:
    closed_at = '"2026-09-01T00:00:00Z"' if status in engine.TERMINAL_STATUSES else "null"
    box = "x" if status == "done" else " "
    (deck / title).mkdir(parents=True)
    (deck / title / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        'summary: "One summary shared by every card."\n'
        f"status: {status}\n"
        "stage: null\n"
        "contribution: medium\n"
        'created: "2026-09-28T00:00:00Z"\n'
        f"closed_at: {closed_at}\n"
        f"human_gate: {gate}\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [story]\n"
        "definition_of_done: |\n"
        f"  - [{box}] TDD: one criterion shared by every card\n"
        + ("draft: true\n" if draft else "")
        + "---\n\n"
        f"# {title}\n\nOne body shared by every card.\n"
    )


def table_title_cell(table: str, title: str) -> str:
    """The TITLE cell of `title`'s row, without its column padding."""
    for line in table.splitlines():
        if line.split(" ", 1)[0] == title:
            return line.split("  ", 1)[0]
    raise AssertionError(f"no table row for {title!r}:\n{table}")


def board_cell(board: str, title: str) -> str:
    for line in board.splitlines():
        for cell in line.split(" | "):
            if cell.strip().split(" ", 1)[0] == title:
                return cell.strip()
    raise AssertionError(f"no board cell for {title!r}:\n{board}")


class QueueTableDraftMarkerCliTest(unittest.TestCase):
    """`goc --status all`, through the real CLI, at every verbosity."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.deck = self.root / ".game-of-cards" / "deck"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def goc(self, *args: str) -> str:
        env = os.environ.copy()
        env.pop("GOC_WORKER", None)
        env["NO_COLOR"] = "1"
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            result.returncode, 0, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        return result.stdout

    def table(self, verbose: int, *args: str) -> str:
        return self.goc("--status", "all", "--no-color", *(["-v"] * verbose), *args)

    def test_draft_title_cell_carries_the_marker_at_every_verbosity(self) -> None:
        write_card(self.deck, "scaffold-card", draft=True)
        write_card(self.deck, "authored-card")
        for verbose in (0, 1, 2):
            with self.subTest(verbose=verbose):
                table = self.table(verbose)
                self.assertEqual(f"scaffold-card {MARK}", table_title_cell(table, "scaffold-card"))
                self.assertEqual("authored-card", table_title_cell(table, "authored-card"))
                authored_row = next(
                    line for line in table.splitlines() if line.startswith("authored-card")
                )
                self.assertNotIn(MARK, authored_row)

    def test_marker_stays_inside_the_title_column(self) -> None:
        # The marker widens the TITLE column instead of pushing the draft's
        # other cells out of line with the header and the authored row.
        write_card(self.deck, "scaffold-card", draft=True)
        write_card(self.deck, "authored-card")
        for verbose in (0, 1, 2):
            with self.subTest(verbose=verbose):
                lines = self.table(verbose).splitlines()
                status_col = lines[0].index("STATUS")
                rows = [line for line in lines if line.split(" ", 1)[0].endswith("-card")]
                self.assertEqual(2, len(rows), msg="\n".join(lines))
                for row in rows:
                    self.assertEqual("open", row[status_col:status_col + 4], msg=row)

    def test_table_board_and_json_mark_the_same_cards(self) -> None:
        write_card(self.deck, "scaffold-card", draft=True)
        write_card(self.deck, "gated-scaffold", gate="decision", draft=True)
        write_card(self.deck, "authored-card")
        write_card(self.deck, "gated-card", gate="decision")
        write_card(self.deck, "claimed-card", status="active")
        write_card(self.deck, "closed-card", status="done")
        flagged = {
            record["title"]: record["draft"]
            for record in json.loads(self.goc("--status", "all", "--json"))
        }
        self.assertEqual({"scaffold-card", "gated-scaffold"}, {t for t, d in flagged.items() if d})
        board = self.goc("--status", "all", "--board", "--no-color")
        for verbose in (0, 1, 2):
            table = self.table(verbose)
            for title, is_draft in flagged.items():
                with self.subTest(verbose=verbose, title=title):
                    self.assertEqual(is_draft, MARK in table_title_cell(table, title))
                    self.assertEqual(is_draft, MARK in board_cell(board, title))

    def test_default_queue_still_hides_drafts(self) -> None:
        # The marker labels drafts where they are listed; it does not list them.
        write_card(self.deck, "scaffold-card", draft=True)
        write_card(self.deck, "authored-card")
        table = self.goc("--no-color")
        self.assertNotIn("scaffold-card", table)
        self.assertNotIn(MARK, table)


class TerminalDraftMarkerTest(unittest.TestCase):
    """A terminal card still flagged `draft: true` is invalid (`goc validate`
    rejects it), but a hand edit can produce one. `--done` hides it as a
    draft, so every view that lists it says so, and the three agree."""

    def card(self, title: str, *, status: str, draft: bool) -> engine.Card:
        fm: dict = {
            "title": title,
            "summary": title,
            "status": status,
            "stage": None,
            "contribution": "medium",
            "created": "2026-09-28",
            "closed_at": "2026-09-30" if status in engine.TERMINAL_STATUSES else None,
            "human_gate": "none",
            "advances": [],
            "advanced_by": [],
            "tags": [],
            "definition_of_done": "- [x] TDD: done\n",
        }
        if draft:
            fm["draft"] = True
        return engine.Card(
            title=title,
            path=Path("/nonexistent") / title,
            frontmatter=fm,
            body=f"\n# {title}\n\nBody.\n",
            dod_open=0,
            dod_done=1,
        )

    def test_every_view_marks_a_terminal_card_still_flagged_draft(self) -> None:
        cards = [
            self.card("stale-draft", status="done", draft=True),
            self.card("clean-close", status="done", draft=False),
        ]
        by_title = {c.title: c for c in cards}
        flagged = {
            r["title"]: r["draft"] for r in json.loads(engine.render_json(cards, by_title=by_title))
        }
        self.assertEqual({"stale-draft": True, "clean-close": False}, flagged)
        table = engine.render_table(cards, verbose=0, no_color=True, by_title=by_title)
        board = engine.render_board(cards, max_rows=20, no_color=True, by_title=by_title)
        for title, is_draft in flagged.items():
            with self.subTest(title=title):
                self.assertEqual(is_draft, MARK in table_title_cell(table, title))
                self.assertEqual(is_draft, MARK in board_cell(board, title))

    def test_board_draft_mark_still_replaces_the_not_ready_glyph(self) -> None:
        # The board shows a gated draft's ✎ instead of ⏳, while a gated
        # authored card keeps ⏳. Making the draft mark ignore `live` must
        # not change which of the two glyphs a live card gets.
        cards = [
            self.card("gated-draft", status="open", draft=True),
            self.card("gated-authored", status="open", draft=False),
        ]
        for card in cards:
            card.frontmatter["human_gate"] = "decision"
        board = engine.render_board(cards, max_rows=20, no_color=True)
        self.assertIn(MARK, board_cell(board, "gated-draft"))
        self.assertNotIn("⏳", board_cell(board, "gated-draft"))
        self.assertIn("⏳", board_cell(board, "gated-authored"))
        self.assertNotIn(MARK, board_cell(board, "gated-authored"))


if __name__ == "__main__":
    unittest.main()
