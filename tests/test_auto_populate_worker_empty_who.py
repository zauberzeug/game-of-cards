from __future__ import annotations

import os
import subprocess
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
    "created: 2026-06-06\n"
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


def _git(args, cwd, env):
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)


def _card(text: str):
    fm, _ = engine.parse_frontmatter(text)
    return type("C", (), {"frontmatter": fm})()


class AutoPopulateWorkerEmptyWhoTest(unittest.TestCase):
    """`_auto_populate_worker` must never stamp an invalid empty-`who` worker.

    When git `user.name` is unset (a stock CI/container checkout) but the tree
    is on a named branch, the function used to hand-build
    `worker: {who: "", where: <branch>}` — a mapping `validate_card` rejects.
    The claim must instead leave the card untouched, because a `where`-only
    worker is itself invalid: there is no valid worker to write.
    """

    def _make_repo(self, work: Path, home: Path) -> dict:
        env = dict(os.environ, HOME=str(home))
        _git(["init", "-q"], work, env)
        _git(["checkout", "-q", "-b", "main"], work, env)
        (work / "f").write_text("x")
        _git(["-c", "user.name=tmp", "-c", "user.email=tmp@e", "add", "f"], work, env)
        _git(["-c", "user.name=tmp", "-c", "user.email=tmp@e", "commit", "-qm", "init"], work, env)
        # Leave user.name unset in both local and global config.
        _git(["config", "--global", "--unset", "user.name"], work, env)
        _git(["config", "--local", "--unset", "user.name"], work, env)
        return env

    def test_empty_who_with_branch_leaves_card_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as w, tempfile.TemporaryDirectory() as h:
            work, home = Path(w), Path(h)
            env = self._make_repo(work, home)

            self.assertEqual(_git(["config", "user.name"], work, env).stdout.strip(), "")
            self.assertEqual(
                _git(["rev-parse", "--abbrev-ref", "HEAD"], work, env).stdout.strip(), "main"
            )

            cwd = os.getcwd()
            os.chdir(work)
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            try:
                out = engine._auto_populate_worker(CARD_TEXT, _card(CARD_TEXT), None, None)
            finally:
                os.chdir(cwd)
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

            self.assertEqual(out, CARD_TEXT, "card text must be unchanged when who is empty")
            self.assertNotIn("worker:", out)
            fm, _ = engine.parse_frontmatter(out)
            self.assertIsNone(fm.get("worker"))

    def test_explicit_who_still_stamps_branch(self) -> None:
        # Positive control: when `who` IS known, the branch is still recorded.
        with tempfile.TemporaryDirectory() as w, tempfile.TemporaryDirectory() as h:
            work, home = Path(w), Path(h)
            self._make_repo(work, home)

            cwd = os.getcwd()
            os.chdir(work)
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            try:
                out = engine._auto_populate_worker(CARD_TEXT, _card(CARD_TEXT), "alice", None)
            finally:
                os.chdir(cwd)
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home

            fm, _ = engine.parse_frontmatter(out)
            self.assertEqual(fm.get("worker"), {"who": "alice", "where": "main"})


if __name__ == "__main__":
    unittest.main()
