"""Regression tests for the SessionStart hook frontmatter parser.

The bug (pre-fix): the hook substring-matched `status: active` against the
full README, so a closed card whose body *mentioned* that string was falsely
reported as active.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "goc" / "templates" / "hooks" / "deck_session_start.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("deck_session_start", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SessionStartHookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _readme(self, content: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.flush()
        return Path(tmp.name)

    def test_active_frontmatter_detected(self):
        p = self._readme("---\nstatus: active\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "active")

    def test_done_frontmatter_not_active(self):
        p = self._readme("---\nstatus: done\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "done")

    def test_body_mention_does_not_fool_parser(self):
        """Regression: a closed card whose body contains `status: active` must not be flagged."""
        p = self._readme(
            "---\nstatus: done\ntitle: t\n---\n"
            "Parallel agents use `status: active` as a soft lock.\n"
            "```yaml\nstatus: active\n```\n"
        )
        self.assertNotEqual(self.hook._card_status(p), "active")
        self.assertEqual(self.hook._card_status(p), "done")

    def test_open_card_not_active(self):
        p = self._readme("---\nstatus: open\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "open")

    def test_missing_frontmatter_returns_none(self):
        p = self._readme("no frontmatter here\nstatus: active\n")
        self.assertIsNone(self.hook._card_status(p))

    def test_original_status_key_not_matched(self):
        """A line like `original_status: active` must not satisfy the check."""
        p = self._readme("---\noriginal_status: active\nstatus: done\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_status(p), "done")
