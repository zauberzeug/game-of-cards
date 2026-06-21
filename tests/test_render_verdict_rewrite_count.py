from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout


class RenderVerdictRewriteCountTest(unittest.TestCase):
    """`_render_verdict`'s `has_rewrite` return feeds `quality-pass --llm`'s
    `rewrite_count` ("N with proposed rewrites"). It must agree with what
    `_apply_verdict_interactive` will actually offer, which guards on
    `not ok and rewrite` — so a title/summary verdict that is `ok: false`
    but carries no `rewrite` string is NOT a proposed rewrite.
    """

    @staticmethod
    def _render(verdict: dict) -> tuple[bool, str]:
        from goc.engine import _render_verdict

        buf = io.StringIO()
        with redirect_stdout(buf):
            has_rewrite = _render_verdict(verdict)
        return has_rewrite, buf.getvalue()

    def test_rewriteless_title_and_summary_not_counted(self) -> None:
        has_rewrite, out = self._render(
            {
                "title": "c",
                "title_verdict": {"ok": False, "reason": "weak"},
                "summary_verdict": {"ok": False, "reason": "long"},
                "dod_issues": [],
            }
        )
        self.assertFalse(has_rewrite)
        self.assertNotIn("REWRITE", out)
        self.assertNotIn("proposed: ?", out)

    def test_real_title_rewrite_is_counted(self) -> None:
        has_rewrite, out = self._render(
            {
                "title": "c",
                "title_verdict": {"ok": False, "reason": "x", "rewrite": "better-title"},
                "summary_verdict": {"ok": True},
                "dod_issues": [],
            }
        )
        self.assertTrue(has_rewrite)
        self.assertIn("title:   REWRITE", out)
        self.assertIn("better-title", out)

    def test_real_summary_rewrite_is_counted(self) -> None:
        has_rewrite, out = self._render(
            {
                "title": "c",
                "title_verdict": {"ok": True},
                "summary_verdict": {"ok": False, "reason": "x", "rewrite": "a clearer summary"},
                "dod_issues": [],
            }
        )
        self.assertTrue(has_rewrite)
        self.assertIn("summary: REWRITE", out)

    def test_dod_issues_still_counted(self) -> None:
        has_rewrite, out = self._render(
            {
                "title": "c",
                "title_verdict": {"ok": False, "reason": "no fix"},
                "summary_verdict": {"ok": True},
                "dod_issues": [{"idx": 0, "issue": "vague", "fix": "do X"}],
            }
        )
        self.assertTrue(has_rewrite)  # driven by DoD, not the rewriteless title
        self.assertIn("dod:", out)

    def test_fixless_dod_issue_not_counted(self) -> None:
        """A DoD issue with no `fix` is not applicable (mirror
        `_apply_dod_rewrite`'s `"idx" in issue and "fix" in issue` guard), so it
        must NOT count toward has_rewrite and must not advertise a bogus fix."""
        has_rewrite, out = self._render(
            {
                "title": "c",
                "title_verdict": {"ok": True},
                "summary_verdict": {"ok": True},
                "dod_issues": [{"idx": 0, "issue": "vague"}],  # no "fix"
            }
        )
        self.assertFalse(has_rewrite)
        self.assertNotIn("fix: ?", out)
        self.assertIn("no rewrite offered", out)

    def test_mixed_fixable_and_fixless_dod_issues(self) -> None:
        """A verdict mixing an applicable fix with a fixless flag counts as a
        rewrite (the fixable one), and only the fixable issue advertises a fix."""
        has_rewrite, out = self._render(
            {
                "title": "c",
                "title_verdict": {"ok": True},
                "summary_verdict": {"ok": True},
                "dod_issues": [
                    {"idx": 0, "issue": "vague", "fix": "do X"},
                    {"idx": 1, "issue": "also vague"},  # no "fix"
                ],
            }
        )
        self.assertTrue(has_rewrite)
        self.assertIn("fix: do X", out)
        self.assertIn("no rewrite offered", out)


if __name__ == "__main__":
    unittest.main()
