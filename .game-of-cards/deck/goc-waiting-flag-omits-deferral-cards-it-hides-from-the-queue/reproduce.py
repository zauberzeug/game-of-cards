#!/usr/bin/env python3
"""Reproduce: `goc --waiting` diverges from the `waiting_impedes` predicate.

The `--waiting` filter (engine.py `_cmd_list`) keeps a card iff
`waiting_on is not None`. The canonical "is this card impeded right now?"
predicate is `waiting_impedes(card)`, used by `card_is_ready`, the board
⏳ marker, and the leverage line. The two disagree:

  * UNDER-inclusion: a bare deferral set with `goc wait <t> --until <future>`
    (no `--reason`, a supported CLI form) has `waiting_on=None` but
    `waiting_impedes` is True — hidden from `--ready`, shown ⏳ on the board,
    yet INVISIBLE to `goc --waiting`.
  * OVER-inclusion: an elapsed wait (`waiting_on` set, `waiting_until` in the
    past) has `waiting_impedes` False — it has RE-ENTERED the queue — yet
    `--waiting` still lists it because `waiting_on is not None`.

This script builds a throwaway deck, exercises the real CLI, and asserts that
the set `goc --waiting` returns equals the set of cards `waiting_impedes`
considers impeded. It exits non-zero while the defect fires, zero once fixed.
"""
import json
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

from goc import engine  # noqa: E402


def goc(workdir: Path, *args: str) -> str:
    env = dict(os.environ, PYTHONPATH=str(REPO))
    res = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(workdir), env=env, capture_output=True, text=True,
    )
    return res.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        (work / ".game-of-cards" / "deck").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=str(work), check=True)

        # bare deferral: --until only, no --reason (impeded, waiting_on=None)
        goc(work, "new", "bare-deferral", "--no-commit")
        goc(work, "wait", "bare-deferral", "--until", "2099-12-31", "--no-commit")
        # open-ended block: --reason only (impeded)
        goc(work, "new", "open-block", "--no-commit")
        goc(work, "wait", "open-block", "--reason", "external", "--no-commit")
        # elapsed wait: reason + past date (NOT impeded — has resurfaced)
        goc(work, "new", "elapsed-wait", "--no-commit")
        goc(work, "wait", "elapsed-wait", "--reason", "external",
            "--until", "2020-01-01", "--no-commit")

        waiting_titles = {
            c["title"] for c in json.loads(goc(work, "--waiting", "--json"))
        }

        deck = work / ".game-of-cards" / "deck"
        impeded = {
            d.name for d in deck.iterdir()
            if d.is_dir() and engine.waiting_impedes(engine.load_card(d))
        }

    print(f"goc --waiting returns : {sorted(waiting_titles)}")
    print(f"waiting_impedes True  : {sorted(impeded)}")
    missing = impeded - waiting_titles
    extra = waiting_titles - impeded
    if missing:
        print(f"UNDER-included (impeded but absent from --waiting): {sorted(missing)}")
    if extra:
        print(f"OVER-included  (in --waiting but not impeded)     : {sorted(extra)}")

    if waiting_titles == impeded:
        print("PASS: --waiting matches the waiting_impedes predicate")
        return 0
    print("FAIL: --waiting diverges from waiting_impedes")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
