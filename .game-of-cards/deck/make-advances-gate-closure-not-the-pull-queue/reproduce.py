"""Demonstrate that `advances` no longer hard-gates the pull queue, while
a `waiting_on` impediment still does.

A card with an open `advances` prereq surfaces in `--ready` (the advisory
"awaiting: <prereqs>" line is shown for context). A card with an active
`waiting_on` overlay is hidden from `--ready` until cleared.

Run from the repo root:

    uv run python .game-of-cards/deck/make-advances-gate-closure-not-the-pull-queue/reproduce.py
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


_UPSTREAM_OPEN = """\
---
title: upstream-prereq
summary: Upstream contributor that lends priority but does not start-gate.
status: open
stage: null
contribution: medium
created: 2026-05-26
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

_DEPENDENT = """\
---
title: dependent-card
summary: Has an open `advances` prereq — should still appear in --ready.
status: open
stage: null
contribution: medium
created: 2026-05-26
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

_WAITING_CARD = """\
---
title: waiting-card
summary: Carries an active `waiting_on` impediment — should NOT appear in --ready.
status: open
stage: null
contribution: medium
created: 2026-05-26
closed_at: null
human_gate: none
advances: []
advanced_by: []
waiting_on: external
waiting_until: 2099-01-01
tags: [bug]
definition_of_done: |
  - [ ] stub
---

# waiting-card
"""


def _write_deck(deck: Path) -> None:
    for name, body in (
        ("upstream-prereq", _UPSTREAM_OPEN),
        ("dependent-card", _DEPENDENT),
        ("waiting-card", _WAITING_CARD),
    ):
        d = deck / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "log.md").write_text("")
        (d / "README.md").write_text(body)


def _ready(cwd: Path, env: dict) -> list[dict]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--ready", "--json"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def _open(cwd: Path, env: dict) -> list[dict]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--status", "open", "--json"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        deck = cwd / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        _write_deck(deck)

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"

        ready = _ready(cwd, env)
        ready_titles = [d["title"] for d in ready]
        print(f"--ready titles: {ready_titles}")

        if "dependent-card" not in ready_titles:
            print("defect: dependent-card is NOT in --ready despite advances-only block")
            return 1
        if "waiting-card" in ready_titles:
            print("defect: waiting-card appears in --ready while waiting_on is active")
            return 1
        if "upstream-prereq" not in ready_titles:
            print("defect: upstream-prereq missing from --ready (no prereq itself)")
            return 1

        open_cards = {d["title"]: d for d in _open(cwd, env)}
        dep = open_cards["dependent-card"]

        if not dep["dependency_awaiting"]:
            print("defect: dependent-card's advisory dependency_awaiting flag dropped")
            return 1
        if dep["awaiting"] != ["upstream-prereq"]:
            print(f"defect: dependent-card.awaiting was {dep['awaiting']!r}, expected ['upstream-prereq']")
            return 1
        if not dep["ready"]:
            print("defect: dependent-card.ready is False despite no impediment")
            return 1

        waiting = open_cards["waiting-card"]
        if waiting["ready"]:
            print("defect: waiting-card.ready is True while waiting_on is active")
            return 1

    print("ok: advances is advisory; waiting_on hard-gates the pull queue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
