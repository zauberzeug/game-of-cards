#!/usr/bin/env python3
"""Count banners the `cards` sweep structurally could not reach still hardcode plurals.

The sibling card `deck-count-messages-print-1-cards-instead-of-1-card` swept
every count banner its scan matched onto a `_cards_noun()` helper. That scan was
`\\{len\\([^)}]*\\)\\}\\s+cards?\\b` — the noun had to be the bare word `cards`,
immediately after the interpolation. Two whole classes fell outside it:

1. **A non-card noun** — `boxes`, `titles`, `summaries`, `items`, `lines`.
   `_cards_noun()` is card-specific, so these have no helper to route through.
2. **An adjective between the count and the noun** — `{len(cluster)} blocked
   cards` is a *card* banner the sweep's own regex never saw.

`tests/test_count_message_pluralization.py`, the CI guard that sweep installed,
inherits the same blind spot, so none of these turn the build red.

Two proofs: a static scan for count-then-plural-noun across the engine, then a
live run of the most user-visible instance (`goc done`'s refusal message).

Exits non-zero while any hardcoded-plural count banner remains.
"""
from __future__ import annotations

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

# The countable nouns this engine reports on. An explicit vocabulary keeps the
# scan precise — a bare `\w+s` regex matches verbs ("has", "contains") too.
NOUNS = (
    "cards|titles|summaries|boxes|lines|items|files|skills|checks|edges|"
    "entries|warnings|errors|hooks|verbs|tags"
)
# {interpolation} + up to two adjective words + a plural noun.
COUNT_NOUN = re.compile(r"\{[^{}]+\}\s+((?:[a-zA-Z][\w-]*\s+){0,2}(?:" + NOUNS + r"))\b(?!\(s\))")

src = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8").splitlines()

unsafe: list[tuple[int, str, str]] = []
for lineno, line in enumerate(src, 1):
    if 'f"' not in line:
        continue
    for m in COUNT_NOUN.finditer(line):
        phrase = m.group(1).strip()
        if "card(s)" in line:
            continue
        # already routed through the helper the cards sweep installed
        if "_cards_noun(" in line and phrase == "cards":
            continue
        unsafe.append((lineno, phrase, line.strip()))

print("static scan — count banners followed by a hardcoded plural noun:")
for lineno, phrase, text in unsafe:
    print(f"  goc/engine.py:{lineno}  [{phrase}]  {text[:92]}")
if not unsafe:
    print("  (none)")

print("\n  of those, card-noun banners the cards sweep's own regex never matched:")
missed = [(n, p, t) for n, p, t in unsafe if p.endswith("cards")]
for lineno, phrase, _ in missed:
    print(f"    goc/engine.py:{lineno}  [{phrase}]")
if not missed:
    print("    (none)")


# ── live: goc done's refusal message, the most-read instance ────────────────

CARD = """\
---
title: one-open-box
summary: a card with exactly one unchecked DoD box
status: active
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [ ] TDD: the single unchecked criterion
---

# one-open-box

Body.
"""

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    card_dir = repo / ".game-of-cards" / "deck" / "one-open-box"
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(CARD, encoding="utf-8")
    (card_dir / "log.md").write_text("", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", "done", "one-open-box"],
        cwd=repo, env=env, capture_output=True, text=True,
    )

print("\nlive — `goc done` on a card with exactly one unchecked box:")
for line in (proc.stdout + proc.stderr).splitlines():
    if "unchecked" in line:
        print(f"  {line.strip()}")

print()
if unsafe:
    print(
        f"FAIL: {len(unsafe)} count banner(s) hardcode a plural noun — "
        f"{len(missed)} of them are card banners the `cards` sweep's regex "
        "never matched, and its CI guard inherits the same blind spot"
    )
    sys.exit(1)
print("PASS: every count banner in goc/engine.py pluralizes correctly")
