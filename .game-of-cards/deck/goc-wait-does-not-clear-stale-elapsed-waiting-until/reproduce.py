#!/usr/bin/env python3
"""Falsification recipe for `goc-wait-does-not-clear-stale-elapsed-waiting-until`.

Drives the real `goc wait` CLI against a scratch deck rather than calling the
predicate directly, so the result is a claim about the shipped verb.

Hypothesis: `goc wait <card> --reason external` (no `--until`) writes
`waiting_on` but leaves a pre-existing *elapsed* `waiting_until` in place. An
elapsed date always resurfaces a card, so the freshly-set open-ended wait is
silently ignored and the card stays pullable.

Prints a verdict for each of the three overlay shapes in the card's table.
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))

CARD = """---
title: scratch-card
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
draft: false
summary: Scratch card used only by this reproduce script.
waiting_until: {until}
definition_of_done: |
  - [ ] MECHANICAL: nothing; scratch card.
---

# Scratch card
"""


def build(tmp: Path, until: str) -> Path:
    d = tmp / ".game-of-cards" / "deck" / "scratch-card"
    d.mkdir(parents=True)
    (d / "README.md").write_text(CARD.format(until=until))
    (d / "log.md").write_text("")
    (tmp / ".game-of-cards" / "config.yaml").write_text("skills_source: plugin\n")
    return d


def probe(label: str, until: str, run_wait: bool) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        build(tmp, until)
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        if run_wait:
            r = subprocess.run(
                [sys.executable, "-m", "goc.cli", "wait", "scratch-card", "--reason", "external"],
                cwd=tmp, env=env, capture_output=True, text=True,
            )
            if r.returncode != 0:
                print(f"  {label}: goc wait failed rc={r.returncode}: {r.stderr.strip()[:200]}")
                return

        # Re-read through the engine, rooted at the scratch deck.
        code = (
            "import sys, json; sys.path.insert(0, %r)\n"
            "import goc.engine as e\n"
            "from pathlib import Path\n"
            "c = e.load_card(Path('.game-of-cards/deck/scratch-card'))\n"
            "print(json.dumps({'waiting_on': c.waiting_on, 'waiting_until': str(c.waiting_until),\n"
            "                  'impedes': e.waiting_impedes(c), 'ready': e.card_is_ready(c, {c.title: c})}))\n"
        ) % str(ROOT)
        r = subprocess.run([sys.executable, "-c", code], cwd=tmp, env=env,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  {label}: probe failed: {r.stderr.strip()[-300:]}")
            return
        print(f"  {label}: {r.stdout.strip()}")


print("=== goc wait --reason external over an elapsed waiting_until ===")
probe("elapsed date + fresh reason  ", "2020-01-01", True)
print("=== controls ===")
probe("no stored date + fresh reason", "null", True)
probe("elapsed date, no reason      ", "2020-01-01", False)
print()
print("Defect shape: row 1 shows impedes=False / ready=True — the wait no-ops.")
print("Row 2 (impedes=True) is the control proving `goc wait` itself works.")
