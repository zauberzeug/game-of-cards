from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _card(title: str, *, status: str = "open", closed: bool = False,
          dod_done: bool = False, extra: str = "") -> str:
    box = "[x]" if dod_done else "[ ]"
    closed_at = '"2026-05-15T00:00:00Z"' if closed else "null"
    return f"""---
title: {title}
summary: "Fixture for the terminal-target supersession contract."
status: {status}
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
{extra}tags: [bug]
definition_of_done: |
  - {box} PROCESS: fixture
---

# {title}
"""


class SupersededByAllowsTerminalTargetTest(unittest.TestCase):
    """`goc status <X> superseded --by <Y>` accepts a terminal `<Y>`, and
    `goc validate` accepts a `superseded_by` pointer that lands on a terminal
    card. A supersession's successor is the work that replaces the old card
    and is *meant to be completed*; a pointer landing on a `done` successor
    has reached the resolution, and a `superseded` successor routes onward via
    its own `superseded_by`. The only constraint is referential integrity —
    the target must exist — enforced generically for every relationship field.
    The symmetric `supersedes`⇒`status: superseded` rule is unchanged (covered
    by `test_superseded_requires_by` and the validator)."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _write_card(self, cwd: Path, title: str, body: str) -> Path:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(body)
        return card_dir

    def _assert_cli_accepts_terminal_successor(self, terminal_status: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            origin = f"origin-for-{terminal_status}"
            successor = f"successor-{terminal_status}"
            self._write_card(cwd, origin, _card(origin, status="open"))
            if terminal_status == "superseded":
                # A superseded successor needs its own forward pointer to keep
                # the deck valid; give it a live tail and wire the inverse.
                self._write_card(
                    cwd, successor,
                    _card(successor, status="superseded", closed=True, dod_done=True,
                          extra="superseded_by:\n  - tail\nsupersedes: []\n"),
                )
                self._write_card(
                    cwd, "tail",
                    _card("tail", status="open",
                          extra="superseded_by: []\nsupersedes:\n  - " + successor + "\n"),
                )
            else:
                self._write_card(
                    cwd, successor,
                    _card(successor, status=terminal_status, closed=True, dod_done=True),
                )

            result = self.run_goc(
                cwd, "status", origin, "superseded", "--by", successor, "--no-commit"
            )
            self.assertEqual(
                0, result.returncode,
                msg=f"terminal successor ({terminal_status}) must be ACCEPTED:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            origin_text = (cwd / ".game-of-cards" / "deck" / origin / "README.md").read_text()
            self.assertIn("status: superseded", origin_text)
            self.assertIn(successor, origin_text)

            validate = self.run_goc(cwd, "validate")
            self.assertEqual(
                0, validate.returncode,
                msg=f"validate must pass for a completed-successor link ({terminal_status}):\n"
                f"stdout:\n{validate.stdout}\nstderr:\n{validate.stderr}",
            )

    def test_cli_accepts_done_successor(self) -> None:
        self._assert_cli_accepts_terminal_successor("done")

    def test_cli_accepts_disproved_successor(self) -> None:
        self._assert_cli_accepts_terminal_successor("disproved")

    def test_cli_accepts_superseded_successor(self) -> None:
        self._assert_cli_accepts_terminal_successor("superseded")

    def test_validate_accepts_completed_successor_link(self) -> None:
        # Hand-crafted: origin superseded, superseded_by → target that is done.
        # This is the natural shape after a supersession's successor completes.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._write_card(
                cwd, "origin",
                _card("origin", status="superseded", closed=True, dod_done=True,
                      extra="superseded_by:\n  - target\nsupersedes: []\n"),
            )
            self._write_card(
                cwd, "target",
                _card("target", status="done", closed=True, dod_done=True,
                      extra="superseded_by: []\nsupersedes:\n  - origin\n"),
            )
            result = self.run_goc(cwd, "validate")
            self.assertEqual(
                0, result.returncode,
                msg=f"validator must accept superseded_by → done (completed) target:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )

    def test_validate_still_rejects_bare_string_superseded_by(self) -> None:
        # The list-type guard survives the relaxation: a bare-string scalar
        # is iterated character-by-character and must still be flagged.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._write_card(
                cwd, "origin",
                _card("origin", status="superseded", closed=True, dod_done=True,
                      extra="superseded_by: target\nsupersedes: []\n"),
            )
            self._write_card(
                cwd, "target",
                _card("target", status="open",
                      extra="superseded_by: []\nsupersedes:\n  - origin\n"),
            )
            result = self.run_goc(cwd, "validate")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("superseded_by", result.stdout + result.stderr)
            self.assertIn("must be a list", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
