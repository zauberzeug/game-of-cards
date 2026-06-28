from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


ACTIVE_CARD = """\
---
title: orphan-fixture
summary: "Active fixture used to drive supersede-without-by attempts."
status: active
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: pretend the work is done
---

# orphan-fixture
"""


ORPHAN_SUPERSEDED_CARD = """\
---
title: orphan-superseded
summary: "Hand-crafted fixture that lands at status: superseded with no superseded_by."
status: superseded
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: closed without a forward routing pointer
---

# orphan-superseded
"""


class SupersededRequiresByTest(unittest.TestCase):
    """`goc status <c> superseded` without `--by` must be refused at the CLI
    boundary, and `goc validate` must reject any hand-edited frontmatter that
    lands at `status: superseded` with an empty `superseded_by` list. Both
    gates exist so the deck-as-record axis always has a typed forward routing
    pointer to follow."""

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

    def test_cli_refuses_status_superseded_without_by(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_dir = self._write_card(cwd, "orphan-fixture", ACTIVE_CARD)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(
                cwd, "status", "orphan-fixture", "superseded", "--no-commit"
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("requires --by", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_validate_rejects_superseded_with_empty_superseded_by(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._write_card(cwd, "orphan-superseded", ORPHAN_SUPERSEDED_CARD)

            result = self.run_goc(cwd, "validate")

            self.assertNotEqual(
                result.returncode,
                0,
                msg=f"validator should reject status: superseded with empty superseded_by:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            combined = result.stdout + result.stderr
            self.assertIn("orphan-superseded", combined)
            self.assertIn("superseded_by", combined)


if __name__ == "__main__":
    unittest.main()
