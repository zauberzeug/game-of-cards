from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class BoardRenderingTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_card(
        self,
        cwd: Path,
        title: str,
        status: str,
        *,
        worker: str | None = None,
    ) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            + (f"worker: {worker}\n" if worker else "")
            + "definition_of_done: |\n"
            "  - [x] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_board_renders_every_status_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for status in ("open", "active", "blocked", "done", "disproved", "superseded"):
                self.write_card(cwd, f"{status}-card", status)

            result = self.run_goc(cwd, "--board", "--no-color")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            for header in ("OPEN", "ACTIVE", "BLOCKED", "DONE", "DISPROVED", "SUPERSEDED"):
                self.assertIn(header, result.stdout)
            for status in ("open", "active", "blocked", "done", "disproved", "superseded"):
                self.assertIn(f"{status}-card", result.stdout)


    def test_board_columns_derive_from_schema_status_values(self) -> None:
        """A status the schema declares but the old hardcoded literal omitted
        must still get a column and render its cards — the board reads its
        status enum from `schema.status_values`, not a hardcoded list."""
        from goc import engine

        custom = replace(
            engine.load_schema(),
            status_values=[
                "open", "active", "review", "blocked",
                "done", "disproved", "superseded",
            ],
        )
        card = engine.Card(
            title="in-review-card",
            path=Path("/tmp/in-review-card"),
            frontmatter={
                "title": "in-review-card",
                "status": "review",
                "contribution": "medium",
                "human_gate": "none",
            },
            body="",
            dod_open=0,
            dod_done=0,
        )
        with mock.patch.object(engine, "load_schema", return_value=custom):
            board = engine.render_board([card], max_rows=20, no_color=True)

        self.assertIn("REVIEW", board)
        self.assertIn("in-review-card", board)

    def test_board_preserves_title_when_worker_suffix_expands_cell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "active-card", "active", worker="Rodja Tr")

            result = self.run_goc(cwd, "--board", "--no-color")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("active-card [l] @Rodja Tr", result.stdout)
            self.assertNotIn("active [l] @Rodja Tr", result.stdout)

    def test_board_renders_full_worker_label_over_eight_chars(self) -> None:
        """The worker suffix must render in full, not truncated to 8 chars.

        Columns auto-size to their widest rendered cell, so a long `who`
        like `claude[bot]` widens the column rather than overflowing. A
        silent `who[:8]` slice would mangle it to `@claude[b`, hiding the
        coordination info the board exists to surface.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "active-card", "active", worker='{who: "claude[bot]"}')

            result = self.run_goc(cwd, "--board", "--no-color")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("@claude[bot]", result.stdout)
            self.assertNotIn("@claude[b ", result.stdout)

    def _open_card(self, title: str):
        from goc import engine

        return engine.Card(
            title=title,
            path=Path(f"/tmp/{title}"),
            frontmatter={
                "title": title,
                "status": "open",
                "contribution": "medium",
                "human_gate": "none",
                "advances": [],
                "advanced_by": [],
                "tags": ["bug"],
            },
            body="",
            dod_open=1,
            dod_done=0,
        )

    def test_board_advertises_hidden_rows_when_truncated(self) -> None:
        """A column with more cards than max_rows must surface the overflow
        count, not silently slice the tail away."""
        from goc import engine

        cards = [self._open_card(f"card-{i:02d}") for i in range(25)]
        board = engine.render_board(cards, max_rows=5, no_color=True)

        self.assertIn("+20 more", board)

        # Indicator count equals (total - rows shown).
        open_rows = [
            line.split(" | ")[0].strip()
            for line in board.splitlines()[2:]
            if line.split(" | ")[0].strip()
        ]
        self.assertEqual(5, sum(1 for r in open_rows if r.startswith("card-")))
        self.assertEqual(1, sum(1 for r in open_rows if "more" in r))

    def test_board_omits_indicator_when_not_truncated(self) -> None:
        """A column at or below the cap must not emit a false '+0 more'."""
        from goc import engine

        cards = [self._open_card(f"card-{i:02d}") for i in range(5)]
        board = engine.render_board(cards, max_rows=5, no_color=True)

        self.assertNotIn("more", board)

    def test_board_truncation_indicator_keeps_grid_aligned(self) -> None:
        """The indicator row participates in width sizing — every rendered
        row has identical display width."""
        from goc import engine

        cards = [self._open_card(f"card-{i:02d}") for i in range(25)]
        board = engine.render_board(cards, max_rows=5, no_color=True)

        widths = {engine._display_width(line) for line in board.splitlines()}
        self.assertEqual(1, len(widths), msg=f"misaligned rows: {widths}")

    def test_board_marks_human_gate_parked_card_not_pullable(self) -> None:
        """An open card parked behind a human gate is not pullable
        (`card_is_ready` False), so the board must paint it with the ⏳
        not-pullable marker — just like the equally-un-pullable
        `waiting_impedes` card — not render it identically to a freely
        pullable card. Regression for the board's `not_ready` predicate
        omitting the `human_gate` axis that `card_is_ready` /
        `card_is_workable_for_scheduler` both reject on."""
        from goc import engine

        gated = self._open_card("gated-decision")
        gated.frontmatter["human_gate"] = "decision"
        impeded = self._open_card("impeded")
        impeded.frontmatter["waiting_on"] = "external"
        impeded.frontmatter["waiting_until"] = "2099-01-01"
        free = self._open_card("free")
        cards = [gated, impeded, free]
        by_title = {c.title: c for c in cards}

        # Preconditions: gated and impeded are not pullable; free is.
        self.assertFalse(engine.card_is_ready(gated, by_title))
        self.assertFalse(engine.card_is_ready(impeded, by_title))
        self.assertTrue(engine.card_is_ready(free, by_title))

        board = engine.render_board(cards, max_rows=20, no_color=True, by_title=by_title)

        def open_cell(title: str) -> str:
            for line in board.splitlines():
                if line.startswith(title):
                    return line.split("|")[0].rstrip()
            self.fail(f"{title!r} not found on board")

        self.assertIn("⏳", open_cell("gated-decision"))
        self.assertIn("⏳", open_cell("impeded"))
        self.assertNotIn("⏳", open_cell("free"))

    def test_renderers_tolerate_non_string_contribution(self) -> None:
        """A hand-edited or legacy card with a non-string scalar
        `contribution` (e.g. `42`) loads cleanly (`load_all_cards` only
        skips `FrontmatterError`, not schema violations) and the read-only
        views render BEFORE validation. `Card.contribution` must coerce to
        `str` so `render_table` (`len`/`ljust`) and `render_board` (`[0]`)
        don't crash the entire deck view on one bad card. Regression for the
        non-string shape left open by `board-crashes-when-a-card-has-no-
        contribution-value` (which fixed only the empty/None case)."""
        from goc import engine

        card = self._open_card("int-contribution")
        card.frontmatter["contribution"] = 42

        # The property hands a string to every downstream consumer.
        self.assertEqual("42", card.contribution)

        vals = engine.compute_values([card])
        # Neither renderer raises.
        engine.render_table([card], values=vals, verbose=0, no_color=True)
        engine.render_table([card], values=vals, verbose=1, no_color=True)
        board = engine.render_board([card], values=vals, max_rows=20, no_color=True)
        self.assertIn("[4]", board)  # marker is first char of "42"

    def test_table_tolerates_non_string_tag_element(self) -> None:
        """`render_table` joins the first four tags; a non-string element
        (e.g. `42` from a hand edit or legacy card) loads cleanly and must
        not crash the whole queue view on the join. Sibling of the
        non-string-contribution crash; only the table renders tags, so the
        board and JSON paths already tolerate the shape."""
        from goc import engine

        card = self._open_card("int-tag")
        card.frontmatter["tags"] = ["bug", 42]

        vals = engine.compute_values([card])
        table = engine.render_table([card], values=vals, verbose=0, no_color=True)
        engine.render_table([card], values=vals, verbose=1, no_color=True)
        self.assertIn("bug,42", table)

    def test_board_marks_none_contribution_with_placeholder(self) -> None:
        """Coercion must not regress the empty/None case: a blank
        `contribution:` (parses to None) stays falsy and keeps the `[?]`
        marker rather than becoming the truthy string ``"None"`` → `[N]`."""
        from goc import engine

        card = self._open_card("none-contribution")
        card.frontmatter["contribution"] = None

        self.assertEqual("", card.contribution)
        board = engine.render_board([card], max_rows=20, no_color=True)
        self.assertIn("[?]", board)
        self.assertNotIn("[N]", board)

    def test_board_rejects_negative_max_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-card", "open")

            negative = self.run_goc(cwd, "--board", "--max-rows", "-1")
            zero = self.run_goc(cwd, "--board", "--max-rows", "0")
            one = self.run_goc(cwd, "--board", "--max-rows", "1")

            self.assertEqual(2, negative.returncode, msg=negative.stdout + negative.stderr)
            self.assertIn("--max-rows", negative.stderr)
            self.assertEqual(0, zero.returncode, msg=zero.stderr)
            self.assertEqual(0, one.returncode, msg=one.stderr)


if __name__ == "__main__":
    unittest.main()
