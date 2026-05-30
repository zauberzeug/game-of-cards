"""Reproduce: `_git_auto_commit` commits ALL staged files, not just the
card paths it was asked to commit. This contradicts AGENTS.md
"Parallel-Agent Commit Safety" which requires `git commit -- <path>...`
as the last guard against bundling unrelated staged files.

Run: `uv run python .game-of-cards/deck/deck-auto-commit-sweeps-unrelated-staged-files-into-card-commits/reproduce.py`
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()
sys.path.insert(0, str(REPO))


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 1. Set up a fake repo with a .game-of-cards/deck/ tree.
        _run(["git", "init", "-q", "-b", "main"], cwd=tmp)
        _run(["git", "config", "user.email", "test@example.com"], cwd=tmp)
        _run(["git", "config", "user.name", "Test"], cwd=tmp)
        # Disable any global pre-commit so the reproducer is self-contained.
        os.environ["PRE_COMMIT_ALLOW_NO_CONFIG"] = "1"
        deck = tmp / ".game-of-cards" / "deck" / "fake-card"
        deck.mkdir(parents=True)
        (deck / "README.md").write_text("initial card body\n")
        (deck / "log.md").write_text("")
        (tmp / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        _run(["git", "add", "."], cwd=tmp)
        _run(["git", "commit", "-q", "-m", "seed"], cwd=tmp)

        # 2. Simulate a parallel agent's WIP: stage an unrelated file.
        stray = tmp / "stray-from-another-agent.txt"
        stray.write_text("WIP from a co-agent — must NOT be in the card commit\n")
        _run(["git", "add", "stray-from-another-agent.txt"], cwd=tmp)

        # 3. Mutate the card README, as a status flip would.
        (deck / "README.md").write_text("initial card body\nmutated by status flip\n")

        # 4. Drive `_git_auto_commit` against ONLY the card directory.
        #    Patch DECK_ROOT so it points at our temp tree.
        from goc import engine
        engine.DECK_ROOT = tmp
        engine.DECK_DIR = tmp / ".game-of-cards" / "deck"
        ok = engine._git_auto_commit([deck], "deck: fake-card open → active")
        if not ok:
            print("UNEXPECTED: _git_auto_commit returned False")
            return 2

        # 5. Inspect what landed in HEAD.
        result = _run(
            ["git", "show", "--name-only", "--format=", "HEAD"], cwd=tmp
        )
        committed = sorted(line for line in result.stdout.splitlines() if line.strip())
        print("Files in the auto-commit:")
        for f in committed:
            print(f"  {f}")

        bundled_stray = "stray-from-another-agent.txt" in committed
        print()
        print(f"AGENTS.md:359-360 requires `git commit -- <path>...`; "
              f"engine.py:3409 omits the pathspec.")
        print(f"Co-agent WIP bundled into card commit? {bundled_stray}")
        if bundled_stray:
            print("DEFECT REPRODUCED: unrelated staged file was swept into the "
                  "card commit despite _git_auto_commit being given only the card "
                  "directory as its pathspec argument.")
            return 1
        print("No defect — the commit pathspec held.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
