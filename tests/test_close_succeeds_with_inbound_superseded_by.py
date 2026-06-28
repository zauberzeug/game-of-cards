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
summary: "Live successor of card-a — the work the supersession was created to track."
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
summary: "Fresh successor for re-superseding card-b (the chain continues)."
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


class CloseSucceedsWithInboundSupersededByTest(unittest.TestCase):
    """Closing the successor of a supersession is allowed. After
    `goc status card-a superseded --by card-b`, `card-b` is the live work
    that replaced `card-a`; it MUST be completable (`goc done card-b`),
    abandonable (`goc status card-b disproved`), or itself re-superseded
    (`goc status card-b superseded --by card-c`). The removed close-time
    guard `_enforce_no_inbound_superseded_by_or_exit` used to make every
    such successor permanently un-closeable. `card-a` legitimately keeps
    routing forward to the now-terminal `card-b` — the record-axis walk
    has reached the resolution, and `goc validate` accepts it."""

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

    def _deck(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title / "README.md"

    def test_goc_done_closes_the_successor_of_a_supersession(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            result = self.run_goc(cwd, "done", "card-b")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("status: done", self._deck(cwd, "card-b").read_text())
            # card-a still routes forward to the now-done card-b.
            self.assertIn("card-b", self._deck(cwd, "card-a").read_text())
            validate = self.run_goc(cwd, "validate")
            self.assertEqual(0, validate.returncode, msg=validate.stdout + validate.stderr)

    def test_goc_done_bundle_closes_successor_with_unrelated_member(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            self._write_card(cwd, "card-unrelated", UNRELATED_CARD)
            result = self.run_goc(cwd, "done", "--bundle", "card-b", "card-unrelated")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("status: done", self._deck(cwd, "card-b").read_text())
            self.assertIn("status: done", self._deck(cwd, "card-unrelated").read_text())

    def test_goc_status_disproved_closes_the_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            result = self.run_goc(cwd, "status", "card-b", "disproved", "--no-commit")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("status: disproved", self._deck(cwd, "card-b").read_text())

    def test_goc_status_superseded_re_supersedes_the_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._seed_holder_and_successor(cwd)
            self._write_card(cwd, "card-c", THIRD_LIVE_CARD)
            result = self.run_goc(
                cwd, "status", "card-b", "superseded", "--by", "card-c", "--no-commit"
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("status: superseded", self._deck(cwd, "card-b").read_text())
            # The chain card-a → card-b → card-c is internally consistent.
            validate = self.run_goc(cwd, "validate")
            self.assertEqual(0, validate.returncode, msg=validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()
