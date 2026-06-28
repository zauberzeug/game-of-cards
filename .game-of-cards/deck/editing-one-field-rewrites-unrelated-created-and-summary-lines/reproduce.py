"""Demonstrate that a whole-frontmatter round-trip rewrites untouched
`created` / `summary` lines from bare to quoted, producing a spurious
cross-field diff on any round-trip verb (e.g. `goc wait`, `goc decide`,
`goc advance`).

Two parts:
  1. Synthetic round-trip: parse a card that stores `created` and
     `summary` bare, mutate ONLY an overlay field, re-emit, and show the
     untouched lines flipped to quoted while the values are preserved.
  2. Live-deck survey: count how many cards in the dogfood deck carry a
     bare colon/comma-bearing `created` or `summary` line that the next
     round-trip verb would silently rewrite.

Exit 0 when the drift is demonstrated (it currently is); a fix should
make the round-trip line-stable so the untouched lines round-trip
byte-identically and the survey counts drop to zero.
"""
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CARD = """\
---
title: example-card
summary: When `cfg: true`, the verb refuses; commas, colons: all bare here.
status: open
stage: null
contribution: medium
created: 2026-06-06T04:37:25Z
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: something
---

# example-card

body text.
"""


def _line(text, key):
    return next(l for l in text.splitlines() if l.startswith(f"{key}:"))


def main() -> int:
    fm, body = engine.parse_frontmatter(CARD)

    # Simulate a `goc wait <title> --until ...` round-trip: mutate ONLY the
    # impediment overlay, then re-emit the whole frontmatter (this is exactly
    # what _cmd_wait / _cmd_decide / _cmd_advance do).
    fm2 = dict(fm)
    fm2["waiting_until"] = "2027-01-01"
    out = engine.emit_frontmatter(fm2, body=body)

    print("=== Part 1: synthetic round-trip (mutated only waiting_until) ===")
    drift = False
    for key in ("created", "summary"):
        before = _line(CARD, key)
        after = _line(out, key)
        flipped = before != after
        drift = drift or flipped
        print(f"[{key}]")
        print(f"  BEFORE: {before[:88]}")
        print(f"  AFTER : {after[:88]}")
        print(f"  FLIPPED (spurious diff): {flipped}")

    # Value must be preserved — this is representational drift, not data loss.
    fm3, _ = engine.parse_frontmatter(out)
    value_ok = fm3["created"] == fm["created"] and fm3["summary"] == fm["summary"]
    print(f"  values preserved across round-trip: {value_ok}")

    print()
    print("=== Part 2: live dogfood-deck survey ===")
    deck = _repo_root() / ".game-of-cards" / "deck"
    trigger = engine._YAML_NEEDS_QUOTE
    counts = {"created": 0, "summary": 0}
    for readme in sorted(deck.glob("*/README.md")):
        try:
            cfm, _ = engine.parse_frontmatter(readme.read_text())
        except engine.FrontmatterError:
            continue
        raw = readme.read_text()
        for key in ("created", "summary"):
            line = next((l for l in raw.splitlines()
                         if l.startswith(f"{key}:")), None)
            if line is None or line.strip() in (f"{key}: |-", f"{key}: |"):
                continue
            val = line[len(key) + 1:].lstrip()
            if val[:1] in ('"', "'"):
                continue  # already quoted
            if trigger.search(val):
                counts[key] += 1
    for key, n in counts.items():
        print(f"  cards with bare quote-trigger {key}: {n} "
              f"(each rewritten on the next round-trip verb)")

    print()
    print(f"DRIFT DEMONSTRATED: {drift and value_ok}")
    return 0 if (drift and value_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
