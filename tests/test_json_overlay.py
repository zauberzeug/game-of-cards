from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_engine():
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from goc import engine

    return engine


CARD_TEMPLATE = """\
---
title: {title}
summary: "{title}"
status: open
stage: null
contribution: medium
created: "2026-05-27T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
{overlay}definition_of_done: |
  - [ ] placeholder
---

# {title}
"""


class JsonOverlayTest(unittest.TestCase):
    def _record(self, overlay: str, slim: bool = False) -> dict:
        engine = _load_engine()
        with tempfile.TemporaryDirectory() as tmp:
            card_dir = Path(tmp) / "card"
            card_dir.mkdir()
            (card_dir / "README.md").write_text(
                CARD_TEMPLATE.format(title="card", overlay=overlay)
            )
            card = engine.load_card(card_dir)
            self.assertIsNotNone(card)
            return json.loads(engine.render_json([card], slim=slim))[0]

    def test_json_exposes_active_overlay(self) -> None:
        record = self._record('waiting_on: external\nwaiting_until: "2099-01-01"\n')
        self.assertEqual("external", record["waiting_on"])
        self.assertEqual("2099-01-01", record["waiting_until"])

    def test_json_emits_null_overlay_when_absent(self) -> None:
        record = self._record("")
        self.assertIn("waiting_on", record)
        self.assertIn("waiting_until", record)
        self.assertIsNone(record["waiting_on"])
        self.assertIsNone(record["waiting_until"])

    def test_slim_json_exposes_active_overlay(self) -> None:
        record = self._record(
            'waiting_on: external\nwaiting_until: "2099-01-01"\n', slim=True
        )
        self.assertEqual("external", record["waiting_on"])
        self.assertEqual("2099-01-01", record["waiting_until"])

    def test_slim_json_emits_null_overlay_when_absent(self) -> None:
        record = self._record("", slim=True)
        self.assertIn("waiting_on", record)
        self.assertIn("waiting_until", record)
        self.assertIsNone(record["waiting_on"])
        self.assertIsNone(record["waiting_until"])

    def test_slim_json_exposes_worker_and_draft(self) -> None:
        record = self._record(
            'worker: {who: "alice", where: feature/x}\n', slim=True
        )
        self.assertEqual({"who": "alice", "where": "feature/x"}, record["worker"])
        self.assertFalse(record["draft"])

    def test_slim_json_marks_draft_scaffold(self) -> None:
        record = self._record("draft: true\n", slim=True)
        self.assertTrue(record["draft"])

    def test_slim_json_emits_null_worker_and_false_draft_when_absent(self) -> None:
        record = self._record("", slim=True)
        self.assertIn("worker", record)
        self.assertIn("draft", record)
        self.assertIsNone(record["worker"])
        self.assertFalse(record["draft"])

    def test_slim_json_keys_contract_lists_worker_and_draft(self) -> None:
        engine = _load_engine()
        self.assertIn("worker", engine.SLIM_JSON_KEYS)
        self.assertIn("draft", engine.SLIM_JSON_KEYS)


if __name__ == "__main__":
    unittest.main()
