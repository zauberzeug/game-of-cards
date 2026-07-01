from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WaitingFilterStatusScopeTest(unittest.TestCase):
    """`goc --waiting` must surface impeded cards regardless of progress
    status — a card may be `status: active` AND carry `waiting_on` (the
    three-axis stuck model). The default status filter must not drop active
    impeded cards before the `--waiting` filter runs.
    """

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

    def write_card(
        self,
        cwd: Path,
        title: str,
        status: str,
        waiting_on: str | None,
        waiting_until: str | None = None,
        closed_at: str | None = None,
        draft: bool = False,
    ) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        overlay = f"waiting_on: {waiting_on}\n" if waiting_on is not None else ""
        if waiting_until is not None:
            overlay += f"waiting_until: {waiting_until}\n"
        if draft:
            overlay += "draft: true\n"
        closed = f'"{closed_at}"' if closed_at is not None else "null"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            f"closed_at: {closed}\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            f"{overlay}"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def titles(self, result: subprocess.CompletedProcess[str]) -> set[str]:
        return {c["title"] for c in json.loads(result.stdout)}

    def test_waiting_surfaces_active_impeded_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-impeded", "open", "external")
            self.write_card(cwd, "active-impeded", "active", "external")
            self.write_card(cwd, "open-clear", "open", None)

            result = self.run_goc(cwd, "--waiting", "--json")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            titles = self.titles(result)
            self.assertIn("open-impeded", titles)
            self.assertIn("active-impeded", titles)
            self.assertNotIn("open-clear", titles)

    def test_waiting_matches_impedes_predicate(self) -> None:
        """`--waiting` must mirror `waiting_impedes`, not the weaker
        `waiting_on is not None` condition: a bare `waiting_until`-only
        deferral (no reason) is impeded and must appear, while an elapsed
        `waiting_until` has resurfaced and must NOT appear even though its
        `waiting_on` field is still set.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # Bare deferral: future waiting_until, no waiting_on → impeded.
            self.write_card(cwd, "bare-deferral", "open", None, "2099-12-31")
            # Open-ended block: reason, no date → impeded.
            self.write_card(cwd, "open-block", "open", "external")
            # Elapsed wait: reason + past date → resurfaced, NOT impeded.
            self.write_card(cwd, "elapsed-wait", "open", "external", "2020-01-01")

            result = self.run_goc(cwd, "--waiting", "--json")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            titles = self.titles(result)
            self.assertIn("bare-deferral", titles)
            self.assertIn("open-block", titles)
            self.assertNotIn("elapsed-wait", titles)

    def test_waiting_excludes_terminal_cards_with_stale_overlay(self) -> None:
        """`--waiting` surfaces *active* impediments only. Closing a card
        never clears its `waiting_on` / `waiting_until` overlay (a
        documented invariant), so a terminal card carries a stale overlay
        forever. It must NOT appear in the impeded view — mirroring the
        board renderer's `live` gate — while live impeded cards still do.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-impeded", "open", "external")
            self.write_card(cwd, "active-impeded", "active", "external")
            for term in ("done", "disproved", "superseded"):
                self.write_card(
                    cwd, f"{term}-stale", term, "external",
                    waiting_until="2099-12-31", closed_at="2026-05-10",
                )

            result = self.run_goc(cwd, "--waiting", "--json")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            titles = self.titles(result)
            self.assertIn("open-impeded", titles)
            self.assertIn("active-impeded", titles)
            for term in ("done", "disproved", "superseded"):
                self.assertNotIn(f"{term}-stale", titles)

    def test_waiting_excludes_draft_scaffolds_with_overlay(self) -> None:
        """`--waiting` surfaces *actionable* impediments only. A `draft: true`
        scaffold is not yet real work — it is hidden from the queue and
        rendered with the `✎` glyph (never `⏳`) on the board. `--waiting`
        must apply the same draft exclusion the board's `card_cell` gate does,
        so the impeded view and the board cannot disagree, while non-draft
        impeded cards still appear.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-impeded", "open", "external")
            self.write_card(
                cwd, "draft-impeded", "open", "external", draft=True,
            )

            result = self.run_goc(cwd, "--waiting", "--json")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            titles = self.titles(result)
            self.assertIn("open-impeded", titles)
            self.assertNotIn("draft-impeded", titles)

    def test_explicit_status_open_still_narrows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-impeded", "open", "external")
            self.write_card(cwd, "active-impeded", "active", "external")

            result = self.run_goc(cwd, "--waiting", "--status", "open", "--json")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            titles = self.titles(result)
            self.assertIn("open-impeded", titles)
            self.assertNotIn("active-impeded", titles)


if __name__ == "__main__":
    unittest.main()
