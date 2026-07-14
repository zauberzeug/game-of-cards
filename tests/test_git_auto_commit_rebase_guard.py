from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _run(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, **kw)


class GitAutoCommitRebaseGuardTest(unittest.TestCase):
    """`_git_auto_commit` must skip while a rebase is in progress, including
    a PAUSED interactive rebase (break/edit step) where `REBASE_HEAD` is
    absent. The reliable sentinel is the rebase state directory
    (`.git/rebase-merge/` for the merge backend, `.git/rebase-apply/` for
    the apply backend) — checking only MERGE_HEAD/REBASE_HEAD/CHERRY_PICK_HEAD
    lets a commit get injected into the middle of the rebase sequence.
    """

    def _seed_repo(self, tmp: Path) -> Path:
        _run(["git", "init", "-q", "-b", "main"], cwd=tmp)
        _run(["git", "config", "user.email", "test@example.com"], cwd=tmp)
        _run(["git", "config", "user.name", "Test"], cwd=tmp)
        os.environ["PRE_COMMIT_ALLOW_NO_CONFIG"] = "1"
        (tmp / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        deck = tmp / ".game-of-cards" / "deck" / "fake-card"
        deck.mkdir(parents=True)
        (deck / "README.md").write_text("body\n")
        (deck / "log.md").write_text("")
        _run(["git", "add", "."], cwd=tmp)
        _run(["git", "commit", "-q", "-m", "c1"], cwd=tmp)
        (deck / "README.md").write_text("body\nv2\n")
        _run(["git", "commit", "-qam", "c2"], cwd=tmp)
        (deck / "README.md").write_text("body\nv2\nv3\n")
        _run(["git", "commit", "-qam", "c3"], cwd=tmp)
        return deck

    def test_skips_during_paused_interactive_rebase(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            deck = self._seed_repo(tmp)

            # Pause an interactive rebase at an inserted `break` step. This
            # leaves .git/rebase-merge/ on disk but NOT REBASE_HEAD. The
            # sequence editor must be portable: GNU sed's `-i "1a break"` is
            # invalid on BSD/macOS sed, so edit the todo list with Python.
            editor = tmp / "insert_break.py"
            editor.write_text(
                "import pathlib, sys\n"
                "todo = pathlib.Path(sys.argv[1])\n"
                "lines = todo.read_text().splitlines(keepends=True)\n"
                "lines.insert(1, 'break\\n')\n"
                "todo.write_text(''.join(lines))\n"
            )
            subprocess.run(
                ["git", "rebase", "-i", "HEAD~2"],
                cwd=tmp, capture_output=True, text=True,
                env={**os.environ,
                     "GIT_SEQUENCE_EDITOR": f'"{sys.executable}" "{editor}"'},
            )
            git_dir = tmp / ".git"
            self.assertTrue(
                (git_dir / "rebase-merge").exists(),
                "setup failed: expected a paused rebase (rebase-merge/ present)",
            )
            self.assertFalse(
                (git_dir / "REBASE_HEAD").exists(),
                "setup assumption broke: REBASE_HEAD unexpectedly present at break step",
            )

            head_before = _run(["git", "rev-parse", "HEAD"], cwd=tmp).stdout.strip()
            (deck / "README.md").write_text("body\nv2\nv3\nmutated by a goc verb\n")

            from goc import engine
            orig_root, orig_dir = engine.DECK_ROOT, engine.DECK_DIR
            try:
                engine.DECK_ROOT = tmp
                engine.DECK_DIR = tmp / ".game-of-cards" / "deck"
                landed = engine._git_auto_commit([deck], "deck: fake-card open → active")
            finally:
                engine.DECK_ROOT, engine.DECK_DIR = orig_root, orig_dir

            head_after = _run(["git", "rev-parse", "HEAD"], cwd=tmp).stdout.strip()
            subprocess.run(["git", "rebase", "--abort"], cwd=tmp, capture_output=True)

            self.assertFalse(landed, "_git_auto_commit committed during a paused rebase")
            self.assertEqual(
                head_before, head_after,
                "a commit was injected into the middle of the rebase sequence",
            )


if __name__ == "__main__":
    unittest.main()
