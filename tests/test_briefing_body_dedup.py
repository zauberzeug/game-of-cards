from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goc.install import _briefing_body, _templates_root  # noqa: E402


class BriefingBodyDedupTest(unittest.TestCase):
    """`_briefing_body` must emit the `Closure is not frozenness.` paragraph
    exactly once for every briefing target. CLAUDE.md is the regression
    surface — it concatenates AGENTS_GOC.md and CLAUDE_GOC.md, so a
    duplicate of any generic paragraph between the two templates would
    surface as a doubled paragraph in the marker-bounded GoC briefing
    block written by `goc install`.
    """

    NEEDLE = "Closure is not frozenness"

    def test_paragraph_appears_exactly_once_per_target(self) -> None:
        templates = _templates_root()
        for target in ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md"):
            with self.subTest(target=target):
                body = _briefing_body(templates, target)
                self.assertEqual(
                    body.count(self.NEEDLE),
                    1,
                    msg=f"{target} briefing body emits {self.NEEDLE!r} "
                        f"{body.count(self.NEEDLE)}x; expected exactly 1.",
                )


if __name__ == "__main__":
    unittest.main()
