#!/usr/bin/env python3
"""Count messages in the engine hardcode the plural noun for one-card results.

Two proofs:

1. **Live** — build a scratch deck holding exactly one card and run the two
   reachable surfaces (`goc quality-pass --no-llm`, `goc triage`). Both print
   "1 cards".
2. **Static** — list every `{len(...)} card…` interpolation in
   `goc/engine.py` and split it into plural-unsafe (hardcoded `cards`) versus
   plural-safe (`card(s)`, or the `noun = "card" if … else "cards"` ternary
   already used by `render_active_notice`). The unsafe sites are the fix set.

Exits non-zero while any plural-unsafe count message remains.
"""
from __future__ import annotations

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

CARD = """\
---
title: solo-card
summary: the only card in this scratch deck
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [ ] TDD: criteria
---

# solo-card

Body.
"""


def run_goc(deck_repo: Path, *args: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=deck_repo,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT), "HOME": str(deck_repo)},
    )
    return proc.stdout + proc.stderr


# ── 1. live: a one-card deck ────────────────────────────────────────────────

live_hits: list[str] = []
with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    card_dir = repo / ".game-of-cards" / "deck" / "solo-card"
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(CARD, encoding="utf-8")
    (card_dir / "log.md").write_text("", encoding="utf-8")

    print("live output on a deck holding exactly one card:")
    for args in (("quality-pass", "--no-llm"), ("triage",)):
        out = run_goc(repo, *args)
        for line in out.splitlines():
            if "1 cards" in line:
                print(f"  $ goc {' '.join(args)}")
                print(f"    {line.strip()}")
                live_hits.append(line.strip())

if not live_hits:
    print("  (none)")


# ── 2. static: every count-interpolated card noun in the engine ─────────────

# The plural-aware ternary, whether written inline or factored into the helper
# this fix introduced (same wording, one definition). That helper was
# `_cards_noun(count)`; the successor card generalized it to
# `_plural(count, singular, plural=None)`, so both names count as safe.
SAFE_TERNARY = re.compile(r'noun\s*=\s*"card"\s*if\b|_cards_noun\(|_plural\(')
COUNT_NOUN = re.compile(r"\{len\([^)}]*\)\}\s+(cards?\(s\)|cards?\b)")

src = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8").splitlines()
ternary_lines = {i for i, ln in enumerate(src, 1) if SAFE_TERNARY.search(ln)}

unsafe: list[tuple[int, str]] = []
safe: list[tuple[int, str]] = []
for lineno, line in enumerate(src, 1):
    m = COUNT_NOUN.search(line)
    if not m:
        continue
    (safe if m.group(1).endswith("(s)") else unsafe).append((lineno, line.strip()))

print(f"\nplural-safe `card(s)` sites: {len(safe)}")
for lineno, text in safe:
    print(f"  goc/engine.py:{lineno}  {text[:88]}")
print(f"plural-safe ternary sites: {len(ternary_lines)} (lines {sorted(ternary_lines)})")
print(f"\nplural-UNSAFE hardcoded `cards` sites: {len(unsafe)}")
for lineno, text in unsafe:
    print(f"  goc/engine.py:{lineno}  {text[:88]}")

print()
if unsafe:
    print(
        f"FAIL: {len(unsafe)} count message(s) hardcode the plural noun while the "
        f"same module already ships {len(safe)} `card(s)` sites and "
        f"{len(ternary_lines)} plural-aware ternary site(s)"
    )
    sys.exit(1)
print("PASS: every count message in goc/engine.py pluralizes correctly")
