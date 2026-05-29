"""Reproduce: `goc triage` silently omits active+gated cards.

Builds a synthetic 3-card deck inside a temp directory:

  - card-a: status=open,   human_gate=decision  (expected in triage)
  - card-b: status=active, human_gate=decision  (parked; should show up)
  - card-c: status=active, human_gate=none      (should NOT show up)

Then runs `uv run goc triage --json` against that deck and prints the
list of titles that appeared. The bug: card-b is missing.
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


REPO_ROOT = _repo_root()


CARD_TEMPLATE = """---
title: {title}
summary: ""
status: {status}
stage: null
contribution: medium
created: "2026-05-29T17:00:00Z"
closed_at: null
human_gate: {gate}
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: placeholder
---

# {title}

## Decision required

Placeholder decision body so triage can render the preview.
"""


def scaffold(deck_dir: Path, title: str, status: str, gate: str) -> None:
    card = deck_dir / title
    card.mkdir(parents=True)
    (card / "README.md").write_text(
        CARD_TEMPLATE.format(title=title, status=status, gate=gate)
    )
    (card / "log.md").write_text("")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        # Minimum config the engine looks for.
        (root / ".game-of-cards" / "config.yaml").write_text("skills_source: vendored\n")
        # A pyproject.toml so the engine treats this as a repo root.
        (root / "pyproject.toml").write_text('[project]\nname = "fixture"\nversion = "0"\n')

        scaffold(deck, "card-a-open-gated", "open", "decision")
        scaffold(deck, "card-b-active-gated", "active", "decision")
        scaffold(deck, "card-c-active-clear", "active", "none")

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "triage", "--json"],
            cwd=root,
            capture_output=True,
            text=True,
            env=env,
        )

    if result.returncode != 0:
        print("goc triage failed:", result.stderr, file=sys.stderr)
        return 1

    payload = json.loads(result.stdout)
    titles = sorted(t["title"] for t in payload)
    print("triage output ({n} cards): {titles}".format(n=len(titles), titles=titles))

    expected = {"card-a-open-gated", "card-b-active-gated"}
    actual = set(titles)
    missing = expected - actual
    unexpected = actual - expected - {"card-c-active-clear"}

    print(f"expected={sorted(expected)}")
    print(f"missing={sorted(missing)}")
    print(f"unexpected={sorted(unexpected)}")

    if missing:
        print(
            "DEFECT CONFIRMED: triage omits the active+gated fixture "
            f"({sorted(missing)}). Both 'card-a-open-gated' and "
            f"'card-b-active-gated' should appear; only "
            f"{sorted(actual & expected)} did."
        )
        return 1
    print("OK: triage included every parked card regardless of status.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
