from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


README = (
    "---\n"
    "title: tmp-card\n"
    "status: open\n"
    "stage: null\n"
    "contribution: low\n"
    'created: "2026-06-28T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] first criterion\n"
    "  - [ ] second criterion\n"
    "---\n\n# tmp-card\n"
)


class DodRewriteMultilineFixTest(unittest.TestCase):
    """A single-item `_apply_dod_rewrite` must not change the DoD box count.

    `fix` strings are LLM-authored (`claude --model sonnet --output-format
    json`). A multi-line `fix` — a wrapped rewrite or an accidental second
    `- [ ]` line — would otherwise become several physical lines on re-emit,
    and any checkbox-shaped line is counted as a fabricated DoD box.
    """

    def _rewrite(self, idx: int, fix: str):
        from goc.engine import (
            Card,
            _apply_dod_rewrite,
            count_dod_boxes,
            parse_frontmatter,
        )

        with tempfile.TemporaryDirectory() as d:
            card_dir = Path(d) / "tmp-card"
            card_dir.mkdir()
            (card_dir / "README.md").write_text(README)
            card = Card(
                title="tmp-card",
                path=card_dir,
                frontmatter={},
                body="",
                dod_open=2,
                dod_done=0,
            )
            _apply_dod_rewrite(card, [{"idx": idx, "fix": fix}])
            fm, _ = parse_frontmatter((card_dir / "README.md").read_text())
            dod = fm["definition_of_done"]
            return dod, count_dod_boxes(dod)

    def test_multiline_fix_does_not_fabricate_a_checkbox(self) -> None:
        dod, (open_boxes, done_boxes) = self._rewrite(
            0, "rewritten first\n- [ ] sneaky injected"
        )
        self.assertEqual(
            (open_boxes, done_boxes),
            (2, 0),
            f"multi-line fix changed the box count; DoD was:\n{dod}",
        )

    def test_multiline_fix_stays_one_line(self) -> None:
        dod, _ = self._rewrite(0, "rewritten first\nwrapped continuation")
        lines = dod.splitlines()
        self.assertEqual(
            len([ln for ln in lines if ln.strip()]),
            2,
            f"rewrite split one item into multiple lines; DoD was:\n{dod}",
        )

    def test_single_line_fix_unchanged(self) -> None:
        """The common single-line case keeps its prior behavior."""
        dod, (open_boxes, done_boxes) = self._rewrite(1, "reworded second criterion")
        self.assertEqual((open_boxes, done_boxes), (2, 0))
        self.assertIn("- [ ] reworded second criterion", dod)


if __name__ == "__main__":
    unittest.main()
