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
    "worker: {who: alice, where: feature/foo}\n"
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


class AutoPopulateWorkerPreservesWhereTest(unittest.TestCase):
    """Claiming a card must not destroy a stored `worker.where`.

    When no `--worker-where` flag is given and the git tree has no detectable
    branch (detached HEAD / fresh checkout, where `git rev-parse --abbrev-ref
    HEAD` prints `HEAD`), the existing `where` must be preserved rather than
    dropped (which collapsed the worker to a bare `who` string).
    """

    def _run(self, work: Path, home: Path, card_text: str, who, where):
        cwd = os.getcwd()
        os.chdir(work)
        old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            return engine._auto_populate_worker(card_text, _card(card_text), who, where)
        finally:
            os.chdir(cwd)
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

    def _make_detached_repo(self, work: Path, home: Path) -> dict:
        env = dict(os.environ, HOME=str(home))
        _git(["init", "-q"], work, env)
        _git(["checkout", "-q", "-b", "main"], work, env)
        (work / "f").write_text("x")
        _git(["-c", "user.name=alice", "-c", "user.email=a@e", "add", "f"], work, env)
        _git(["-c", "user.name=alice", "-c", "user.email=a@e", "commit", "-qm", "init"], work, env)
        head = _git(["rev-parse", "HEAD"], work, env).stdout.strip()
        _git(["checkout", "-q", head], work, env)  # detach HEAD
        _git(["config", "--global", "user.name", "alice"], work, env)
        return env

    def test_detached_head_preserves_existing_where(self) -> None:
        with tempfile.TemporaryDirectory() as w, tempfile.TemporaryDirectory() as h:
            work, home = Path(w), Path(h)
            env = self._make_detached_repo(work, home)
            self.assertEqual(
                _git(["rev-parse", "--abbrev-ref", "HEAD"], work, env).stdout.strip(), "HEAD"
            )

            out = self._run(work, home, CARD_TEXT, None, None)

            fm, _ = engine.parse_frontmatter(out)
            self.assertEqual(
                fm.get("worker"),
                {"who": "alice", "where": "feature/foo"},
                "stored worker.where must survive a claim on a detached HEAD",
            )

    def test_detectable_branch_still_updates_where(self) -> None:
        # The documented "add/update where" behavior is unchanged: when a branch
        # IS detectable, `where` is updated to the current branch.
        with tempfile.TemporaryDirectory() as w, tempfile.TemporaryDirectory() as h:
            work, home = Path(w), Path(h)
            env = dict(os.environ, HOME=str(home))
            _git(["init", "-q"], work, env)
            _git(["checkout", "-q", "-b", "main"], work, env)
            (work / "f").write_text("x")
            _git(["-c", "user.name=alice", "-c", "user.email=a@e", "add", "f"], work, env)
            _git(["-c", "user.name=alice", "-c", "user.email=a@e", "commit", "-qm", "init"], work, env)
            _git(["config", "--global", "user.name", "alice"], work, env)

            out = self._run(work, home, CARD_TEXT, None, None)

            fm, _ = engine.parse_frontmatter(out)
            self.assertEqual(fm.get("worker"), {"who": "alice", "where": "main"})


if __name__ == "__main__":
    unittest.main()
