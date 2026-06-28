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
    'created: "2026-06-21T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] TDD: top-level criterion\n"
    "    - [ ] sub-criterion under it\n"
    "  - [x] already-done item\n"
    "---\n\n# tmp-card\n"
)


class DodRewritePreservesIndentTest(unittest.TestCase):
    """`_apply_dod_rewrite` must keep a nested checkbox's leading indentation.

    `_dod_box_indices` counts indented `  - [ ]` sub-items as boxes at their
    own index, so an LLM verdict can target one. The rewriter lstrips the
    fix text and rebuilds the line; without re-applying the original indent
    the nested item is flattened to column 0, silently restructuring the DoD.
    """

    def _rewrite(self, idx: int, fix: str) -> list[str]:
        from goc.engine import Card, _apply_dod_rewrite, parse_frontmatter

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
                dod_done=1,
            )
            _apply_dod_rewrite(card, [{"idx": idx, "fix": fix}])
            fm, _ = parse_frontmatter((card_dir / "README.md").read_text())
            return fm["definition_of_done"].splitlines()

    def test_nested_item_keeps_indent(self) -> None:
        lines = self._rewrite(1, "sub-criterion reworded to be measurable")
        self.assertTrue(
            lines[1].startswith("  - [ ]"),
            f"nested sub-item lost its indent: {lines[1]!r}",
        )

    def test_top_level_item_stays_at_column_zero(self) -> None:
        lines = self._rewrite(0, "top-level criterion reworded")
        self.assertTrue(
            lines[0].startswith("- [ ]") and not lines[0].startswith("  "),
            f"top-level item gained spurious indent: {lines[0]!r}",
        )


if __name__ == "__main__":
    unittest.main()
