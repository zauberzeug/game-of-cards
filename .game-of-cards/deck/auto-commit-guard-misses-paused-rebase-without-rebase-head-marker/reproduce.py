#!/usr/bin/env python3
"""Proof that `_git_auto_commit` fails to skip during a paused rebase.

A paused interactive rebase (stopped at a `break`/`edit` step) leaves
`.git/rebase-merge/` on disk but NOT `REBASE_HEAD`. The guard at
engine.py:3898 only checks `MERGE_HEAD` / `REBASE_HEAD` / `CHERRY_PICK_HEAD`,
so it does not see the in-progress rebase and lets a commit through —
injecting it into the middle of the rebase sequence.

Run: uv run python deck/<title>/reproduce.py
Exit 0 == the guard correctly skips (defect fixed); exit 1 == defect fires.
"""
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


sys.path.insert(0, str(_repo_root()))


def _run(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, **kw)


def main() -> int:
    from goc import engine

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        _run(["git", "init", "-q", "-b", "main"], cwd=tmp)
        _run(["git", "config", "user.email", "t@example.com"], cwd=tmp)
        _run(["git", "config", "user.name", "Test"], cwd=tmp)
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

        # Pause an interactive rebase at a `break` step inserted after the
        # first picked commit. This leaves .git/rebase-merge/ but no REBASE_HEAD.
        env = {"GIT_SEQUENCE_EDITOR": 'sed -i "1a break"'}
        subprocess.run(
            ["git", "rebase", "-i", "HEAD~2"],
            cwd=tmp, capture_output=True, text=True,
            env={**__import__("os").environ, **env},
        )

        git_dir = tmp / ".git"
        rebase_in_progress = (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()
        rebase_head = (git_dir / "REBASE_HEAD").exists()
        print(f"rebase paused: rebase-merge|rebase-apply present = {rebase_in_progress}")
        print(f"               REBASE_HEAD present              = {rebase_head}")
        if not rebase_in_progress:
            print("SETUP FAILED: could not pause a rebase; cannot test the guard")
            return 2

        head_before = _run(["git", "rev-parse", "HEAD"], cwd=tmp).stdout.strip()

        # Now stage a deck mutation and call the shared auto-commit path,
        # exactly as `goc status active --commit` would mid-rebase.
        (deck / "README.md").write_text("body\nv2\nv3\nmutated by a goc verb\n")
        orig_root, orig_dir = engine.DECK_ROOT, engine.DECK_DIR
        try:
            engine.DECK_ROOT = tmp
            engine.DECK_DIR = tmp / ".game-of-cards" / "deck"
            landed = engine._git_auto_commit([deck], "deck: fake-card open → active")
        finally:
            engine.DECK_ROOT, engine.DECK_DIR = orig_root, orig_dir

        head_after = _run(["git", "rev-parse", "HEAD"], cwd=tmp).stdout.strip()
        committed_mid_rebase = head_before != head_after

        print(f"_git_auto_commit returned: {landed}")
        print(f"commit injected mid-rebase: {committed_mid_rebase}")

        subprocess.run(["git", "rebase", "--abort"], cwd=tmp, capture_output=True)

        if landed or committed_mid_rebase:
            print("DEFECT: auto-commit ran during a paused rebase (guard missed it)")
            return 1
        print("OK: auto-commit correctly skipped during the paused rebase")
        return 0


if __name__ == "__main__":
    sys.exit(main())
