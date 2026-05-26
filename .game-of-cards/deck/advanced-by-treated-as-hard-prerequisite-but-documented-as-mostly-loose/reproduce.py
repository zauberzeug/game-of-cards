"""Demonstrate that `advanced-by-closed` correctly FAILs closure of a card
whose `advanced_by` includes a non-terminal upstream, and that the two
honest resolutions both work:

1. wait — the FAIL clears when the upstream closes; and
2. retract — `goc unadvance <closing> --by <upstream>` removes a false
   edge and lets the closing card pass the check.

This card is about the *semantics* of the existing check, not its
mechanics; the check logic is unchanged. The reproduce exercises both
paths against a fresh temp deck so the value-chain rule documented on
`Skill(card-schema)` is empirically anchored.

Run from the repo root:

    uv run python .game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/reproduce.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


_CONFIG_YAML = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
  - name: dod-100-percent
    kind: derived
  - name: log-md-closure-entry
    kind: derived
workflow:
  auto_commit: false
"""


def _upstream(status: str) -> str:
    closed_at = "null" if status == "open" else "2026-05-01"
    return f"""\
---
title: upstream-prereq
summary: Upstream that gates the closing card's value chain.
status: {status}
stage: null
contribution: medium
created: 2026-05-01
closed_at: {closed_at}
human_gate: none
advances:
  - closing-card
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] stub
---

# upstream-prereq
"""


_CLOSING_WITH_EDGE = """\
---
title: closing-card
summary: Card the operator is trying to close while upstream is still open.
status: active
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
  - [x] work complete
---

# closing-card
"""


_CLOSING_WITHOUT_EDGE = _CLOSING_WITH_EDGE.replace(
    "advanced_by:\n  - upstream-prereq\n",
    "advanced_by: []\n",
)


def _write_deck(deck: Path, upstream_status: str, closing_body: str) -> None:
    for name in ("upstream-prereq", "closing-card"):
        d = deck / name
        d.mkdir(parents=True, exist_ok=True)
    (deck / "upstream-prereq" / "README.md").write_text(_upstream(upstream_status))
    (deck / "upstream-prereq" / "log.md").write_text("")
    (deck / "closing-card" / "README.md").write_text(closing_body)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (deck / "closing-card" / "log.md").write_text(
        f"## {today} — Closure\n\n- **What changed**: stub.\n"
    )


def _run_attest(cwd: Path, env: dict) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "attest", "closing-card"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def _run_unadvance(cwd: Path, env: dict) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "unadvance", "closing-card", "--by", "upstream-prereq"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / ".game-of-cards").mkdir()
        (cwd / ".game-of-cards" / "config.yaml").write_text(_CONFIG_YAML)
        deck = cwd / ".game-of-cards" / "deck"
        deck.mkdir()

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(repo) if not pythonpath else f"{repo}{os.pathsep}{pythonpath}"

        # Scenario A: closing-card.advanced_by = [upstream-prereq], upstream still open.
        # advanced-by-closed MUST FAIL.
        _write_deck(deck, upstream_status="open", closing_body=_CLOSING_WITH_EDGE)
        rc_a, out_a = _run_attest(cwd, env)
        print(f"-- scenario A: attest while upstream open --\nexit={rc_a}\n{out_a}")
        if rc_a == 0:
            print("defect: attest passed while upstream was open")
            return 1
        if "advanced-by-closed" not in out_a or "not done" not in out_a:
            print("defect: attest output did not name advanced-by-closed failure")
            return 1
        if "goc unadvance closing-card --by" not in out_a:
            print("defect: failure message did not name the retract resolution")
            return 1

        # Scenario B (resolution path 1 — wait): upstream closes; re-attest passes
        # without touching the edge. Reset the closing-card body to clear the
        # prior attestation block we just appended to log.md, then mark the
        # upstream done.
        _write_deck(deck, upstream_status="done", closing_body=_CLOSING_WITH_EDGE)
        rc_b, out_b = _run_attest(cwd, env)
        print(f"-- scenario B: attest after upstream closed (wait path) --\nexit={rc_b}\n{out_b}")
        if rc_b != 0:
            print("defect: attest still failed after upstream closed")
            return 1
        if "advanced-by-closed" not in out_b:
            print("defect: attest did not report advanced-by-closed")
            return 1

        # Scenario C (resolution path 2 — retract): upstream still open, but the
        # edge was false. `goc unadvance` retracts it; attest then passes.
        _write_deck(deck, upstream_status="open", closing_body=_CLOSING_WITH_EDGE)
        rc_pre, out_pre = _run_attest(cwd, env)
        if rc_pre == 0:
            print(f"defect: precondition for scenario C — expected FAIL, got pass\n{out_pre}")
            return 1
        if _run_unadvance(cwd, env) != 0:
            print("defect: goc unadvance failed")
            return 1
        rc_c, out_c = _run_attest(cwd, env)
        print(f"-- scenario C: attest after retracting false edge --\nexit={rc_c}\n{out_c}")
        if rc_c != 0:
            print("defect: attest failed after the false edge was retracted")
            return 1
        if "no advanced_by edges" not in out_c:
            print("defect: advanced-by-closed should report no edges after retract")
            return 1

    print("ok: advanced-by-closed FAILs on open upstream; both wait and unadvance resolve it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
