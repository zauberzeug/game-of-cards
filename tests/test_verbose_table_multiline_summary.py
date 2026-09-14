from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


class VerboseTableMultiLineSummaryTest(unittest.TestCase):
    """`goc -v`'s per-card block must stay inside its four-space indent.

    Every entry the `verbose >= 1` block writes is one `    key: value`
    line, and that indent is what marks a line as belonging to the row
    above rather than being a new record. `summary` is a multi-line block
    scalar on a real share of a mature deck — `emit_frontmatter` writes any
    multi-line string that way and `_apply_summary_rewrite` exists to
    produce them from `goc quality-pass` — so interpolating it whole
    emitted continuation lines at column zero. See
    `deck/verbose-table-renders-a-multi-line-summary-raw-breaking-the-per-card-block/`.
    """

    MULTI = (
        "First line of the summary.\n"
        "Second line that YAML kept as a block scalar.\n"
        "Third line."
    )

    def card(self, title: str, summary: str) -> engine.Card:
        return engine.Card(
            title=title,
            path=None,
            frontmatter={
                "title": title,
                "summary": summary,
                "status": "open",
                "stage": None,
                "contribution": "medium",
                "created": "2026-05-04",
                "closed_at": None,
                "human_gate": "none",
                "advances": [],
                "advanced_by": [],
                "tags": [],
                "definition_of_done": "- [ ] MECHANICAL: x\n",
            },
            body="",
            dod_open=1,
            dod_done=0,
        )

    @staticmethod
    def detail_lines(rendered: str) -> list[str]:
        """The per-card block: everything after header, rule, and data row."""
        return rendered.splitlines()[3:]

    def render(self, summary: str, title: str = "multi-line-summary-card") -> str:
        return engine.render_table(
            [self.card(title, summary)], verbose=1, no_color=True
        )

    def summary_lines(self, rendered: str) -> list[str]:
        return [ln for ln in self.detail_lines(rendered) if "summary:" in ln]

    def test_multi_line_summary_stays_inside_the_block_indent(self) -> None:
        rendered = self.render(self.MULTI)
        strays = [
            ln
            for ln in self.detail_lines(rendered)
            if ln and not ln.startswith("    ")
        ]
        self.assertEqual(
            [], strays,
            msg=(
                "continuation lines of a multi-line summary escaped the "
                "four-space per-card block indent and read as new records"
            ),
        )

    def test_multi_line_summary_renders_exactly_one_summary_line(self) -> None:
        rendered = self.render(self.MULTI)
        self.assertEqual(1, len(self.summary_lines(rendered)))
        self.assertNotIn("Second line", rendered)
        self.assertNotIn("Third line", rendered)

    def test_clipped_summary_names_the_card_so_the_full_text_is_reachable(self) -> None:
        rendered = self.render(self.MULTI, title="some-clipped-card")
        line = self.summary_lines(rendered)[0]
        self.assertIn("First line of the summary.", line)
        self.assertIn("…", line)
        self.assertIn("goc show some-clipped-card", line)

    def test_single_line_summary_is_unchanged_and_carries_no_indicator(self) -> None:
        rendered = self.render("One line only.")
        self.assertEqual(
            ["    summary: One line only."], self.summary_lines(rendered)
        )

    def test_trailing_newline_only_summary_is_not_treated_as_multi_line(self) -> None:
        # `emit_frontmatter` writes `|` (clip) for a value ending in a single
        # newline, so a one-sentence summary round-trips with a trailing "\n".
        # `splitlines()` yields one element for it, so no clip indicator is due.
        rendered = self.render("One line only.\n")
        self.assertEqual(
            ["    summary: One line only."], self.summary_lines(rendered)
        )


if __name__ == "__main__":
    unittest.main()
