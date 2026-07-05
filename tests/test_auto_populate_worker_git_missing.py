from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


CARD_TEXT = (
    "---\n"
    "title: demo-card\n"
    "summary: demo-card\n"
    "status: open\n"
    "stage: null\n"
    "contribution: low\n"
    "created: 2026-07-05\n"
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] PROCESS: test card\n"
    "---\n\n"
    "# demo\n"
)


def _card(text: str):
    fm, _ = engine.parse_frontmatter(text)
    return type("C", (), {"frontmatter": fm})()


class AutoPopulateWorkerGitMissingTest(unittest.TestCase):
    """`_auto_populate_worker` must degrade gracefully when git is not on PATH.

    The claim verb auto-detects `who`/`where` by shelling out to git. When the
    binary is absent (minimal container, PATH-stripped CI), `subprocess.run`
    raises FileNotFoundError — which used to escape as a raw traceback that
    aborted `goc status <title> active`. A missing git must behave exactly
    like git failing: no worker detected, card text left untouched.
    """

    def _with_empty_path(self, fn):
        with tempfile.TemporaryDirectory() as empty:
            old_path = os.environ.get("PATH")
            os.environ["PATH"] = empty
            try:
                return fn()
            finally:
                if old_path is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = old_path

    def test_git_missing_leaves_card_unchanged(self) -> None:
        out = self._with_empty_path(
            lambda: engine._auto_populate_worker(CARD_TEXT, _card(CARD_TEXT), None, None)
        )
        self.assertEqual(out, CARD_TEXT, "git-less claim must leave the card text unchanged")
        self.assertNotIn("worker:", out)

    def test_git_missing_with_explicit_who_still_stamps(self) -> None:
        # Explicit --worker-who skips the `git config` call; the branch lookup
        # still fires and must tolerate the missing binary (where stays unset).
        out = self._with_empty_path(
            lambda: engine._auto_populate_worker(CARD_TEXT, _card(CARD_TEXT), "alice", None)
        )
        fm, _ = engine.parse_frontmatter(out)
        self.assertEqual(fm.get("worker"), "alice")


if __name__ == "__main__":
    unittest.main()
