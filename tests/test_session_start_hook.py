"""Regression tests for the SessionStart hook frontmatter parser.

The bug (pre-fix): the hook substring-matched `status: active` against the
full README, so a closed card whose body *mentioned* that string was falsely
reported as active.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

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

    def test_human_gate_default_none_when_absent(self):
        p = self._readme("---\nstatus: active\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "none")

    def test_human_gate_decision_parsed(self):
        p = self._readme("---\nstatus: active\nhuman_gate: decision\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "decision")

    def test_human_gate_session_parsed(self):
        p = self._readme("---\nstatus: active\nhuman_gate: session\ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "session")

    def test_human_gate_empty_value_normalized_to_none(self):
        p = self._readme("---\nstatus: active\nhuman_gate: \ntitle: t\n---\nbody\n")
        self.assertEqual(self.hook._card_human_gate(p), "none")


class SessionStartHookGatedActiveCardsTest(unittest.TestCase):
    """The hook must not label `human_gate != none` active cards as resumable.

    Fixture deck contains three active cards: one each at human_gate `none`,
    `decision`, `session`. The expected output puts the `none` card under the
    `resume or close` line and the two gated cards under a distinct
    `awaiting human / agent cannot resume` line.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _make_card(self, deck_dir: Path, name: str, status: str, human_gate: str) -> None:
        card = deck_dir / name
        card.mkdir(parents=True)
        body = (
            f"---\nstatus: {status}\nhuman_gate: {human_gate}\ntitle: {name}\n---\nbody\n"
        )
        (card / "README.md").write_text(body, encoding="utf-8")

    def _run_hook(self, project_dir: Path) -> str:
        buf = io.StringIO()
        stdin = io.StringIO(json.dumps({"cwd": str(project_dir)}))
        with mock.patch.object(sys, "stdin", stdin), redirect_stdout(buf):
            rc = self.hook.main()
        self.assertEqual(rc, 0)
        return buf.getvalue()

    def test_three_active_cards_partitioned_by_human_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "ready-card", "active", "none")
            self._make_card(deck, "decision-card", "active", "decision")
            self._make_card(deck, "session-card", "active", "session")
            out = self._run_hook(project)

        resumable_lines = [
            line for line in out.splitlines() if "resume or close" in line
        ]
        self.assertEqual(len(resumable_lines), 1, out)
        self.assertIn("ready-card", resumable_lines[0])
        self.assertNotIn("decision-card", resumable_lines[0])
        self.assertNotIn("session-card", resumable_lines[0])

        parked_lines = [
            line for line in out.splitlines() if "agent cannot resume" in line
        ]
        self.assertEqual(len(parked_lines), 1, out)
        self.assertIn("decision-card", parked_lines[0])
        self.assertIn("session-card", parked_lines[0])
        self.assertNotIn("ready-card", parked_lines[0])

    def test_only_gated_active_cards_emits_only_parked_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "decision-card", "active", "decision")
            out = self._run_hook(project)
        self.assertNotIn("resume or close", out)
        self.assertIn("agent cannot resume", out)
        self.assertIn("decision-card", out)

    def test_only_resumable_active_cards_emits_only_resumable_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "ready-card", "active", "none")
            out = self._run_hook(project)
        self.assertIn("resume or close", out)
        self.assertNotIn("agent cannot resume", out)
        self.assertIn("ready-card", out)

    def test_no_active_cards_emits_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            deck = project / ".game-of-cards" / "deck"
            deck.mkdir(parents=True)
            self._make_card(deck, "done-card", "done", "none")
            out = self._run_hook(project)
        self.assertEqual(out, "")
