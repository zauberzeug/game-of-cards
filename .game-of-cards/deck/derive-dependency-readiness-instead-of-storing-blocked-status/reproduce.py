"""Demonstrate that a card with an open `advanced_by` prereq is derived-blocked,
and that closing the prereq makes it derived-ready with no manual status flip
on the dependent.

Run from the repo root:

    uv run python .game-of-cards/deck/derive-dependency-readiness-instead-of-storing-blocked-status/reproduce.py
"""

from __future__ import annotations

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


_PREREQ_OPEN = """\
---
title: upstream-prereq
summary: Upstream prereq that gates the dependent.
status: open
stage: null
contribution: medium
created: 2026-05-01
closed_at: null
human_gate: none
advances:
  - dependent-card
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] stub
---

# upstream-prereq
"""

_PREREQ_DONE = _PREREQ_OPEN.replace("status: open", "status: done").replace(
    "closed_at: null", "closed_at: 2026-05-02"
).replace("- [ ] stub", "- [x] stub")

_DEPENDENT = """\
---
title: dependent-card
summary: Card whose readiness is derived from upstream-prereq.
status: open
stage: null
contribution: medium
created: 2026-05-01
closed_at: null
human_gate: none
advances: []
advanced_by:
  - upstream-prereq
tags: [bug]
definition_of_done: |
  - [ ] stub
---

# dependent-card
"""


def _write_deck(deck: Path, prereq_body: str) -> None:
    for name in ("upstream-prereq", "dependent-card"):
        d = deck / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "log.md").write_text("")
    (deck / "upstream-prereq" / "README.md").write_text(prereq_body)
    (deck / "dependent-card" / "README.md").write_text(_DEPENDENT)


def _ready_titles(cwd: Path, env: dict) -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--ready", "--json"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return [d["title"] for d in json.loads(result.stdout)]


def _dependent_blocked(cwd: Path, env: dict) -> tuple[bool, list[str]]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "open", "--json"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    for d in json.loads(result.stdout):
        if d["title"] == "dependent-card":
            return d["dependency_blocked"], d["blocked_by"]
    raise RuntimeError("dependent-card missing from open queue")


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        _write_deck(deck, _PREREQ_OPEN)

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"

        ready_before = _ready_titles(cwd, env)
        blocked_before, blockers_before = _dependent_blocked(cwd, env)
        print(f"prereq=open ready={ready_before} dep_blocked={blocked_before} blockers={blockers_before}")

        if "dependent-card" in ready_before:
            print("defect: dependent-card appears ready while prereq is still open")
            return 1
        if not blocked_before or blockers_before != ["upstream-prereq"]:
            print("defect: dependent-card is not derived-blocked by its open prereq")
            return 1

        _write_deck(deck, _PREREQ_DONE)

        ready_after = _ready_titles(cwd, env)
        blocked_after, blockers_after = _dependent_blocked(cwd, env)
        print(f"prereq=done ready={ready_after} dep_blocked={blocked_after} blockers={blockers_after}")

        if "dependent-card" not in ready_after:
            print("defect: dependent-card did not self-clear after prereq closed")
            return 1
        if blocked_after or blockers_after:
            print("defect: dependent-card still reports a blocker after prereq closed")
            return 1

    print("ok: derived dependency-readiness self-clears with no manual status flip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
