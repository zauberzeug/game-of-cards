from __future__ import annotations

import unittest
from pathlib import Path

from goc import engine


def _make_card(title: str, status: str, advanced_by: list[str] | None = None) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/nonexistent/{title}"),
        frontmatter={
            "title": title,
            "status": status,
            "advanced_by": advanced_by or [],
            "advances": [],
            "human_gate": "none",
            "contribution": "medium",
        },
        body="",
        dod_open=0,
        dod_done=0,
    )


class ClosureGateTerminalPrereqsTest(unittest.TestCase):
    def _gate(self, upstream_status: str) -> tuple[bool, str]:
        upstream = _make_card("X-upstream", upstream_status)
        downstream = _make_card("Y-downstream", "open", advanced_by=["X-upstream"])
        return engine._run_derived_check(
            {"name": "advanced-by-closed"}, downstream, [upstream, downstream], "2026-05-27"
        )

    def test_terminal_upstreams_pass(self) -> None:
        for status in ("done", "superseded", "disproved"):
            with self.subTest(upstream=status):
                ok, msg = self._gate(status)
                self.assertTrue(ok, msg=f"expected pass for {status!r}, got: {msg}")

    def test_non_terminal_upstreams_fail(self) -> None:
        for status in ("open", "active"):
            with self.subTest(upstream=status):
                ok, msg = self._gate(status)
                self.assertFalse(ok, msg=f"expected block for {status!r}, got: {msg}")
                self.assertIn("not done", msg)


if __name__ == "__main__":
    unittest.main()
