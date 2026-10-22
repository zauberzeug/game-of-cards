"""Reproduce: one card whose bytes do not decode crashes deck views unnamed.

Builds a scratch deck with a healthy card and a card whose README.md holds a
single Latin-1 byte (0xE9) in its summary, then runs the goc commands that
read the whole deck, plus `show` on the bad card. Python's UTF-8 mode is
forced so the byte is undecodable on any host.

A command handles the bad card when it exits without a Python traceback and
its output names the bad card. `validate` must also exit non-zero, and the
deck views must still list the healthy card: one broken card must not blank
the queue (`load_all_cards`).

Exits non-zero while any command fails that check.
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

CARD = (
    "---\n"
    "title: {title}\n"
    'summary: "{summary}"\n'
    "status: open\n"
    "stage: null\n"
    "contribution: medium\n"
    'created: "2026-10-10T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] TDD: fixture\n"
    "---\n\n"
    "# {title}\n"
)

# (argv, must exit non-zero, must still list the healthy card)
COMMANDS = [
    (["validate"], True, False),
    ([], False, True),
    (["--json"], False, True),
    (["--board"], False, True),
    (["triage"], False, False),
    (["show", "bad-bytes"], False, False),
]


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        deck = scratch / ".game-of-cards" / "deck"
        for title, summary in (("healthy-card", "fine"), ("bad-bytes", "caf\xe9")):
            card = deck / title
            card.mkdir(parents=True)
            text = CARD.format(title=title, summary=summary)
            (card / "README.md").write_bytes(text.encode("latin-1"))
            (card / "log.md").write_text("")

        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1")
        for argv, must_fail, must_list in COMMANDS:
            proc = subprocess.run(
                [sys.executable, "-m", "goc.cli", *argv],
                cwd=scratch, env=env, capture_output=True, text=True,
            )
            output = proc.stdout + proc.stderr
            problems = []
            if "Traceback (most recent call last)" in proc.stderr:
                last = proc.stderr.strip().splitlines()[-1]
                problems.append(f"traceback ({last})")
            if "bad-bytes" not in output:
                problems.append("never names the bad card")
            if must_fail and proc.returncode == 0:
                problems.append("exits 0")
            if must_list and "healthy-card" not in proc.stdout:
                problems.append("drops the healthy card")
            label = "goc " + " ".join(argv) if argv else "goc (bare queue)"
            if problems:
                failures += 1
                print(f"[FAIL] {label}: exit {proc.returncode}; " + "; ".join(problems))
            else:
                print(f"[OK]   {label}: exit {proc.returncode}")

    if failures:
        print(f"{failures} of {len(COMMANDS)} commands mishandle a card whose bytes do not decode.")
        return 1
    print("Every command names the undecodable card and keeps working.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
