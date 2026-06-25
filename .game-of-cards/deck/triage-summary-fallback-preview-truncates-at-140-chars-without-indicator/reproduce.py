#!/usr/bin/env python3
"""Reproduce: `goc triage` summary-fallback preview hard-cuts at 140 chars
with no clip indicator, unlike the sibling decision_required branch which
advertises clipping with `… +N more lines (see goc show ...)`.

Builds an isolated deck with one parked card that has a long single-line
`summary` and NO `## Decision required` section (the fallback branch), runs
the engine's triage renderer, and prints the preview line.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import goc.engine as engine

LONG = (
    "This card needs a human decision about whether to adopt approach A or "
    "approach B for the new export pipeline, and the tradeoffs around latency, "
    "memory, and operational complexity are subtle enough that we should not "
    "auto-pick one without a maintainer weighing in on the rollout risk."
)

CARD = f"""---
title: long-summary-parked-card
status: open
stage: null
contribution: high
created: "2026-06-25T00:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] decide
summary: "{LONG}"
---

# long-summary-parked-card

No decision-required section here on purpose — exercises the summary fallback.
"""


def main():
    with tempfile.TemporaryDirectory() as td:
        deck = Path(td) / "deck"
        (deck / "long-summary-parked-card").mkdir(parents=True)
        (deck / "long-summary-parked-card" / "README.md").write_text(CARD)
        engine.DECK_DIR = deck

        class A:
            as_json = False
            worker = None

        buf = io.StringIO()
        with redirect_stdout(buf):
            engine._cmd_triage(A())
        out = buf.getvalue()

        preview = [l for l in out.splitlines() if l.strip().startswith(">")]
        line = preview[0] if preview else "(no preview line)"
        body = line.lstrip().lstrip(">").strip()

        print(f"summary length          : {len(LONG)} chars")
        print(f"preview body length     : {len(body)} chars")
        print(f"preview line            : {line!r}")
        ends_clean = body.endswith(LONG)
        advertises = "…" in line or "more" in line or "goc show" in line
        print(f"shows full summary?     : {ends_clean}")
        print(f"advertises the clip?    : {advertises}")
        if not ends_clean and not advertises:
            print("DEFECT: preview is silently truncated mid-text with no indicator.")
            sys.exit(1)
        print("OK: clip is advertised (or full summary shown).")


if __name__ == "__main__":
    main()
