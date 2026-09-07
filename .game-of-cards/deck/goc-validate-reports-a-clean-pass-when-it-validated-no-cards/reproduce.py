#!/usr/bin/env python3
"""`goc validate` cannot say it validated nothing.

Runs the real CLI against three decks and prints, for each, the exact bytes
on stdout/stderr plus the exit code:

  A. the repo's own deck (708 cards)  — the "gate really ran" case
  B. a scaffolded but empty deck      — `goc install` on a fresh repo
  C. no deck directory at all         — wrong cwd / unscaffolded checkout

B and C are the interesting pair: both are states in which the
frontmatter-drift gate checked zero cards, and both render byte-identically
to "nothing to report" at exit 0. A caller (CI step, pre-commit hook, human)
that reads exit 0 as "the deck is clean" is reading a false green.

Exits 1 while the defect fires (B or C produce no output), 0 once every run
states its outcome.
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


def run_validate(cwd: Path) -> tuple[int, str, str]:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    r = subprocess.run(
        [sys.executable, "-m", "goc.cli", "validate"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    return r.returncode, r.stdout, r.stderr


def describe(label: str, cwd: Path) -> tuple[int, int]:
    rc, out, err = run_validate(cwd)
    print(f"--- {label}")
    print(f"    cwd        : {cwd}")
    print(f"    exit code  : {rc}")
    print(f"    stdout     : {len(out)} bytes")
    print(f"    stderr     : {len(err)} bytes")
    head = (out or err).splitlines()[:1]
    print(f"    first line : {head[0] if head else '(none)'}")
    return len(out), len(err)


def main() -> int:
    print("goc validate — output on decks that contain no cards\n")

    describe("A. repo's own deck (708 cards)", ROOT)
    print()

    findings = 0
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "scaffolded-empty"
        (empty / ".game-of-cards" / "deck").mkdir(parents=True)
        out_b, err_b = describe("B. scaffolded but empty deck", empty)
        print()

        bare = Path(tmp) / "no-deck-at-all"
        bare.mkdir()
        out_c, err_c = describe("C. no deck directory at all", bare)
        print()

    if out_b + err_b == 0:
        findings += 1
        print("FINDING: B printed 0 bytes — a deck with no cards is silent.")
    if out_c + err_c == 0:
        findings += 1
        print("FINDING: C printed 0 bytes — a MISSING deck is silent too;")
        print("         `goc validate` reports success for a deck it never found.")

    print(f"\n{findings} finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
