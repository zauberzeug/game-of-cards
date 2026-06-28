"""Parity guard: every enum surface derives from schema.yaml.

`schema.yaml` is the documented single source of truth for the card
enums (`status_values`, `stage_values`, `contribution_values`,
`human_gate_values`, `waiting_on_values`). The engine historically
re-stated those enums as literals — module-level ordering constants,
argparse `choices`, renderer column lists — and each divergence was
found and fixed one card at a time (see the closed family headed by
`schema-enum-surfaces-keep-drifting-into-hardcoded-literals`).

This test closes the family: it asserts each enum surface equals the
corresponding `schema.*` list, so the whole class turns red on the
first drift instead of waiting for a human to notice a dropped card.
The custom-workflow / custom-enum epics make this acute — once a
consuming repo can widen the schema, any surviving literal silently
fails to render or offer the new value.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _global_choices(dest: str) -> list[str]:
    """argparse `choices` for a top-level option, by its dest."""
    from goc.engine import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if action.dest == dest:
            return list(action.choices)
    raise AssertionError(f"no top-level option with dest {dest!r}")


def _sub_choices(subcommand: str, dest: str) -> list[str]:
    """argparse `choices` for an option on a subparser."""
    from goc.engine import _build_parser

    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub = action.choices[subcommand]
            break
    else:
        raise AssertionError("no subparsers found on engine parser")
    for action in sub._actions:
        if action.dest == dest:
            return list(action.choices)
    raise AssertionError(f"{subcommand} parser has no {dest!r} argument")


def _positional_choices(subcommand: str, dest: str) -> list[str]:
    return _sub_choices(subcommand, dest)


class SchemaEnumSurfaceParityTest(unittest.TestCase):
    def setUp(self) -> None:
        from goc.engine import load_schema

        self.schema = load_schema()

    # ── module-level ordering / membership constants ──────────────────

    def test_status_values_match_schema(self) -> None:
        from goc.engine import STATUS_VALUES

        self.assertEqual(list(STATUS_VALUES), list(self.schema.status_values))

    def test_status_filter_values_are_status_plus_all(self) -> None:
        from goc.engine import STATUS_FILTER_VALUES

        self.assertEqual(
            list(STATUS_FILTER_VALUES),
            [*self.schema.status_values, "all"],
        )

    def test_mutable_status_values_are_status_minus_done(self) -> None:
        from goc.engine import MUTABLE_STATUS_VALUES

        self.assertEqual(
            list(MUTABLE_STATUS_VALUES),
            [s for s in self.schema.status_values if s != "done"],
        )

    def test_contribution_order_matches_schema_order(self) -> None:
        from goc.engine import CONTRIBUTION_ORDER

        self.assertEqual(
            CONTRIBUTION_ORDER,
            {c: i for i, c in enumerate(self.schema.contribution_values)},
        )

    def test_contribution_rank_covers_every_schema_level(self) -> None:
        from goc.engine import CONTRIBUTION_RANK

        # Every contribution level must have a rank; a missing one sorts
        # the card to 0.0 silently. Ranks descend with schema order.
        self.assertEqual(
            sorted(CONTRIBUTION_RANK), sorted(self.schema.contribution_values)
        )
        ranks = [CONTRIBUTION_RANK[c] for c in self.schema.contribution_values]
        self.assertEqual(ranks, sorted(ranks, reverse=True))

    def test_stage_order_matches_schema_stage_values(self) -> None:
        from goc.engine import STAGE_ORDER

        expected = ["null" if v is None else v for v in self.schema.stage_values]
        self.assertEqual(STAGE_ORDER, expected)

    # ── argparse `choices` surfaces ───────────────────────────────────

    def test_global_status_filter_choices_match_schema(self) -> None:
        self.assertEqual(
            _global_choices("status_flag"),
            [*self.schema.status_values, "all"],
        )

    def test_global_contribution_filter_choices_match_schema(self) -> None:
        self.assertEqual(
            _global_choices("contribution"), list(self.schema.contribution_values)
        )

    def test_global_human_gate_filter_choices_match_schema(self) -> None:
        self.assertEqual(
            _global_choices("human_gate"), list(self.schema.human_gate_values)
        )

    def test_status_transition_choices_match_mutable_schema(self) -> None:
        self.assertEqual(
            _positional_choices("status", "new_status"),
            [s for s in self.schema.status_values if s != "done"],
        )

    def test_new_contribution_choices_match_schema(self) -> None:
        self.assertEqual(
            _sub_choices("new", "contribution"), list(self.schema.contribution_values)
        )

    def test_new_gate_choices_match_schema(self) -> None:
        self.assertEqual(
            _sub_choices("new", "gate"), list(self.schema.human_gate_values)
        )

    def test_wait_reason_choices_match_schema(self) -> None:
        self.assertEqual(
            _sub_choices("wait", "reason"), list(self.schema.waiting_on_values)
        )

    # ── renderer column list ──────────────────────────────────────────

    def test_board_columns_match_schema_status_values(self) -> None:
        # render_board derives columns from load_schema().status_values;
        # assert the source line still reads the schema rather than a literal.
        src = (ROOT / "goc" / "engine.py").read_text()
        self.assertIn("columns = list(load_schema().status_values)", src)


if __name__ == "__main__":
    unittest.main()
