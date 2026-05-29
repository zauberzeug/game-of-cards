"""Module-level singleton guards for goc/engine.py.

Regresses defects where the same module-level constant is assigned
twice, so the second binding silently shadows the first. The trap is
that edits to one definition appear to have no effect — see card
`duplicate-dod-any-box-regex-in-engine-shadows-the-first`.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENGINE_SRC = (ROOT / "goc" / "engine.py").read_text()


class ModuleSingletonTest(unittest.TestCase):
    def test_dod_any_box_defined_once(self):
        matches = re.findall(
            r"^DOD_ANY_BOX = re\.compile", ENGINE_SRC, re.MULTILINE
        )
        self.assertEqual(
            len(matches),
            1,
            "DOD_ANY_BOX must be assigned exactly once at module scope; "
            "a second assignment silently shadows the first and traps "
            "future regex edits.",
        )


if __name__ == "__main__":
    unittest.main()
