"""Regression guard: `goc wait --reason` choices read from schema.yaml.

The `_cmd_wait` validator already reads `schema.waiting_on_values`. The
argparse layer must do the same — otherwise adding a fourth value to
`schema.yaml` succeeds at the validator but fails at argparse, a silent
schema-source-of-truth drift.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _wait_reason_choices() -> list[str]:
    from goc.engine import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            wait = action.choices["wait"]
            break
    else:
        raise AssertionError("no subparsers found on engine parser")
    for action in wait._actions:
        if action.dest == "reason":
            return list(action.choices)
    raise AssertionError("wait parser has no --reason argument")


class WaitReasonSchemaSourcedTest(unittest.TestCase):
    def test_reason_choices_match_schema(self) -> None:
        from goc.engine import load_schema

        schema = load_schema()
        self.assertEqual(_wait_reason_choices(), list(schema.waiting_on_values))


if __name__ == "__main__":
    unittest.main()
