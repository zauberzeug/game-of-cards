"""Regression guard: shipped `/loop` examples must lead with their interval.

Claude Code's /loop grammar takes an interval either as a leading bare token
(`/loop 30m /pull-card`) or as a trailing clause (`every 2 hours`). A trailing
bare token (`/loop pull-card 30m`) matches neither, so the loop gets no
interval and picks its own cadence. The pull-card skill and the deck skill's
reference shipped that form until the card
`loop-examples-trail-a-bare-interval-that-claude-code-does-not-parse`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "goc" / "templates"
LOOP = re.compile(r"`/loop ([^`]+)`")
INTERVAL = re.compile(r"^\d+[smhd]$")


def trailing_bare_interval(example: str) -> bool:
    tokens = example.split()
    return bool(tokens) and not INTERVAL.match(tokens[0]) and any(
        INTERVAL.match(t) for t in tokens[1:]
    )


class LoopExamplesLeadWithTheIntervalTest(unittest.TestCase):
    def test_detector(self) -> None:
        self.assertTrue(trailing_bare_interval("pull-card 30m"))
        self.assertTrue(trailing_bare_interval("/pull-card 30m"))
        self.assertFalse(trailing_bare_interval("30m /pull-card"))
        self.assertFalse(trailing_bare_interval("check the build every 2 hours"))
        self.assertFalse(trailing_bare_interval("stop"))

    def test_shipped_templates_lead_with_the_interval(self) -> None:
        offenders = []
        for path in sorted(TEMPLATES.rglob("*")):
            if path.suffix not in {".md", ".yaml"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                for match in LOOP.finditer(line):
                    if trailing_bare_interval(match.group(1)):
                        rel = path.relative_to(ROOT)
                        offenders.append(f"{rel}:{lineno}: {match.group(0)}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
