from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class GitAutoCommitPathspecTest(unittest.TestCase):
    """`_git_auto_commit` must commit ONLY the card paths it was given,
    even when the index also holds unrelated files staged by a parallel
    agent. AGENTS.md "Parallel-Agent Commit Safety" requires the pathspec
    on `git commit` as the last guard.
    """

    def test_unrelated_staged_file_is_not_swept_into_card_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            _run(["git", "init", "-q", "-b", "main"], cwd=tmp)
            _run(["git", "config", "user.email", "test@example.com"], cwd=tmp)
            _run(["git", "config", "user.name", "Test"], cwd=tmp)
            os.environ["PRE_COMMIT_ALLOW_NO_CONFIG"] = "1"

            deck = tmp / ".game-of-cards" / "deck" / "fake-card"
            deck.mkdir(parents=True)
            (deck / "README.md").write_text("initial card body\n")
            (deck / "log.md").write_text("")
            (tmp / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
            _run(["git", "add", "."], cwd=tmp)
            _run(["git", "commit", "-q", "-m", "seed"], cwd=tmp)

            stray = tmp / "stray-from-another-agent.txt"
            stray.write_text("WIP from a co-agent — must NOT be in the card commit\n")
            _run(["git", "add", "stray-from-another-agent.txt"], cwd=tmp)

            (deck / "README.md").write_text("initial card body\nmutated by status flip\n")

            from goc import engine
            original_deck_root = engine.DECK_ROOT
            original_deck_dir = engine.DECK_DIR
            try:
                engine.DECK_ROOT = tmp
                engine.DECK_DIR = tmp / ".game-of-cards" / "deck"
                ok = engine._git_auto_commit([deck], "deck: fake-card open → active")
            finally:
                engine.DECK_ROOT = original_deck_root
                engine.DECK_DIR = original_deck_dir

            self.assertTrue(ok, "_git_auto_commit returned False unexpectedly")

            result = _run(
                ["git", "show", "--name-only", "--format=", "HEAD"], cwd=tmp
            )
            committed = sorted(line for line in result.stdout.splitlines() if line.strip())

            self.assertNotIn(
                "stray-from-another-agent.txt",
                committed,
                f"co-agent WIP was bundled into card commit: {committed}",
            )
            self.assertIn(".game-of-cards/deck/fake-card/README.md", committed)


if __name__ == "__main__":
    unittest.main()
