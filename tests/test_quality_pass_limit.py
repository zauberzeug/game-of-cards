from __future__ import annotations

import unittest


class QualityPassLimitTest(unittest.TestCase):
    """`quality-pass --limit` is a count cap that feeds `cards[:limit]`.

    A negative value is a valid Python slice bound but silently drops
    trailing cards instead of capping, so the flag must reject negatives
    exactly like the structurally-identical `--max-rows` flag already does.
    """

    def setUp(self) -> None:
        from goc.engine import _build_parser

        self.parser = _build_parser()

    def test_negative_limit_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["quality-pass", "--limit", "-2"])

    def test_zero_and_positive_limit_parse(self) -> None:
        for good in ("0", "3"):
            ns = self.parser.parse_args(["quality-pass", "--limit", good])
            self.assertEqual(int(good), ns.limit)

    def test_default_limit_is_none(self) -> None:
        ns = self.parser.parse_args(["quality-pass"])
        self.assertIsNone(ns.limit)


if __name__ == "__main__":
    unittest.main()
