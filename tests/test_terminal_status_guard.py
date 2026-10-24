"""Regression guard: state-touching verbs refuse closed cards.

`terminal-status-guard-missing-across-mutation-verbs` decided on one shared
guard, `engine._refuse_terminal_mutation`, which every verb that must not
write to a `done` / `disproved` / `superseded` card calls right after
`load_card_or_exit`. These tests pin the helper's contract and each guarded
verb's refusal: exit 2, the card byte-identical, and a message naming the
card, its status and a forward path that actually works.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


CARD = """---
title: {title}
summary: "Probe card for the terminal-status guard."
status: {status}
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
{extra}tags: [bug]
definition_of_done: |
  - [x] MECHANICAL: probe.
---

# {title}

Body.
"""


def _card(title: str, status: str) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(title),
        frontmatter={"title": title, "status": status},
        body="",
        dod_open=0,
        dod_done=0,
    )


class RefuseTerminalMutationHelperTest(unittest.TestCase):
    def test_live_statuses_pass_through(self) -> None:
        for status in engine.STATUS_VALUES:
            if status in engine.TERMINAL_STATUSES:
                continue
            with self.subTest(status=status):
                self.assertIsNone(
                    engine._refuse_terminal_mutation(_card("live-card", status), "wait")
                )

    def test_terminal_statuses_exit_2_naming_card_status_verb_and_forward_path(self) -> None:
        for status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(status=status):
                err = io.StringIO()
                with redirect_stderr(err), self.assertRaises(SystemExit) as raised:
                    engine._refuse_terminal_mutation(_card("closed-card", status), "wait")
                self.assertEqual(raised.exception.code, 2)
                message = err.getvalue()
                self.assertIn("closed-card", message)
                self.assertIn(repr(status), message)
                self.assertIn("`goc wait`", message)
                self.assertIn("post-close amendment", message)


class GuardedVerbCliTest(unittest.TestCase):
    """Drives the guarded verbs through the real CLI against a scratch deck."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.deck = self.root / ".game-of-cards" / "deck"
        self._write("live-card", "open")
        for status in sorted(engine.TERMINAL_STATUSES):
            # Each closed card carries the overlay it was impeded by while
            # live, so `--clear` has something it could wipe.
            extra = "waiting_on: external\n"
            if status == "superseded":
                extra = "superseded_by:\n  - live-card\n" + extra
            self._write(f"{status}-card", status, extra)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, title: str, status: str, extra: str = "") -> None:
        card = self.deck / title
        card.mkdir(parents=True)
        closed_at = '"2026-05-30T00:00:00Z"' if status in engine.TERMINAL_STATUSES else "null"
        (card / "README.md").write_text(
            CARD.format(title=title, status=status, closed_at=closed_at, extra=extra)
        )
        (card / "log.md").write_text("")

    def _goc(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env.pop("GOC_WORKTREE_DECK", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args, "--no-commit"],
            cwd=str(self.root), env=env, text=True, capture_output=True, check=False,
        )

    def _assert_refused(self, title: str, verb: str, *flags: str) -> None:
        card = self.deck / title
        before = {p.name: p.read_bytes() for p in card.iterdir()}
        res = self._goc(verb, title, *flags)
        after = {p.name: p.read_bytes() for p in card.iterdir()}
        self.assertEqual(
            res.returncode, 2,
            msg=f"expected exit 2\nstdout: {res.stdout}\nstderr: {res.stderr}",
        )
        self.assertEqual(before, after, msg=f"{title} was mutated\nstderr: {res.stderr}")
        self.assertIn(f"ERROR: {title}: status is", res.stderr)
        self.assertIn(f"`goc {verb}`", res.stderr)

    def test_wait_refuses_every_terminal_status_setters_and_clear_alike(self) -> None:
        shapes = (
            ("--reason", "external", "--until", "2027-01-01"),
            ("--until", "2027-01-01"),
            ("--clear",),
        )
        for status in sorted(engine.TERMINAL_STATUSES):
            for flags in shapes:
                with self.subTest(status=status, flags=flags):
                    self._assert_refused(f"{status}-card", "wait", *flags)

    def test_wait_still_sets_the_overlay_on_a_live_card(self) -> None:
        res = self._goc("wait", "live-card", "--reason", "external")
        self.assertEqual(res.returncode, 0, msg=res.stderr)
        self.assertIn("waiting_on: external", (self.deck / "live-card" / "README.md").read_text())

    def test_the_forward_path_offered_is_not_the_refused_supersede_command(self) -> None:
        # `goc status <old> superseded --by <new>` reads like the way to retire
        # a closed card, but `_cmd_status` refuses every terminal card — so the
        # guard must not offer it. If supersession of closed cards ever becomes
        # legal, this test fails and the helper's message can say so again.
        res = self._goc("status", "done-card", "superseded", "--by", "live-card")
        self.assertEqual(res.returncode, 2, msg=res.stdout + res.stderr)
        refusal = self._goc("wait", "done-card", "--clear").stderr
        self.assertNotIn("superseded --by", refusal)
        self.assertIn("log.md", refusal)


if __name__ == "__main__":
    unittest.main()
