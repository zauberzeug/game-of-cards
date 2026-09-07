#!/usr/bin/env python3
"""Reproduce: `goc new` mkdirs before it can emit, so an inline-emitter refusal
leaves an orphan card directory and a raw traceback.

Exits 0 when the defect is FIXED (clean `ERROR:` line, exit 2, deck untouched),
1 while it still fires.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
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

# (label, `goc new` flags) — each value carries a line break the inline emitter
# refuses. CR is the realistic door: command substitution strips a trailing LF
# but not a trailing CR, so `--worker "$(cat name.txt)"` on a CRLF file hands
# `goc new` a value no human typed.
CASES = [
    ("summary-with-CR", ["--summary", "first\rsecond"]),
    ("worker-with-CR", ["--summary", "fine", "--worker", "alice\r"]),
    ("worker-with-LF", ["--summary", "fine", "--worker", "alice\nbob"]),
]


def _run(deck_repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=deck_repo,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    failures: list[str] = []
    for label, flags in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".game-of-cards" / "deck").mkdir(parents=True)
            title = f"probe-{label.lower().replace('_', '-')}"

            proc = _run(repo, ["new", title, *flags])
            card_dir = repo / ".game-of-cards" / "deck" / title

            traceback_leaked = "Traceback (most recent call last)" in proc.stderr
            clean_error = proc.stderr.startswith("ERROR:")
            orphan = card_dir.is_dir()
            missing_readme = orphan and not (card_dir / "README.md").exists()

            # A deck carrying the orphan is validate-red.
            validate = _run(repo, ["validate"])
            validate_red = f"{title}: card directory missing README.md" in (
                validate.stdout + validate.stderr
            )

            print(f"--- {label} ---")
            print(f"  argv          : goc new {title} {' '.join(map(repr, flags))}")
            print(f"  exit code     : {proc.returncode}   (contract: 2)")
            print(f"  traceback     : {traceback_leaked}   (contract: False)")
            print(f"  clean ERROR:  : {clean_error}   (contract: True)")
            print(f"  orphan dir    : {orphan}   (contract: False)")
            print(f"  no README.md  : {missing_readme}   (contract: False)")
            print(f"  validate red  : {validate_red}   (contract: False)")
            if proc.stderr.strip():
                last = proc.stderr.strip().splitlines()[-1]
                print(f"  last stderr   : {last[:120]}")
            print()

            if traceback_leaked or not clean_error:
                failures.append(f"{label}: refusal is not the CLI's clean `ERROR:` contract")
            if proc.returncode != 2:
                failures.append(f"{label}: exit {proc.returncode}, expected 2")
            if orphan:
                failures.append(f"{label}: left an orphan card directory behind")
            if validate_red:
                failures.append(f"{label}: goc validate is red because of the orphan")

    if failures:
        print("FAIL: `goc new` breaks its refusal contract and corrupts the deck:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PASS: every refused value flag exits 2 with a clean ERROR: and leaves no directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
