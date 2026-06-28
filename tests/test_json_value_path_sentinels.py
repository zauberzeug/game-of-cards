"""Regression: render_json's `value_path` must carry only real card slugs.

`compute_values` terminates every argmax chain with an internal sentinel
(`["self"]` for a leaf, `["cycle"]` on a validate-failing cyclic deck).
`_format_why` (the `-v` WHY column) strips that sentinel, but before the fix
`render_json` emitted the raw path, so the machine-readable `value_path` field
presented `"self"` / `"cycle"` as if they were card titles — a drift from the
human surface. Both surfaces now derive the chain from `_value_path_slugs`, so
they cannot disagree.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from goc import engine


def _card(title: str, advances: list[str], contrib: str = "medium") -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": "open",
            "contribution": contrib,
            "human_gate": "none",
            "created": "2026-06-24",
            "summary": f"{title} summary",
            "tags": [],
            "advances": advances,
            "advanced_by": [],
            "supersedes": [],
            "superseded_by": [],
            "definition_of_done": "- [ ] x\n",
        },
        body="body",
        dod_open=1,
        dod_done=0,
    )


class JsonValuePathSentinelsTest(unittest.TestCase):
    def test_value_path_carries_only_real_slugs(self) -> None:
        root = _card("root-card", ["mid-card"])
        mid = _card("mid-card", ["leaf-card"])
        leaf = _card("leaf-card", [], contrib="high")

        records = {
            r["title"]: r for r in json.loads(engine.render_json([root, mid, leaf]))
        }

        self.assertEqual(records["root-card"]["value_path"], ["mid-card", "leaf-card"])
        self.assertEqual(records["mid-card"]["value_path"], ["leaf-card"])
        self.assertEqual(records["leaf-card"]["value_path"], [])
        for rec in records.values():
            self.assertNotIn("self", rec["value_path"])
            self.assertNotIn("cycle", rec["value_path"])

    def test_helper_strips_both_sentinels(self) -> None:
        self.assertEqual(engine._value_path_slugs(["self"]), [])
        self.assertEqual(engine._value_path_slugs(["cycle"]), [])
        self.assertEqual(engine._value_path_slugs(["a", "b", "self"]), ["a", "b"])
        self.assertEqual(engine._value_path_slugs(["a", "b", "cycle"]), ["a", "b"])
        # A real slug that is not a sentinel is preserved untouched.
        self.assertEqual(engine._value_path_slugs(["a", "b"]), ["a", "b"])
        self.assertEqual(engine._value_path_slugs([]), [])

    def test_why_column_still_correct(self) -> None:
        # _format_why now routes its trailing-strip through the shared helper;
        # the closed WHY-trace contract must be unchanged.
        self.assertEqual(engine._format_why(["self"], {}), "")
        self.assertEqual(engine._format_why(["cycle"], {}), "(cycle)")
        self.assertEqual(
            engine._format_why(["a", "b", "self"], {}), "→ a (?) → b (?)"
        )
        self.assertEqual(
            engine._format_why(["a", "b", "cycle"], {}),
            "→ a (?) → b (?) (cycle)",
        )


if __name__ == "__main__":
    unittest.main()
