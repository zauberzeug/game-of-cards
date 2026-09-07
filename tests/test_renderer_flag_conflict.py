"""Regression guard: `--board` and `--json` are mutually exclusive renderers.

`_cmd_default` used to select the renderer with a bare
`if args.board: … elif args.as_json: …` chain, so `goc --board --json`
printed an ASCII kanban board with exit 0 and an empty stderr. A caller
that asked for machine-readable output got a table, and the only
diagnostic surfaced one hop downstream as a `jq` parse error.

Every other conflicting-flag pair reachable from the same function
refuses with exit 2 — `--done` with `--status`, `--since` without
`--done`, and `--commit` with `--no-commit` on the mutating verbs. This
test pins the renderer pair to that contract in both flag orders, and
pins the two flags' solo behaviour so the guard cannot over-fire.

See the card
`board-flag-silently-overrides-json-and-returns-an-ascii-table`.
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
sys.path.insert(0, str(ROOT))

CARD = """\
---
title: probe-card
summary: probe-card
status: open
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: test card
---

# probe-card
"""


class RendererFlagConflictTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = Path(self._tmp.name)
        card_dir = self.cwd / ".game-of-cards" / "deck" / "probe-card"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(CARD, encoding="utf-8")
        (card_dir / "log.md").write_text("", encoding="utf-8")
        self.env = os.environ.copy()
        pythonpath = self.env.get("PYTHONPATH")
        self.env["PYTHONPATH"] = (
            str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        )
        # Isolate from a runner-scoped GOC_WORKER, which would filter the
        # fixture card out of the queue and make every assertion vacuous.
        self.env.pop("GOC_WORKER", None)

    def _goc(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *argv],
            cwd=self.cwd,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_board_then_json_refuses(self) -> None:
        result = self._goc("--status", "all", "--board", "--json")
        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("--board", result.stderr)
        self.assertIn("--json", result.stderr)
        self.assertEqual("", result.stdout)

    def test_json_then_board_refuses(self) -> None:
        # argparse imposes no ordering, so the reversed spelling must refuse
        # identically — the pre-fix `if/elif` took the board branch either way.
        result = self._goc("--status", "all", "--json", "--board")
        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("--board", result.stderr)
        self.assertIn("--json", result.stderr)
        self.assertEqual("", result.stdout)

    def test_json_alone_still_emits_json(self) -> None:
        result = self._goc("--status", "all", "--json")
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(["probe-card"], [c["title"] for c in payload])

    def test_board_alone_still_renders_the_board(self) -> None:
        result = self._goc("--status", "all", "--board")
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("OPEN", result.stdout)
        self.assertIn("probe-card", result.stdout)

    def test_refusal_precedes_the_deck_walk(self) -> None:
        """The guard must fire before `load_all_cards()`.

        A usage error should not depend on — or pay for — reading the deck.
        Pointed at a directory with no deck at all, the conflict still
        refuses with exit 2 rather than the loader's own diagnostic.
        """
        with tempfile.TemporaryDirectory() as empty:
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "--board", "--json"],
                cwd=empty,
                env=self.env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("--board", result.stderr)
        self.assertIn("--json", result.stderr)

    def test_help_text_documents_the_exclusion(self) -> None:
        """Each flag's own `--help` entry names the other.

        Read off the parser actions rather than `format_help()`: argparse
        wraps help text at the terminal width, so a line-oriented scrape
        splits the very cross-reference this asserts.
        """
        from goc.engine import _build_parser

        helps = {
            action.dest: action.help or ""
            for action in _build_parser()._actions
            if action.dest in ("board", "as_json")
        }
        self.assertIn("--json", helps["board"])
        self.assertIn("--board", helps["as_json"])


if __name__ == "__main__":
    unittest.main()
