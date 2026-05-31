from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


LIVE_SUCCESSOR_CARD = """\
---
title: card-b
summary: "Live successor of card-a; the target this close-time guard protects."
status: open
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
superseded_by: []
supersedes:
  - card-a
tags: [bug]
definition_of_done: |
  - [x] PROCESS: ready to close
---

# card-b
"""


HOLDER_CARD = """\
---
title: card-a
summary: "Card that supersession-routes forward to card-b."
status: superseded
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
superseded_by:
  - card-b
supersedes: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: replaced by card-b
---

# card-a
"""


UNRELATED_CARD = """\
---
title: card-unrelated
summary: "Innocent bystander used for the --bundle path."
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
  - [x] PROCESS: ready to close
---

# card-unrelated
"""


THIRD_LIVE_CARD = """\
---
title: card-c
summary: "Fresh live successor for the `status superseded --by` path."
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

# card-c
"""


class CloseWithInboundSupersededByTest(unittest.TestCase):
    """All close-time verbs (`goc done`, `goc done --bundle`,
    `goc status <X> disproved`, `goc status <X> superseded --by <new>`)
    must refuse to close a card that another card still routes forward
    to via `superseded_by`. Without this guard, the holder's typed
    forward routing pointer lands on a terminal card — the dead-end
    shape `validate_superseded_by_targets` catches reactively at read
    time. The close-time guard prevents the dead end from ever landing."""

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

    def _seed_holder_and_successor(self, cwd: Path) -> None:
        self._write_card(cwd, "card-a", HOLDER_CARD)
        self._write_card(cwd, "card-b", LIVE_SUCCESSOR_CARD)

    def _assert_rejected_naming_holder(
        self,
        result: subprocess.CompletedProcess[str],
        b_readme: Path,
        expected_status_in_msg: str,
    ) -> None:
        self.assertEqual(
            2,
            result.returncode,
            msg=f"close should be rejected:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("card-a", result.stderr)
        self.assertIn("superseded_by", result.stderr)
        self.assertIn(expected_status_in_msg, result.stderr)
        # card-b must remain live (status: open) — no partial mutation.
        self.assertIn("status: open", b_readme.read_text())

    def test_goc_done_refuses_when_inbound_superseded_by_holder_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            b_readme = cwd / ".game-of-cards" / "deck" / "card-b" / "README.md"
            result = self.run_goc(cwd, "done", "card-b")
            self._assert_rejected_naming_holder(result, b_readme, "done")

    def test_goc_done_bundle_refuses_when_member_has_inbound_holder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            self._write_card(cwd, "card-unrelated", UNRELATED_CARD)
            b_readme = cwd / ".game-of-cards" / "deck" / "card-b" / "README.md"
            unrelated_readme = cwd / ".game-of-cards" / "deck" / "card-unrelated" / "README.md"
            result = self.run_goc(cwd, "done", "--bundle", "card-b", "card-unrelated")
            self._assert_rejected_naming_holder(result, b_readme, "done")
            # Atomicity: the unrelated member must NOT have been partially closed.
            self.assertIn("status: open", unrelated_readme.read_text())

    def test_goc_status_disproved_refuses_when_inbound_holder_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            b_readme = cwd / ".game-of-cards" / "deck" / "card-b" / "README.md"
            result = self.run_goc(cwd, "status", "card-b", "disproved", "--no-commit")
            self._assert_rejected_naming_holder(result, b_readme, "disproved")

    def test_goc_status_superseded_refuses_when_inbound_holder_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            self._write_card(cwd, "card-c", THIRD_LIVE_CARD)
            b_readme = cwd / ".game-of-cards" / "deck" / "card-b" / "README.md"
            result = self.run_goc(
                cwd, "status", "card-b", "superseded", "--by", "card-c", "--no-commit"
            )
            self._assert_rejected_naming_holder(result, b_readme, "superseded")


if __name__ == "__main__":
    unittest.main()
