#!/usr/bin/env python3
"""Prove `_auto_populate_worker` self-corrupts a card on `goc status active`.

When a card has no prior `worker` field and is claimed on a machine where
`git config user.name` is empty/unset BUT the working tree is on a real named
branch, `_auto_populate_worker` builds `worker: {who: "", where: <branch>}` by
hand. That mapping has an empty `who`, which `validate_card` rejects — so the
claim silently writes a card that immediately fails `goc validate`.

Run: uv run python deck/<title>/reproduce.py
Exit 0 == defect reproduced (bug present); exit 1 == defect gone (fixed).
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


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD_TEXT = """---
title: demo-card
summary: "x"
status: open
contribution: medium
created: 2026-06-06
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] x
---

# demo
"""


def main() -> int:
    # A temp git repo with one commit on branch `main` and NO user.name set,
    # so `git config user.name` -> "" while `git rev-parse --abbrev-ref HEAD`
    # -> "main". This is a stock CI/container checkout where identity is passed
    # per-commit rather than stored in config.
    with tempfile.TemporaryDirectory() as work, tempfile.TemporaryDirectory() as home:
        env = dict(os.environ, HOME=home)
        run = lambda *a: subprocess.run(["git", *a], cwd=work, env=env,
                                        capture_output=True, text=True)
        run("init", "-q")
        run("checkout", "-q", "-b", "main")
        (Path(work) / "f").write_text("x")
        run("-c", "user.name=tmp", "-c", "user.email=tmp@e", "add", "f")
        run("-c", "user.name=tmp", "-c", "user.email=tmp@e", "commit", "-qm", "init")
        # Leave user.name unset in both local and global config.
        run("config", "--global", "--unset", "user.name")
        run("config", "--local", "--unset", "user.name")

        name = run("config", "user.name").stdout.strip()
        branch = run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        print(f"git user.name = {name!r}; branch = {branch!r}")

        fm, body = engine.parse_frontmatter(CARD_TEXT)
        card = type("C", (), {"frontmatter": fm})()

        cwd = os.getcwd()
        os.chdir(work)  # _auto_populate_worker shells out to git in cwd
        try:
            out = engine._auto_populate_worker(CARD_TEXT, card, None, None)
        finally:
            os.chdir(cwd)

        worker_line = next((l for l in out.splitlines() if l.startswith("worker")), None)
        print(f"emitted worker line: {worker_line!r}")

        new_fm, new_body = engine.parse_frontmatter(out)
        worker_val = new_fm.get("worker")
        print(f"re-parsed worker  : {worker_val!r}")

        # Now validate the resulting card the way `goc validate` would.
        schema = engine.load_schema()
        card_obj = engine.Card(
            title="demo-card",
            path=Path(work) / "README.md",
            frontmatter=new_fm,
            body=new_body,
            dod_open=1,
            dod_done=0,
        )
        errors = engine.validate_card(card_obj, schema, {"demo-card"})
        worker_errors = [e for e in errors if "worker" in e]
        print(f"validate_card worker errors: {worker_errors}")

        corrupt = (
            isinstance(worker_val, dict)
            and worker_val.get("who", "x") == ""
            and bool(worker_errors)
        )
        if corrupt:
            print("DEFECT REPRODUCED: claim stamped an invalid empty-`who` worker "
                  "that fails goc validate.")
            return 0
        print("No defect: worker was not stamped with an empty `who`.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
