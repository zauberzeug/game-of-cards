from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# A card that reached a terminal status while still carrying a raised gate —
# the contradictory state `goc validate` flags but, before this fix, no verb
# could repair. Reachable via older closures, hand-edits, or `goc migrate`.
CLOSED_BUT_GATED = """\
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

## Decision required

Option A vs Option B — left dangling at close.
"""


CLEANLY_DONE = """\
---
title: cleanly-done
summary: "A cleanly-closed card — gate already none, nothing to decide."
status: done
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] PROCESS: closed cleanly
---

# cleanly-done
"""


class DecideRepairsTerminalGateTest(unittest.TestCase):
    """`goc decide` is the repair verb for the `status: terminal` +
    `human_gate != none` contradiction the validator flags. The close-time
    verbs refuse to *create* that state; `goc decide` is what *clears* it on
    a card that landed there via an old closure, a hand-edit, or a migrate
    import. It records the resolving decision, lowers the gate to `none`, and
    leaves the card closed — so `goc validate` passes afterward. A *cleanly*
    closed card (gate already `none`) is still refused, because there is no
    pending gate to lower."""

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

    def _assert_repairs(self, body: str, terminal_status: str, extra_cards=None) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_dir = self._write_card(cwd, "closed-but-gated", body)
            for title, card_body in (extra_cards or {}).items():
                self._write_card(cwd, title, card_body)
            readme = card_dir / "README.md"

            # Precondition: validator rejects the contradictory state.
            pre = self.run_goc(cwd, "validate")
            self.assertNotEqual(pre.returncode, 0, msg="validator should reject terminal+gate-raised")

            result = self.run_goc(
                cwd, "decide", "closed-but-gated",
                "--decision", "close out the dangling gate",
                "--because", "card already terminal; clearing stale gate",
                "--no-commit",
            )
            self.assertEqual(
                0, result.returncode,
                msg=f"decide must repair the gate on a {terminal_status} card:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            text = readme.read_text()
            self.assertIn("human_gate: none", text)
            # The card stays closed — repair must not reopen it.
            self.assertIn(f"status: {terminal_status}", text)
            # Output must not falsely promise the card is pullable.
            self.assertNotIn("any agent can now claim this card", result.stdout)
            self.assertTrue((card_dir / "log.md").exists())

            post = self.run_goc(cwd, "validate")
            self.assertEqual(
                0, post.returncode,
                msg=f"validate must pass after repair:\nstdout:\n{post.stdout}\nstderr:\n{post.stderr}",
            )

    def test_repairs_done_card(self) -> None:
        self._assert_repairs(CLOSED_BUT_GATED, "done")

    def test_repairs_disproved_card(self) -> None:
        body = CLOSED_BUT_GATED.replace("status: done", "status: disproved")
        self._assert_repairs(body, "disproved")

    def test_repairs_superseded_card(self) -> None:
        body = CLOSED_BUT_GATED.replace("status: done", "status: superseded").replace(
            "advances: []", "advances: []\nsuperseded_by:\n  - live-successor\nsupersedes: []"
        )
        successor = """\
---
title: live-successor
summary: "Live successor for the superseded repair fixture."
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
  - closed-but-gated
tags: [bug]
definition_of_done: |
  - [ ] PROCESS: live tail
---

# live-successor
"""
        self._assert_repairs(body, "superseded", extra_cards={"live-successor": successor})

    def test_still_refuses_cleanly_closed_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_dir = self._write_card(cwd, "cleanly-done", CLEANLY_DONE)
            before = (card_dir / "README.md").read_text()
            result = self.run_goc(
                cwd, "decide", "cleanly-done",
                "--decision", "x", "--because", "y", "--no-commit",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gate already 'none'", result.stderr)
            self.assertEqual(before, (card_dir / "README.md").read_text())
            self.assertFalse((card_dir / "log.md").exists())


if __name__ == "__main__":
    unittest.main()
