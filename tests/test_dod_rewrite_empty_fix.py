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
    "  - [ ] TDD: regression test proves the fix\n"
    "  - [ ] implement the guard\n"
    "---\n\n# tmp-card\n"
)


class DodRewriteEmptyFixTest(unittest.TestCase):
    """`_apply_dod_rewrite` must not blank a DoD item when the `fix` is empty.

    An accepted verdict issue can carry an empty (or whitespace-only) `fix`
    string — "I flagged this item but offered no replacement." The rewriter
    must preserve the original line verbatim (its docstring contract), not
    rewrite it to the content-less literal "- [ ] ".
    """

    def _rewrite(self, issues: list[dict]) -> list[str]:
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
                dod_done=0,
            )
            _apply_dod_rewrite(card, issues)
            fm, _ = parse_frontmatter((card_dir / "README.md").read_text())
            return fm["definition_of_done"].splitlines()

    def test_empty_fix_preserves_criterion(self) -> None:
        lines = self._rewrite([{"idx": 0, "fix": ""}])
        self.assertEqual(lines[0], "- [ ] TDD: regression test proves the fix")

    def test_whitespace_fix_preserves_criterion(self) -> None:
        lines = self._rewrite([{"idx": 0, "fix": "   "}])
        self.assertEqual(lines[0], "- [ ] TDD: regression test proves the fix")

    def test_non_empty_fix_in_same_call_still_applies(self) -> None:
        lines = self._rewrite(
            [{"idx": 0, "fix": ""}, {"idx": 1, "fix": "TDD: reworded and measurable"}]
        )
        # idx 0 preserved verbatim despite the empty fix.
        self.assertEqual(lines[0], "- [ ] TDD: regression test proves the fix")
        # idx 1 still rewritten normally.
        self.assertEqual(lines[1], "- [ ] TDD: reworded and measurable")


if __name__ == "__main__":
    unittest.main()
