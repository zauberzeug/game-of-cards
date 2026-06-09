from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PARKED_CARD = """\
---
title: parked-fixture
summary: "Parked fixture for close-side gate guard."
status: active
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: pretend the work is done
---

# parked-fixture

## Decision required

Option A vs Option B — pending human pick.
"""


CLOSED_BUT_GATED_CARD = """\
---
title: closed-but-gated
summary: "Already-closed fixture whose human_gate was left raised."
status: done
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: closed with a stale gate
---

# closed-but-gated
"""


class CloseTerminalGateGuardTest(unittest.TestCase):
    """`goc done`, `goc done --bundle`, `goc status <t> disproved`, and
    `goc status <t> superseded` must refuse to flip a card to a terminal
    state while `human_gate` is anything other than `none`. The validator
    must also reject any card that already carries that contradictory
    state, so a deck repaired by hand can be detected during CI.

    This is the symmetric counterpart to the existing `_cmd_decide` guard
    (engine.py:`_cmd_decide`), which refuses to record a decision on a
    gate that is already `none`."""

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
        readme = card_dir / "README.md"
        readme.write_text(body)
        return card_dir

    def test_done_refuses_card_with_decision_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_dir = self._write_card(cwd, "parked-fixture", PARKED_CARD)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(cwd, "done", "parked-fixture")

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("human_gate is 'decision'", result.stderr)
            self.assertIn("goc decide", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_done_refuses_card_with_session_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            body = PARKED_CARD.replace("human_gate: decision", "human_gate: session")
            card_dir = self._write_card(cwd, "parked-fixture", body)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(cwd, "done", "parked-fixture")

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("human_gate is 'session'", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_done_bundle_refuses_when_any_member_has_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            good = PARKED_CARD.replace("title: parked-fixture", "title: card-good").replace(
                "human_gate: decision", "human_gate: none"
            ).replace("# parked-fixture", "# card-good").replace(
                "## Decision required\n\nOption A vs Option B — pending human pick.\n",
                "",
            )
            bad = PARKED_CARD.replace("title: parked-fixture", "title: card-bad").replace(
                "# parked-fixture", "# card-bad"
            )
            self._write_card(cwd, "card-good", good)
            self._write_card(cwd, "card-bad", bad)

            result = self.run_goc(cwd, "done", "--bundle", "card-good", "card-bad")

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("card-bad", result.stderr)
            self.assertIn("human_gate is 'decision'", result.stderr)
            # No mutation: the good card is still active, no log entry written.
            readme_good = (cwd / ".game-of-cards" / "deck" / "card-good" / "README.md").read_text()
            self.assertIn("status: active", readme_good)
            self.assertFalse(
                (cwd / ".game-of-cards" / "deck" / "card-good" / "log.md").exists()
            )

    def test_status_disproved_refuses_card_with_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_dir = self._write_card(cwd, "parked-fixture", PARKED_CARD)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(
                cwd, "status", "parked-fixture", "disproved", "--no-commit"
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("human_gate is 'decision'", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_status_superseded_refuses_card_with_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # Successor card (referenced by --by) must exist and be loadable.
            successor = PARKED_CARD.replace(
                "title: parked-fixture", "title: successor-card"
            ).replace("# parked-fixture", "# successor-card").replace(
                "human_gate: decision", "human_gate: none"
            ).replace(
                "## Decision required\n\nOption A vs Option B — pending human pick.\n",
                "",
            )
            self._write_card(cwd, "successor-card", successor)
            card_dir = self._write_card(cwd, "parked-fixture", PARKED_CARD)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(
                cwd,
                "status",
                "parked-fixture",
                "superseded",
                "--by",
                "successor-card",
                "--no-commit",
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("human_gate is 'decision'", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_done_reports_terminal_status_not_dod_for_terminal_card(self) -> None:
        """A `disproved`/`superseded` card legitimately carries unchecked DoD
        boxes. `goc done` must refuse it with the authoritative terminal-status
        message, not the misleading 'unchecked DoD boxes' diagnostic — the
        status guard outranks the DoD-completeness gate."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            body = (
                CLOSED_BUT_GATED_CARD.replace("status: done", "status: disproved")
                .replace("human_gate: decision", "human_gate: none")
                .replace(
                    "  - [x] PROCESS: closed with a stale gate",
                    "  - [ ] PROCESS: never checked — card was disproved",
                )
            )
            card_dir = self._write_card(cwd, "closed-but-gated", body)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(cwd, "done", "closed-but-gated")

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("(terminal)", result.stderr)
            self.assertNotIn("unchecked DoD boxes", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_done_bundle_reports_terminal_status_not_dod_for_terminal_card(self) -> None:
        """The bundle path has the same guard-ordering contract: a terminal
        member with open DoD boxes is refused with the terminal-status reason."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            good = (
                PARKED_CARD.replace("title: parked-fixture", "title: card-good")
                .replace("human_gate: decision", "human_gate: none")
                .replace("# parked-fixture", "# card-good")
                .replace(
                    "## Decision required\n\nOption A vs Option B — pending human pick.\n",
                    "",
                )
            )
            bad = (
                CLOSED_BUT_GATED_CARD.replace("title: closed-but-gated", "title: card-bad")
                .replace("# closed-but-gated", "# card-bad")
                .replace("status: done", "status: disproved")
                .replace("human_gate: decision", "human_gate: none")
                .replace(
                    "  - [x] PROCESS: closed with a stale gate",
                    "  - [ ] PROCESS: never checked — card was disproved",
                )
            )
            self._write_card(cwd, "card-good", good)
            self._write_card(cwd, "card-bad", bad)

            result = self.run_goc(cwd, "done", "--bundle", "card-good", "card-bad")

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("card-bad", result.stderr)
            self.assertIn("(terminal)", result.stderr)
            self.assertNotIn("unchecked DoD boxes", result.stderr)

    def test_validate_rejects_card_with_terminal_status_and_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._write_card(cwd, "closed-but-gated", CLOSED_BUT_GATED_CARD)

            result = self.run_goc(cwd, "validate")

            self.assertNotEqual(
                result.returncode,
                0,
                msg=f"validator should reject a closed card with a raised gate:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            combined = result.stdout + result.stderr
            self.assertIn("human_gate", combined)
            self.assertIn("must be 'none'", combined)
            self.assertIn("closed-but-gated", combined)

    def test_validate_rejects_disproved_with_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            body = CLOSED_BUT_GATED_CARD.replace("status: done", "status: disproved")
            self._write_card(cwd, "closed-but-gated", body)

            result = self.run_goc(cwd, "validate")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("human_gate", result.stdout + result.stderr)

    def test_validate_rejects_superseded_with_gate_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # superseded_by requires a non-empty list whose target exists; build that.
            body = CLOSED_BUT_GATED_CARD.replace(
                "status: done", "status: superseded"
            ).replace(
                "advances: []", "advances: []\nsuperseded_by:\n  - successor-card\nsupersedes: []"
            )
            successor = CLOSED_BUT_GATED_CARD.replace(
                "title: closed-but-gated", "title: successor-card"
            ).replace("# closed-but-gated", "# successor-card").replace(
                "human_gate: decision", "human_gate: none"
            ).replace(
                "status: done", "status: open"
            ).replace(
                'closed_at: "2026-05-15T00:00:00Z"', "closed_at: null"
            )
            self._write_card(cwd, "closed-but-gated", body)
            self._write_card(cwd, "successor-card", successor)

            result = self.run_goc(cwd, "validate")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("human_gate", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
