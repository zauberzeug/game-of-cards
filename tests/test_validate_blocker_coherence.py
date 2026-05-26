from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ValidateBlockerCoherenceTest(unittest.TestCase):
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
        *,
        status: str = "open",
        human_gate: str = "none",
        advanced_by: list[str] | None = None,
        advances: list[str] | None = None,
        dod: str | None = None,
    ) -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        done = "x" if status == "done" else " "
        closed_at = "2026-05-04" if status in {"done", "disproved", "superseded"} else "null"

        def fmt(items: list[str] | None) -> str:
            if not items:
                return "[]"
            return "\n" + "\n".join(f"  - {item}" for item in items)

        dod_block = dod if dod is not None else f"  - [{done}] PROCESS: test card"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            f"closed_at: {closed_at}\n"
            f"human_gate: {human_gate}\n"
            f"advances: {fmt(advances)}\n"
            f"advanced_by: {fmt(advanced_by)}\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            f"{dod_block}\n"
            "---\n\n"
            f"# {title}\n"
        )
        (card_dir / "log.md").write_text("")

    def test_stale_blocked_warning_fires_when_all_blockers_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "prereq-card", status="done", advances=["blocked-card"])
            self.write_card(cwd, "blocked-card", status="blocked", advanced_by=["prereq-card"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN STALE_BLOCKED blocked-card: all advanced_by entries inactive: [prereq-card=done]",
                result.stderr,
            )

    def test_partial_blocked_does_not_fire_stale_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "done-prereq", status="done", advances=["blocked-card"])
            self.write_card(cwd, "active-prereq", status="active", advances=["blocked-card"])
            self.write_card(
                cwd,
                "blocked-card",
                status="blocked",
                advanced_by=["done-prereq", "active-prereq"],
            )

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("STALE_BLOCKED", result.stderr)

    def test_orphan_blocked_warning_fires_for_gate_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "orphan-card", status="blocked", human_gate="none")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("WARN ORPHAN_BLOCKED orphan-card:", result.stderr)

    def test_orphan_blocked_suppressed_when_gate_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "park-decision", status="blocked", human_gate="decision")
            self.write_card(cwd, "park-session", status="blocked", human_gate="session")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("ORPHAN_BLOCKED", result.stderr)

    def test_cascade_chain_root_fires_at_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "decision-root",
                status="open",
                human_gate="decision",
                advances=["leaf-a", "leaf-b", "leaf-c"],
            )
            for leaf in ("leaf-a", "leaf-b", "leaf-c"):
                self.write_card(cwd, leaf, status="blocked", advanced_by=["decision-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN CASCADE_CHAIN_ROOT decision-root: 3 blocked cards rooted here (gate=decision)",
                result.stderr,
            )

    def test_cascade_chain_root_does_not_fire_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "decision-root",
                status="open",
                human_gate="decision",
                advances=["leaf-a", "leaf-b"],
            )
            for leaf in ("leaf-a", "leaf-b"):
                self.write_card(cwd, leaf, status="blocked", advanced_by=["decision-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

    def test_cascade_walks_transitively_through_blocked_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "decision-root",
                status="open",
                human_gate="decision",
                advances=["mid-card"],
            )
            self.write_card(
                cwd,
                "mid-card",
                status="blocked",
                advanced_by=["decision-root"],
                advances=["leaf-a", "leaf-b"],
            )
            for leaf in ("leaf-a", "leaf-b"):
                self.write_card(cwd, leaf, status="blocked", advanced_by=["mid-card"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN CASCADE_CHAIN_ROOT decision-root: 3 blocked cards rooted here",
                result.stderr,
            )

    def test_warnings_do_not_fail_exit_alongside_clean_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-card", status="open")
            self.write_card(cwd, "done-card", status="done")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("WARN", result.stderr)

    def test_untagged_dod_item_warning_fires_for_open_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "untagged-card", status="open", dod="  - [ ] do the thing")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("WARN UNTAGGED_DOD_ITEM untagged-card:", result.stderr)

    def test_tagged_dod_item_does_not_fire_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "tagged-card",
                status="open",
                dod="  - [ ] TDD: assertion holds\n  - [ ] MECHANICAL: edit lands",
            )

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("UNTAGGED_DOD_ITEM", result.stderr)

    def test_untagged_dod_item_suppressed_for_closed_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "done-untagged", status="done", dod="  - [x] do the thing")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("UNTAGGED_DOD_ITEM", result.stderr)


if __name__ == "__main__":
    unittest.main()
