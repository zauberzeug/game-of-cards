#!/usr/bin/env python3
"""Reproduce: standup Section 5 ("Next up") lists cards pull-card would never pick.

`goc/templates/skills/standup/SKILL.md` § "Section 5 — Next up" tells the
agent to

    Show the top 3 open `human_gate: none` cards by value score (the cards
    `Skill(pull-card)` would pick next), as a forward look.

and then ships this command to produce that list:

    goc 2>/dev/null | head -5 || true

Bare `goc` is `--status open` with **no** gate filter and **no** impediment
filter. `Skill(pull-card)` selects with `goc --ready`, i.e. the engine's
`card_is_ready`: `status: open` ∧ `human_gate: none` ∧ no active
`waiting_on`/`waiting_until` overlay ∧ not a draft scaffold. So the section
answers a different question from the one its own prose asks.

This script builds a hermetic scratch deck with one card per readiness class,
runs both predicates against it, and reports the disagreement. It then checks
whether the shipped skill template still carries the drifting command.

Exit code:
  0 — Section 5 uses the ready predicate (defect fixed)
  1 — Section 5 still uses the bare-queue predicate (defect present)

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
"""

from __future__ import annotations

import json
import os
import re
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

TEMPLATE = ROOT / "goc" / "templates" / "skills" / "standup" / "SKILL.md"

# The four readiness classes, as (title, extra frontmatter, draft?) triples.
# Only `ready-low-value` satisfies `card_is_ready`; it is also the *lowest*
# value card, so a value-sorted bare queue buries it below three cards that
# `pull-card` will never touch.
CARDS = [
    (
        "gated-epic-blocks-the-queue",
        {"contribution": "high", "human_gate": "session"},
    ),
    (
        "impeded-card-waiting-on-a-vendor",
        {"contribution": "high", "human_gate": "none", "waiting_on": "external"},
    ),
    (
        "deferred-card-parked-until-next-year",
        {"contribution": "high", "human_gate": "none", "waiting_until": "2999-01-01"},
    ),
    (
        "ready-low-value-typo-fix",
        {"contribution": "low", "human_gate": "none"},
    ),
]

FRONTMATTER = """\
---
title: {title}
summary: "Scratch card for the standup Section 5 reproducer."
status: open
stage: null
contribution: {contribution}
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: {human_gate}
advances: []
advanced_by: []
tags: []
{overlay}definition_of_done: |
  - [ ] MECHANICAL: scratch card, never closed
---

# {title}

## Summary

Scratch card for the standup Section 5 reproducer.
"""


def _write_deck(deck: Path) -> None:
    for title, fields in CARDS:
        overlay = ""
        for key in ("waiting_on", "waiting_until"):
            if key in fields:
                overlay += f"{key}: {fields[key]}\n"
        card = deck / title
        card.mkdir(parents=True)
        (card / "README.md").write_text(
            FRONTMATTER.format(
                title=title,
                contribution=fields["contribution"],
                human_gate=fields["human_gate"],
                overlay=overlay,
            )
        )
        (card / "log.md").write_text("")


def _goc_json(cwd: Path, *args: str) -> list[dict]:
    env = dict(os.environ)
    env.pop("GOC_WORKER", None)
    out = subprocess.run(
        [sys.executable, "-m", "goc.cli", "--json", *args],
        cwd=cwd,
        env={**env, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


def _section_5_command() -> str | None:
    """The shell command Section 5 of the standup template actually ships."""
    text = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(
        r"^## Section 5 — Next up\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not m:
        return None
    fence = re.search(r"```bash\n(.*?)\n```", m.group(1), re.DOTALL)
    return fence.group(1).strip() if fence else None


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        deck = repo / ".game-of-cards" / "deck"
        _write_deck(deck)
        (repo / ".game-of-cards" / "config.yaml").write_text(
            "workflow:\n  auto_commit: false\n"
        )

        # Bare `goc` — the predicate Section 5 ships.
        bare = _goc_json(repo, "--status", "open")
        bare.sort(key=lambda c: (-c["value"], c["created"]))
        shown = bare[:3]
        # `goc --ready` — the predicate Section 5's prose describes and
        # `Skill(pull-card)` actually uses.
        ready = {c["title"] for c in _goc_json(repo, "--ready")}

    print("Scratch deck — one card per readiness class:")
    for c in bare:
        print(
            f"  {c['title']:<38} value={c['value']:<4} "
            f"gate={c['human_gate']:<7} ready={str(c['ready']).lower()}"
        )
    print()
    print("Section 5 as shipped (`goc | head -5` → top 3 rows):")
    for c in shown:
        print(f"  {c['title']:<38} ready={str(c['ready']).lower()}")
    print()
    print("`goc --ready` (what pull-card would actually pick):")
    for title in sorted(ready):
        print(f"  {title}")
    print()

    wrong = [c["title"] for c in shown if not c["ready"]]
    missed = sorted(ready - {c["title"] for c in shown})
    print(f"False positives (shown, never pullable): {len(wrong)}/{len(shown)} {wrong}")
    print(f"False negatives (pullable, not shown):   {len(missed)} {missed}")
    print()

    command = _section_5_command()
    print(f"Shipped Section 5 command: {command!r}")
    if command is None:
        print("[FAIL] could not locate Section 5's bash block in the template")
        return 1
    if "--ready" not in command:
        print("[FAIL] Section 5 does not use `goc --ready`; the drift is live.")
        return 1
    print("[OK] Section 5 uses `goc --ready`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
