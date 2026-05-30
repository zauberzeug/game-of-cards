from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


ORIGIN_CARD_TEMPLATE = """\
---
title: {title}
summary: "Origin card driven into the terminal --by guard."
status: open
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] PROCESS: placeholder
---

# {title}
"""


TERMINAL_SUCCESSOR_TEMPLATE = """\
---
title: {title}
summary: "Terminal-status successor used to exercise the routing guard."
status: {status}
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: terminal fixture
---

# {title}
"""


DEAD_END_ORIGIN_CARD = """\
---
title: dead-end-origin
summary: "Hand-crafted fixture where superseded_by lands on a terminal card."
status: superseded
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
superseded_by:
  - dead-end-target
supersedes: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: closed with a dead-end forward pointer
---

# dead-end-origin
"""


DEAD_END_TARGET_CARD = """\
---
title: dead-end-target
summary: "Terminal-status target of a hand-crafted dead-end superseded_by pointer."
status: done
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
superseded_by: []
supersedes:
  - dead-end-origin
tags: [bug]
definition_of_done: |
  - [x] PROCESS: terminal target
---

# dead-end-target
"""


class SupersededByMustBeLiveTest(unittest.TestCase):
    """`goc status <X> superseded --by <Y>` must refuse when `<Y>` is itself
    terminal (done, disproved, superseded), and `goc validate` must flag any
    hand-edited frontmatter where `superseded_by` already points at a
    terminal card. Both gates exist so the deck-as-record forward routing
    pointer always lands on live work."""

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

    def _scaffold_origin_and_terminal_successor(
        self, cwd: Path, origin_title: str, successor_title: str, successor_status: str
    ) -> Path:
        self._write_card(cwd, origin_title, ORIGIN_CARD_TEMPLATE.format(title=origin_title))
        return self._write_card(
            cwd,
            successor_title,
            TERMINAL_SUCCESSOR_TEMPLATE.format(title=successor_title, status=successor_status),
        )

    def _assert_cli_refuses_terminal_successor(self, terminal_status: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            origin_title = f"origin-for-{terminal_status}"
            successor_title = f"successor-{terminal_status}"
            origin_dir = cwd / ".game-of-cards" / "deck" / origin_title
            self._scaffold_origin_and_terminal_successor(
                cwd, origin_title, successor_title, terminal_status
            )
            origin_readme = origin_dir / "README.md"
            before = origin_readme.read_text()

            result = self.run_goc(
                cwd, "status", origin_title, "superseded", "--by", successor_title, "--no-commit"
            )

            self.assertEqual(
                2,
                result.returncode,
                msg=f"terminal successor ({terminal_status}) must be rejected:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("terminal", result.stderr)
            self.assertIn(terminal_status, result.stderr)
            self.assertEqual(before, origin_readme.read_text())

    def test_cli_refuses_done_successor(self) -> None:
        self._assert_cli_refuses_terminal_successor("done")

    def test_cli_refuses_disproved_successor(self) -> None:
        self._assert_cli_refuses_terminal_successor("disproved")

    def test_cli_refuses_superseded_successor(self) -> None:
        self._assert_cli_refuses_terminal_successor("superseded")

    def test_validate_flags_existing_dead_end_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._write_card(cwd, "dead-end-origin", DEAD_END_ORIGIN_CARD)
            self._write_card(cwd, "dead-end-target", DEAD_END_TARGET_CARD)

            result = self.run_goc(cwd, "validate")

            self.assertNotEqual(
                result.returncode,
                0,
                msg=f"validator should reject superseded_by pointing at a terminal target:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            combined = result.stdout + result.stderr
            self.assertIn("dead-end-origin", combined)
            self.assertIn("superseded_by", combined)
            self.assertIn("dead-end-target", combined)


if __name__ == "__main__":
    unittest.main()
