#!/usr/bin/env python3
"""Prove that `goc move` leaves a ghost copy of the renamed card in HEAD.

Run: uv run python .game-of-cards/deck/card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck/reproduce.py

Three parts:

1. `goc move OLD NEW` followed by any auto-committing verb leaves BOTH
   card directories in HEAD — the source-side deletion `git mv` staged is
   never committed, because every commit the engine makes is pathspec-scoped
   and `_git_auto_commit` builds its pathspec by filtering on `.exists()`.
2. A fresh clone of that repository carries both cards. `goc validate`
   reports both OK and the queue offers the renamed-away card as pullable
   work — the corruption is invisible in the worktree that caused it.
3. The fix sketched on the sibling card
   `goc-move-leaves-cross-reference-rewrites-uncommitted`
   (`_git_auto_commit([dst, *rewrite_dirs], ...)`) does NOT close this:
   applied verbatim, the ghost still lands in HEAD.

Exits 1 while the defect reproduces, 0 once it is fixed.
"""

from __future__ import annotations

import os
import shutil
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
sys.path.insert(0, str(ROOT))

ENV = {**os.environ, "PYTHONPATH": str(ROOT), "GIT_CONFIG_NOSYSTEM": "1"}
CARD_DOD = "  - [ ] (replace with real criteria)\n"
CARD_BODY = "(write the design doc here)"


def run(args: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd), env=ENV, capture_output=True, text=True, check=check)


def goc(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return run([sys.executable, "-m", "goc.cli", *args], cwd)


def git(args: list[str], cwd: Path) -> str:
    return run(["git", *args], cwd).stdout.strip()


def make_repo(tmp: Path) -> Path:
    repo = tmp / "consumer"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "main", "."], repo)
    run(["git", "config", "user.email", "probe@example.com"], repo)
    run(["git", "config", "user.name", "probe"], repo)
    goc(["install", "--local-skills", "--claude"], repo)
    run(["git", "add", "-A"], repo)
    run(["git", "commit", "-qm", "scaffold"], repo)

    goc(["new", "original-card-title", "--summary", "A card."], repo)
    readme = repo / ".game-of-cards" / "deck" / "original-card-title" / "README.md"
    readme.write_text(
        readme.read_text()
        .replace(CARD_DOD, "  - [ ] MECHANICAL: a real criterion\n")
        .replace(CARD_BODY, "A real body.")
    )
    goc(["publish", "original-card-title"], repo)
    return repo


def deck_paths_in_head(repo: Path) -> list[str]:
    listing = git(["ls-tree", "-r", "--name-only", "HEAD"], repo).splitlines()
    return sorted(p for p in listing if "/deck/" in p and p.endswith("README.md"))


def part1() -> bool:
    print("=" * 72)
    print("PART 1 — goc move + the next auto-committing verb")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as td:
        repo = make_repo(Path(td))
        print(f"HEAD before move: {deck_paths_in_head(repo)}")

        goc(["move", "original-card-title", "better-card-title"], repo)
        print("\n`goc move original-card-title better-card-title` ran.")
        print("index after move (git diff --cached --name-status):")
        for line in git(["diff", "--cached", "--name-status"], repo).splitlines():
            print(f"  {line}")

        goc(["status", "better-card-title", "active"], repo)
        print("\n`goc status better-card-title active` ran (auto-commits).")
        head = deck_paths_in_head(repo)
        print(f"HEAD after: {head}")
        print("index residue (never committed):")
        for line in git(["diff", "--cached", "--name-status"], repo).splitlines():
            print(f"  {line}")

        ghost = any("original-card-title" in p for p in head)
        renamed = any("better-card-title" in p for p in head)
        print(f"\n  ghost old card in HEAD:  {ghost}")
        print(f"  renamed card in HEAD:    {renamed}")
        return ghost and renamed


def part2() -> bool:
    print()
    print("=" * 72)
    print("PART 2 — what a teammate who clones actually gets")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        repo = make_repo(tmp)
        goc(["move", "original-card-title", "better-card-title"], repo)
        goc(["status", "better-card-title", "active"], repo)

        clone = tmp / "clone"
        run(["git", "clone", "-q", str(repo), str(clone)], tmp)
        deck = clone / ".game-of-cards" / "deck"
        dirs = sorted(p.name for p in deck.iterdir() if p.is_dir())
        print(f"card directories in the clone: {dirs}")

        validate = goc(["validate"], clone)
        print("\n`goc validate` in the clone:")
        for line in validate.stdout.strip().splitlines()[-4:]:
            print(f"  {line}")

        queue = goc([], clone)
        print("\n`goc` (the pullable queue) in the clone:")
        for line in queue.stdout.strip().splitlines():
            print(f"  {line}")

        duplicated = "original-card-title" in dirs and "better-card-title" in dirs
        offered = "original-card-title" in queue.stdout
        print(f"\n  both copies present in the clone: {duplicated}")
        print(f"  renamed-away card offered as pullable work: {offered}")
        print(f"  goc validate exit code: {validate.returncode} (0 = reports the deck clean)")
        return duplicated and offered and validate.returncode == 0


def part3() -> bool:
    print()
    print("=" * 72)
    print("PART 3 — the sibling card's Option A fix sketch, applied verbatim")
    print("=" * 72)
    with tempfile.TemporaryDirectory() as td:
        repo = make_repo(Path(td))
        goc(["move", "original-card-title", "better-card-title"], repo)

        # `_git_auto_commit([dst, *rewrite_dirs], f"deck: rename OLD → NEW")`
        # exactly as sketched on goc-move-leaves-cross-reference-rewrites-uncommitted.
        driver = (
            "import os, sys\n"
            f"sys.path.insert(0, {str(ROOT)!r})\n"
            f"os.chdir({str(repo)!r})\n"
            "from goc import engine\n"
            "dst = engine.DECK_DIR / 'better-card-title'\n"
            "print('committed:', engine._git_auto_commit("
            "[dst], 'deck: rename original-card-title -> better-card-title'))\n"
        )
        out = run([sys.executable, "-c", driver], repo)
        print(out.stdout.strip() or out.stderr.strip())

        head = deck_paths_in_head(repo)
        print(f"HEAD after the Option-A-style commit: {head}")
        ghost = any("original-card-title" in p for p in head)
        print(f"\n  ghost STILL in HEAD after the sketched fix: {ghost}")
        print("  cause: _git_auto_commit builds its pathspec with `if (p := d / fname).exists()`")
        print("         (goc/engine.py:4677-4682) — a deleted path can never enter it.")
        return ghost


def main() -> int:
    if shutil.which("git") is None:
        print("git not available", file=sys.stderr)
        return 2
    results = [part1(), part2(), part3()]
    print()
    print("=" * 72)
    labels = ["ghost survives the next auto-commit", "clone sees two cards", "sketched fix does not help"]
    for label, ok in zip(labels, results):
        print(f"  [{'FAIL' if ok else ' ok '}] {label}")
    if any(results):
        print("\nDEFECT REPRODUCES — goc move leaves a duplicate of the old card in the shared deck.")
        return 1
    print("\nFIXED — the rename leaves exactly one card directory in HEAD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
