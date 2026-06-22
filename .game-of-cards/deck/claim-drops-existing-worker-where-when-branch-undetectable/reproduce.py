#!/usr/bin/env python3
"""Reproduce: claiming a card on a detached HEAD drops a stored worker.where.

Builds a card carrying `worker: {who: alice, where: feature/foo}`, puts a git
tree into a detached-HEAD state (so `git rev-parse --abbrev-ref HEAD` -> "HEAD"),
and runs `_auto_populate_worker` with no --worker-where flag. The stored
`where` is silently dropped instead of preserved.

Run from the repo root:  python .game-of-cards/deck/claim-drops-existing-worker-where-when-branch-undetectable/reproduce.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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


def main() -> int:
    with tempfile.TemporaryDirectory() as w, tempfile.TemporaryDirectory() as h:
        work, home = Path(w), Path(h)
        env = dict(os.environ, HOME=str(home))
        _git(["init", "-q"], work, env)
        _git(["checkout", "-q", "-b", "main"], work, env)
        (work / "f").write_text("x")
        _git(["-c", "user.name=alice", "-c", "user.email=a@e", "add", "f"], work, env)
        _git(["-c", "user.name=alice", "-c", "user.email=a@e", "commit", "-qm", "init"], work, env)
        # Detach HEAD so `rev-parse --abbrev-ref HEAD` prints "HEAD".
        head = _git(["rev-parse", "HEAD"], work, env).stdout.strip()
        _git(["checkout", "-q", head], work, env)
        # Make `who` auto-detectable so the worker is stamped at all.
        _git(["config", "--global", "user.name", "alice"], work, env)

        abbrev = _git(["rev-parse", "--abbrev-ref", "HEAD"], work, env).stdout.strip()
        print(f"git rev-parse --abbrev-ref HEAD  -> {abbrev!r}")

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

        fm, _ = engine.parse_frontmatter(out)
        got = fm.get("worker")
        expected = {"who": "alice", "where": "feature/foo"}
        print(f"stored worker before claim : {{'who': 'alice', 'where': 'feature/foo'}}")
        print(f"worker after claim (no flag): {got!r}")
        print(f"expected (where preserved) : {expected!r}")

        if got == expected:
            print("\nPASS: worker.where preserved — bug fixed.")
            return 0
        print("\nFAIL: worker.where was dropped — data loss on detached-HEAD claim.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
