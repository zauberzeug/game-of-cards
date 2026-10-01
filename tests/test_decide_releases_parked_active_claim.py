"""`goc decide` hands a card parked while `active` back to the pull queue.

Skill(pull-card) claims a card (`goc status <t> active`) before it can hit the
judgement call that raises the gate, so the Andon cord ordinarily leaves the
card parked at `status: active`. Lowering the gate alone left `active` +
`human_gate: none` — the shape of a live agent claim. `goc`, `goc --ready` and
pull-card.yml's launch count all require `status: open`, and pull-card treats
every active card as someone's soft lock, so the decided card was pulled by
nobody while `goc decide`'s own `Next:` line said any agent could claim it.

These tests pin the round trip: claim → raise the gate → `goc decide` → the
card is pullable again, and the `Next:` line's promise matches the queue.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TITLE = "probe-card"
CLAIM_PROMISE = "any agent can now claim this card"


CARD = """\
---
title: probe-card
summary: "Authored probe card for the decide round trip."
status: {status}
stage: null
contribution: medium
created: "2026-09-28T00:00:00Z"
closed_at: null
human_gate: {gate}
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: probe item
---

# probe-card
{extra}"""

DECISION_REQUIRED = "\n## Decision required\n\n- **A** — one way.\n- **B** — another way.\n"


class DecideReleasesParkedActiveClaimTest(unittest.TestCase):
    def goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env.pop("GOC_WORKER", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd, env=env, text=True, capture_output=True, check=False,
        )

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout

    def readme(self, cwd: Path) -> Path:
        return cwd / ".game-of-cards" / "deck" / TITLE / "README.md"

    def write_card(self, cwd: Path, *, status: str, gate: str, extra: str = "") -> None:
        readme = self.readme(cwd)
        readme.parent.mkdir(parents=True)
        readme.write_text(CARD.format(status=status, gate=gate, extra=extra))

    def listed(self, cwd: Path, *query: str) -> bool:
        result = self.goc(cwd, *query, "--json")
        self.assertEqual(0, result.returncode, msg=result.stderr)
        return TITLE in [c["title"] for c in json.loads(result.stdout)]

    def next_line(self, result: subprocess.CompletedProcess[str]) -> str:
        return next(ln for ln in result.stdout.splitlines() if ln.startswith("Next:"))

    def assert_pullable(self, cwd: Path) -> None:
        text = self.readme(cwd).read_text()
        self.assertIn("status: open", text)
        self.assertIn("human_gate: none", text)
        self.assertTrue(self.listed(cwd, "--ready"), msg="decided card missing from goc --ready")
        # pull-card.yml's launch gate counts exactly this query.
        self.assertTrue(
            self.listed(cwd, "--status", "open", "--human-gate", "none"),
            msg="decided card missing from the pull-card workflow's launch count",
        )
        self.assertFalse(
            self.listed(cwd, "--status", "active"),
            msg="decided card still reads as a live claim (soft lock)",
        )

    def test_card_parked_while_active_is_released_to_the_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.git(cwd, "init", "-q", "-b", "main")
            self.git(cwd, "config", "user.name", "Probe User")
            self.git(cwd, "config", "user.email", "probe@example.com")
            self.write_card(cwd, status="open", gate="none")
            self.git(cwd, "add", "-A")
            self.git(cwd, "commit", "-q", "-m", "seed")

            # pull-card: claim, then pull the Andon cord on the claimed card.
            claim = self.goc(cwd, "status", TITLE, "active")
            self.assertEqual(0, claim.returncode, msg=claim.stderr)
            readme = self.readme(cwd)
            readme.write_text(
                readme.read_text().replace("human_gate: none", "human_gate: decision")
                + DECISION_REQUIRED
            )
            self.git(cwd, "commit", "-q", "-am", "park probe-card at decision")
            self.assertIn("status: active", readme.read_text())

            result = self.goc(cwd, "decide", TITLE, "--decision", "go with A", "--because", "cheaper")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn(f"{TITLE}: decision recorded; gate decision → none", result.stdout)
            self.assertIn(f"{TITLE}: active → open", result.stdout)
            self.assert_pullable(cwd)

            # The Next: line tells the truth: the promised claim is real, and
            # the session that parked the card is told how to keep it.
            next_line = self.next_line(result)
            self.assertIn(CLAIM_PROMISE, next_line)
            self.assertIn(f"goc status {TITLE} active", next_line)

            # The journal records the release beside the decision.
            log = (readme.parent / "log.md").read_text()
            self.assertIn("Gate decision → none. Status active → open", log)

            # The release lands in the decide commit, not as a dirty tree.
            self.assertEqual("", self.git(cwd, "status", "--porcelain"))
            committed = self.git(cwd, "show", f"HEAD:.game-of-cards/deck/{TITLE}/README.md")
            self.assertIn("status: open", committed)
            self.assertIn("human_gate: none", committed)

            # Like `goc status <title> open`, the release keeps the worker
            # designation, and the next claim succeeds.
            self.assertIn("worker:", readme.read_text())
            reclaim = self.goc(cwd, "status", TITLE, "active")
            self.assertEqual(0, reclaim.returncode, msg=reclaim.stderr)
            self.assertIn(f"{TITLE}: open → active", reclaim.stdout)
            self.assertNotIn("possible racing claim", reclaim.stderr)

            validate = self.goc(cwd, "validate")
            self.assertEqual(0, validate.returncode, msg=validate.stdout + validate.stderr)

    def test_card_parked_while_open_stays_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, status="open", gate="decision", extra=DECISION_REQUIRED)

            result = self.goc(
                cwd, "decide", TITLE, "--decision", "go with A", "--because", "cheaper",
                "--no-commit",
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertNotIn("active → open", result.stdout)
            self.assertNotIn("Status active → open", (self.readme(cwd).parent / "log.md").read_text())
            self.assert_pullable(cwd)
            self.assertIn(CLAIM_PROMISE, self.next_line(result))


if __name__ == "__main__":
    unittest.main()
