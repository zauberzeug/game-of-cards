#!/usr/bin/env python3
"""Evidence for deck-auto-commit-ignores-card-files-other-than-readme-and-log.

Scaffolds a throwaway git repo, files a card, drops a `reproduce.py`
sibling into the card directory (exactly what `Skill(create-card)` Step 6
requires for bug-class cards), then runs `goc publish` — whose auto-commit
reports success. Prints what the resulting commit actually contains and
what `git status` still shows as untracked.

Also asserts the mechanism directly: `_git_auto_commit` iterates a
hardcoded filename pair, so no sibling file can ever be staged.

Run:   uv run python .game-of-cards/deck/<title>/reproduce.py
Exit 0 = defect reproduced; exit 1 = defect gone.
"""

from __future__ import annotations

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


ROOT = _repo_root()


def run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)


def goc(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return run([sys.executable, "-m", "goc.cli", *args], cwd)


def main() -> int:
    # --- Part 1: the mechanism, read straight off the source -------------
    engine = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8")
    hardcoded = 'for fname in ("README.md", "log.md")' in engine
    print("goc/engine.py _git_auto_commit stages a hardcoded filename pair")
    print(f'  \'for fname in ("README.md", "log.md")\' present : {hardcoded}')
    print()

    # --- Part 2: end-to-end, in a throwaway repo -------------------------
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer"
        deck = repo / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        run(["git", "init", "-q", "."], repo)
        run(["git", "config", "user.email", "probe@example.com"], repo)
        run(["git", "config", "user.name", "probe"], repo)
        # A first commit so HEAD exists and `git log` is meaningful.
        (repo / "README.md").write_text("probe repo\n")
        run(["git", "add", "--", "README.md"], repo)
        run(["git", "commit", "-q", "-m", "init", "--", "README.md"], repo)

        title = "probe-card-with-a-sibling-artifact"
        r = goc(["new", title, "--summary", "A probe card.", "--contribution", "low"], repo)
        if r.returncode != 0:
            print("goc new failed:", r.stdout, r.stderr)
            return 1

        card = deck / title
        # Author the card so `goc publish` accepts it (it refuses placeholders).
        readme = card / "README.md"
        text = readme.read_text(encoding="utf-8")
        text = text.replace(
            "  - [ ] (replace with real criteria)",
            "  - [ ] TDD: the probe asserts something real",
        ).replace("(write the design doc here)", "Real body prose for the probe card.")
        readme.write_text(text, encoding="utf-8")
        # The sibling artifact create-card Step 6 mandates for bug-class cards.
        (card / "reproduce.py").write_text("print('probe evidence')\n", encoding="utf-8")

        r = goc(["publish", title, "--commit"], repo)
        print("goc publish --commit output:")
        for line in (r.stdout + r.stderr).strip().splitlines():
            print(f"  {line}")
        print()

        committed = run(
            ["git", "show", "--name-only", "--format=", "HEAD"], repo
        ).stdout.split()
        untracked = run(
            ["git", "status", "--porcelain", "--untracked-files=all"], repo
        ).stdout.strip().splitlines()

        print("files in the commit goc publish created:")
        for f in committed:
            print(f"  {f}")
        print("git status after the 'committed' message:")
        for line in untracked or ["  (clean)"]:
            print(f"  {line.strip()}")
        print()

        sibling = f".game-of-cards/deck/{title}/reproduce.py"
        sibling_committed = sibling in committed
        sibling_untracked = any(sibling in ln for ln in untracked)

    print(f"sibling reproduce.py in the commit    : {sibling_committed}")
    print(f"sibling reproduce.py left untracked   : {sibling_untracked}")
    if hardcoded and sibling_untracked and not sibling_committed:
        print("\nDEFECT PRESENT — auto-commit reported success, evidence file untracked")
        return 0
    print("\nDEFECT GONE — auto-commit now stages sibling card files")
    return 1


if __name__ == "__main__":
    sys.exit(main())
