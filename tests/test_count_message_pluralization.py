"""Count banners in goc/engine.py must agree with themselves on "1 card".

Regression for card `deck-count-messages-print-1-cards-instead-of-1-card`:
seven `{len(...)} cards` interpolations hardcoded the plural noun, so a
one-result view read "Quality pass over 1 cards" while the `ACTIVE:` banner
on the same deck read "1 claimed card". The static guard below is what keeps
the swept convention from drifting back one site at a time.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENGINE_SRC = (ROOT / "goc" / "engine.py").read_text(encoding="utf-8")

# A count interpolation followed by a bare `card`/`cards` literal — the
# hardcoded-plural shape. `card(s)` (the migrate paths) is the other accepted
# convention and is deliberately allowed.
HARDCODED_PLURAL = re.compile(r"\{len\([^)}]*\)\}\s+cards?\b(?!\(s\))")

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


class CardsNounTest(unittest.TestCase):
    def test_singular_only_for_exactly_one(self) -> None:
        from goc.engine import _cards_noun

        self.assertEqual("card", _cards_noun(1))
        for plural in (0, 2, 7, 100):
            self.assertEqual("cards", _cards_noun(plural))


class NoHardcodedPluralTest(unittest.TestCase):
    def test_engine_has_no_hardcoded_plural_count_banner(self) -> None:
        offenders = [
            f"goc/engine.py:{lineno}  {line.strip()}"
            for lineno, line in enumerate(ENGINE_SRC.splitlines(), 1)
            if HARDCODED_PLURAL.search(line)
        ]
        self.assertEqual(
            [],
            offenders,
            "count banners must pluralize via _cards_noun() (or the `card(s)` "
            "form) so a one-result view reads '1 card':\n" + "\n".join(offenders),
        )


class OneCardDeckOutputTest(unittest.TestCase):
    """End-to-end on the two surfaces a human reads on a nearly-drained deck."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_single_card_surfaces_read_singular(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            card_dir = repo / ".game-of-cards" / "deck" / "solo-card"
            card_dir.mkdir(parents=True)
            (card_dir / "README.md").write_text(CARD, encoding="utf-8")
            (card_dir / "log.md").write_text("", encoding="utf-8")

            quality = self.run_goc(repo, "quality-pass", "--no-llm")
            triage = self.run_goc(repo, "triage")

        for label, proc in (("quality-pass", quality), ("triage", triage)):
            out = proc.stdout + proc.stderr
            self.assertNotIn("1 cards", out, f"goc {label} printed '1 cards':\n{out}")

        self.assertIn("Quality pass over 1 card (status=open):", quality.stdout)
        self.assertIn("## Waiting on you (gate ≠ none) — 1 card", triage.stdout)


if __name__ == "__main__":
    unittest.main()
