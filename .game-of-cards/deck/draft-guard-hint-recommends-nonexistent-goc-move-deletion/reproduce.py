"""Offline reproduction: the draft-scaffold refusal in `goc status` hints
`delete it with `goc move``, but `goc move` is a rename verb with two
required positionals — the hinted remedy exits 2 with a usage error.

Run: uv run python .game-of-cards/deck/draft-guard-hint-recommends-nonexistent-goc-move-deletion/reproduce.py
Exits non-zero while the defect fires.
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


def main() -> int:
    root = _repo_root()

    with tempfile.TemporaryDirectory() as tmp:
        consumer = Path(tmp) / "consumer"
        consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(consumer)], check=True)
        (consumer / ".game-of-cards" / "deck").mkdir(parents=True)

        env = dict(os.environ, PYTHONPATH=str(root))

        def goc(*argv):
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *argv],
                cwd=consumer,
                env=env,
                capture_output=True,
                text=True,
            )

        goc("new", "canonical-card", "--summary", "the canonical card")
        # gate none so the terminal-status human-gate guard (which fires
        # first) doesn't mask the draft-scaffold refusal under test
        goc("new", "my-draft", "--summary", "duplicate scaffold, never authored", "--gate", "none")

        refusal = goc("status", "my-draft", "superseded", "--by", "canonical-card")
        hint = "delete it with `goc move`" in refusal.stderr
        print(f'[1] refusal stderr contains "delete it with `goc move`": {hint}')

        remedy = goc("move", "my-draft")
        err = remedy.stderr.strip().splitlines()[-1] if remedy.stderr.strip() else ""
        print(f"[2] hinted remedy `goc move my-draft` -> exit {remedy.returncode}: {err}")

        if hint and remedy.returncode != 0:
            print("[FAIL] refusal hint names a deletion remedy the CLI cannot execute")
            return 1
        print("[OK] hint no longer names an unexecutable remedy")
        return 0


if __name__ == "__main__":
    sys.exit(main())
