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
        draft: bool = False,
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
            + ("draft: true\n" if draft else "")
            + "definition_of_done: |\n"
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

    # CASCADE_CHAIN_ROOT is a closure-gate signal: every live (non-terminal,
    # non-draft) card below a gated root waits on that one human action,
    # because `advanced-by-closed` keeps it from closing first. The cascade
    # fixtures therefore use the current encoding — downstream cards stay
    # `open` (or `active`) — not the retired `status: blocked`, which the
    # walk used to require and which no migrated deck holds any more.

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
                self.write_card(cwd, leaf, status="open", advanced_by=["decision-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN CASCADE_CHAIN_ROOT decision-root: "
                "3 cards cannot close until this one does (gate=decision)",
                result.stderr,
            )

    def test_cascade_chain_root_counts_active_and_legacy_blocked_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "session-root",
                status="open",
                human_gate="session",
                advances=["open-leaf", "active-leaf", "blocked-leaf"],
            )
            self.write_card(cwd, "open-leaf", status="open", advanced_by=["session-root"])
            self.write_card(cwd, "active-leaf", status="active", advanced_by=["session-root"])
            self.write_card(cwd, "blocked-leaf", status="blocked", advanced_by=["session-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN CASCADE_CHAIN_ROOT session-root: "
                "3 cards cannot close until this one does (gate=session)",
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
                self.write_card(cwd, leaf, status="open", advanced_by=["decision-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

    def test_cascade_chain_root_needs_a_raised_gate(self) -> None:
        # The same three-card fan-out below an ungated root: no human cord to
        # pull, so no warning however much closure waits on it.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "ungated-root",
                status="open",
                human_gate="none",
                advances=["leaf-a", "leaf-b", "leaf-c"],
            )
            for leaf in ("leaf-a", "leaf-b", "leaf-c"):
                self.write_card(cwd, leaf, status="open", advanced_by=["ungated-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

    def test_cascade_walks_transitively_through_open_chain(self) -> None:
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
                status="open",
                advanced_by=["decision-root"],
                advances=["leaf-a", "leaf-b"],
            )
            self.write_card(cwd, "leaf-a", status="open", advanced_by=["mid-card"])
            self.write_card(cwd, "leaf-b", status="active", advanced_by=["mid-card"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN CASCADE_CHAIN_ROOT decision-root: 3 cards cannot close until this one does",
                result.stderr,
            )
            # mid-card is not gated, so it is not a root of its own.
            self.assertNotIn("WARN CASCADE_CHAIN_ROOT mid-card", result.stderr)

    def _write_cascade_with_dead_descendant(self, cwd: Path, *, dead_status: str, draft: bool) -> None:
        """root -> {dead-card, live-a, live-b}; dead-card -> live-c.

        Exactly two cards are held up by the root: live-a and live-b. Counting
        dead-card, walking through it to live-c, or both, reaches the threshold
        of 3 — so one silent assertion catches every way of mishandling it.
        """
        self.write_card(
            cwd,
            "decision-root",
            status="open",
            human_gate="decision",
            advances=["dead-card", "live-a", "live-b"],
        )
        self.write_card(
            cwd,
            "dead-card",
            status=dead_status,
            draft=draft,
            advanced_by=["decision-root"],
            advances=["live-c"],
        )
        self.write_card(cwd, "live-a", status="open", advanced_by=["decision-root"])
        self.write_card(cwd, "live-b", status="open", advanced_by=["decision-root"])
        self.write_card(cwd, "live-c", status="open", advanced_by=["dead-card"])

    def test_cascade_neither_counts_nor_walks_through_a_terminal_descendant(self) -> None:
        for dead_status in ("done", "disproved"):
            with self.subTest(dead_status=dead_status), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                self._write_cascade_with_dead_descendant(cwd, dead_status=dead_status, draft=False)

                result = self.run_goc(cwd, "validate", "--quiet")

                self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
                self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

    def test_cascade_neither_counts_nor_walks_through_a_draft_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._write_cascade_with_dead_descendant(cwd, dead_status="open", draft=True)

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

    def test_cascade_chain_root_is_never_a_draft_or_closed_card(self) -> None:
        # A draft root is not yet real work (`goc new` stamps `draft: true`
        # beside its default `decision` gate); a closed root holds nothing up.
        # The closed one is only reachable on a hand-edited deck, which the
        # gate-on-terminal ERROR already rejects.
        for root_status, draft, expected_exit in (("open", True, 0), ("done", False, 1)):
            with self.subTest(root_status=root_status, draft=draft), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                self.write_card(
                    cwd,
                    "gated-root",
                    status=root_status,
                    human_gate="decision",
                    draft=draft,
                    advances=["leaf-a", "leaf-b", "leaf-c"],
                )
                for leaf in ("leaf-a", "leaf-b", "leaf-c"):
                    self.write_card(cwd, leaf, status="open", advanced_by=["gated-root"])

                result = self.run_goc(cwd, "validate", "--quiet")

                self.assertEqual(expected_exit, result.returncode, msg=f"stderr:\n{result.stderr}")
                if expected_exit:
                    self.assertIn("human_gate: must be 'none' when status=done", result.stderr)
                self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

    def test_cascade_does_not_count_the_root_on_a_cycle_back_to_it(self) -> None:
        # decision-root -> a -> b -> decision-root: two cards wait on the root,
        # not three. The cycle itself is a validate ERROR.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "decision-root",
                status="open",
                human_gate="decision",
                advances=["cycle-a"],
                advanced_by=["cycle-b"],
            )
            self.write_card(cwd, "cycle-a", advanced_by=["decision-root"], advances=["cycle-b"])
            self.write_card(cwd, "cycle-b", advanced_by=["cycle-a"], advances=["decision-root"])

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(1, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("cycle", result.stderr.lower())
            self.assertNotIn("CASCADE_CHAIN_ROOT", result.stderr)

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
