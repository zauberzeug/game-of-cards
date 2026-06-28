from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


class TitleAntipatternReturnTypeTest(unittest.TestCase):
    """Pin the contract the docstring of `_check_title_antipatterns` describes:
    the helper returns a flat list of reason *strings*, not (substring, reason)
    tuples. A maintainer who trusts a stale "returns tuples" docstring and writes
    `for sub, reason in _check_title_antipatterns(t):` would crash; this test
    guards against that drift creeping back in."""

    def test_returns_reason_strings_not_tuples(self) -> None:
        # A title with multiple antipatterns: underscore + camelCase token.
        reasons = engine._check_title_antipatterns("fixBug_in_parser")
        self.assertTrue(reasons, "expected the jargon title to trip antipatterns")
        for element in reasons:
            self.assertIsInstance(
                element,
                str,
                msg=f"each returned element must be a reason string, got {element!r}",
            )

    def test_clean_title_returns_empty_list(self) -> None:
        self.assertEqual(
            engine._check_title_antipatterns("auth-cookie-expires-too-soon"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
