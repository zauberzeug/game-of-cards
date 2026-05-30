"""Reproducer: mutating verbs corrupt card state on --commit --no-commit conflict.

Goal: prove that `goc <verb> ... --commit --no-commit` writes the card's
README to disk BEFORE the argparse-style mutual-exclusion error is
emitted via `_commit_override → sys.exit(2)`.

Setup: a throwaway repo with one card (`probe-target` plus a sibling
`probe-target-2` so `advance` has a second endpoint). For each verb,
hash the README before, run the verb with both flags, then hash the
README after. Pre-fix: exit code == 2 AND hashes differ. Post-fix:
exit code == 2 AND hashes equal (validation must precede mutation).

Runs in isolation — never touches the consuming repo's own deck.
"""

import hashlib
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


SRC = _repo_root()


CARD_TEMPLATE = """---
title: {title}
summary: ""
status: open
stage: null
contribution: medium
created: "2026-05-30T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] (replace)
---

# {title}

body
"""


def _setup_temp_repo(tmp: Path) -> None:
    (tmp / "pyproject.toml").write_text('[project]\nname = "stub"\nversion = "0"\n')
    deck = tmp / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    for title in ("probe-target", "probe-target-2"):
        card_dir = deck / title
        card_dir.mkdir()
        (card_dir / "README.md").write_text(CARD_TEMPLATE.format(title=title))
        (card_dir / "log.md").write_text("")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("GOC_WORKTREE_DECK", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


VERBS = [
    ("wait",     ["wait",     "probe-target", "--reason", "external"]),
    ("status",   ["status",   "probe-target", "active"]),
    ("advance",  ["advance",  "probe-target", "--by", "probe-target-2"]),
    ("unadvance",["unadvance","probe-target", "--by", "probe-target-2"]),
    # `decide` requires gate != none; skipped here — its ordering bug
    # is co-located and the body documents the file:line; one verb is
    # enough to ground the reproducer.
]


def main() -> int:
    overall_failed = False
    for verb_name, verb_args in VERBS:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _setup_temp_repo(tmp)
            # `unadvance` only has an edge to remove if `advance` ran first;
            # set up a baseline edge so we observe the on-disk mutation.
            if verb_name == "unadvance":
                pre = _run(tmp, "advance", "probe-target", "--by", "probe-target-2")
                if pre.returncode != 0:
                    print(f"[{verb_name}] FAIL: setup advance returned "
                          f"{pre.returncode}: {pre.stderr.strip()}")
                    overall_failed = True
                    continue
            readme = tmp / ".game-of-cards" / "deck" / "probe-target" / "README.md"
            before = _hash(readme)
            res = _run(tmp, *verb_args, "--commit", "--no-commit")
            after = _hash(readme)
            ok_exit = res.returncode == 2
            ok_hash = before == after
            verdict = "PASS" if (ok_exit and ok_hash) else "FAIL"
            if not (ok_exit and ok_hash):
                overall_failed = True
            print(f"[{verb_name}] {verdict}: exit={res.returncode} "
                  f"hash_eq={ok_hash}")
            if not ok_hash:
                print(f"  before={before[:12]} after={after[:12]}")
                print(f"  stderr: {res.stderr.strip()}")
    return 1 if overall_failed else 0


if __name__ == "__main__":
    sys.exit(main())
