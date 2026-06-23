from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone

from goc.engine import parse_closed_since


NOW = datetime(2026, 6, 23, tzinfo=timezone.utc)


class ClosedSinceWindowBoundsTest(unittest.TestCase):
    def test_oversized_window_exits_2_without_traceback(self) -> None:
        err = io.StringIO()
        with self.assertRaises(SystemExit) as cm, redirect_stderr(err):
            parse_closed_since("99999999999w", now=NOW)
        self.assertEqual(2, cm.exception.code)
        self.assertIn("goc: error: --closed-since:", err.getvalue())

    def test_valid_relative_windows_still_parse(self) -> None:
        for window in ("24h", "7d", "2w"):
            with self.subTest(window=window):
                result = parse_closed_since(window, now=NOW)
                self.assertIsInstance(result, datetime)
                self.assertLess(result, NOW)

    def test_absolute_date_still_parses(self) -> None:
        result = parse_closed_since("2026-05-01", now=NOW)
        self.assertEqual(datetime(2026, 5, 1, tzinfo=timezone.utc), result)


if __name__ == "__main__":
    unittest.main()
