"""`goc decide` must name unclosed `advanced_by` prerequisites before it
reports the gate flip — and must stay non-blocking while doing so.

Lowering a gate is what makes a card autonomously pullable ("any agent can now
claim this card"), so a decision taken without its prerequisite is a decision an
unattended worker may act on before any human sees the card again. The queue and
board renderers carry a dependency advisory for the *work* moment;
`_cmd_decide` carried none.

The advisory is derived from `dependency_advisory` — the same helper the
renderers consume — in its default terminal-gated form, NOT the stricter
`queue_only` slice. This pins both the wiring and the slice choice, plus the
negative cases (all prerequisites terminal, no prerequisites at all).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from goc import engine


ROOT = Path(__file__).resolve().parents[1]


def _card(title: str, status: str, advanced_by: list[str]) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": status,
            "contribution": "medium",
            "human_gate": "decision",
            "created": "2026-07-26",
            "summary": f"{title} summary",
            "tags": [],
            "advances": [],
            "advanced_by": advanced_by,
            "supersedes": [],
            "superseded_by": [],
            "definition_of_done": "- [ ] MECHANICAL: test card\n",
        },
        body="body",
        dod_open=1,
        dod_done=0,
    )


class UnclosedPrerequisiteNoticeTest(unittest.TestCase):
    """Unit-level contract of the notice builder."""

    def setUp(self) -> None:
        self.open_prereq = _card("prereq-open", "open", [])
        self.by_title = {"prereq-open": self.open_prereq}

    def test_names_the_open_prerequisite_and_its_status(self) -> None:
        card = _card("gated-card", "open", ["prereq-open"])
        notice = engine._unclosed_prerequisite_notice(card, self.by_title)
        self.assertIsNotNone(notice)
        self.assertIn("prereq-open", notice)
        self.assertIn("(open)", notice)
        self.assertIn("1 unclosed prerequisite", notice)

    def test_no_prerequisites_produces_no_notice(self) -> None:
        card = _card("gated-card", "open", [])
        self.assertIsNone(engine._unclosed_prerequisite_notice(card, self.by_title))

    def test_terminal_prerequisites_produce_no_notice(self) -> None:
        for terminal_status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(prereq_status=terminal_status):
                by_title = {"prereq": _card("prereq", terminal_status, [])}
                card = _card("gated-card", "open", ["prereq"])
                self.assertIsNone(
                    engine._unclosed_prerequisite_notice(card, by_title)
                )

    def test_mixed_prerequisites_name_only_the_unclosed_ones(self) -> None:
        by_title = {
            "prereq-open": _card("prereq-open", "open", []),
            "prereq-active": _card("prereq-active", "active", []),
            "prereq-done": _card("prereq-done", "done", []),
        }
        card = _card(
            "gated-card", "open", ["prereq-open", "prereq-done", "prereq-active"]
        )
        notice = engine._unclosed_prerequisite_notice(card, by_title)
        self.assertIsNotNone(notice)
        self.assertIn("2 unclosed prerequisites", notice)
        self.assertIn("prereq-open", notice)
        self.assertIn("prereq-active", notice)
        self.assertNotIn("prereq-done", notice)

    def test_dangling_prerequisite_is_named_as_not_found(self) -> None:
        # `dependency_blockers` treats an unknown title as non-terminal; the
        # notice must render a status label rather than crash on the None card.
        card = _card("gated-card", "open", ["ghost-card"])
        notice = engine._unclosed_prerequisite_notice(card, {})
        self.assertIsNotNone(notice)
        self.assertIn("ghost-card", notice)
        self.assertIn("not found", notice)

    def test_terminal_card_produces_no_notice(self) -> None:
        # On a terminal card `goc decide` is the record-axis gate repair; the
        # card never "starts", so prerequisites are moot. Inherited from
        # `dependency_advisory`'s terminal gate rather than re-inlined.
        for terminal_status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(card_status=terminal_status):
                card = _card("gated-card", terminal_status, ["prereq-open"])
                self.assertIsNone(
                    engine._unclosed_prerequisite_notice(card, self.by_title)
                )

    def test_active_card_still_gets_the_notice(self) -> None:
        # Pins the slice choice: the renderers' `queue_only=True` form
        # suppresses `active` cards ("you may start" has no audience once
        # claimed), which is exactly the wrong gate here — an active card's
        # decision is one somebody is about to act on.
        card = _card("gated-card", "active", ["prereq-open"])
        notice = engine._unclosed_prerequisite_notice(card, self.by_title)
        self.assertIsNotNone(notice)
        self.assertIn("prereq-open", notice)

    def test_notice_is_derived_from_the_shared_advisory_helper(self) -> None:
        # Derivation, not reimplementation: whatever `dependency_advisory`
        # reports as blockers is exactly what the notice names.
        card = _card("gated-card", "open", ["prereq-open"])
        for status in ["open", "active", *sorted(engine.TERMINAL_STATUSES)]:
            with self.subTest(prereq_status=status):
                by_title = {"prereq-open": _card("prereq-open", status, [])}
                blockers, _ = engine.dependency_advisory(card, by_title)
                notice = engine._unclosed_prerequisite_notice(card, by_title)
                self.assertEqual(bool(blockers), notice is not None)


class DecideSurfacesUnclosedPrerequisitesTest(unittest.TestCase):
    """End-to-end through the real CLI."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True, exist_ok=True)
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

    def assert_goc_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
        )

    def card_readme(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title / "README.md"

    def make_deck(
        self, cwd: Path, *, prereq_status: str = "open", wire_edge: bool = True
    ) -> None:
        self.assert_goc_ok(self.run_goc(cwd, "new", "prereq-card", "--tag", "story"))
        new_args = ["new", "gated-card", "--gate", "decision", "--tag", "story"]
        if wire_edge:
            new_args += ["--advanced-by", "prereq-card"]
        self.assert_goc_ok(self.run_goc(cwd, *new_args))
        if prereq_status != "open":
            readme = self.card_readme(cwd, "prereq-card")
            readme.write_text(
                readme.read_text().replace(
                    "status: open", f"status: {prereq_status}", 1
                )
            )

    def decide(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        return self.run_goc(
            cwd,
            "decide",
            "gated-card",
            "--decision",
            "go with A",
            "--because",
            "it is cheaper",
            "--no-commit",
        )

    def test_open_prerequisite_is_named_before_the_gate_flip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.make_deck(cwd)
            result = self.decide(cwd)
            self.assert_goc_ok(result)
            out = result.stdout + result.stderr
            self.assertIn("prereq-card", out)
            self.assertIn("unclosed prerequisite", out)
            # Ordering: the advisory precedes the gate-flip report. Both
            # streams are merged for the human, so compare within the union.
            lines = (result.stderr + result.stdout).splitlines()
            advisory_at = next(
                i for i, ln in enumerate(lines) if "unclosed prerequisite" in ln
            )
            flip_at = next(
                i for i, ln in enumerate(lines) if "decision recorded; gate" in ln
            )
            self.assertLess(advisory_at, flip_at)

    def test_advisory_is_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.make_deck(cwd)
            result = self.decide(cwd)
            # Exit code unchanged, gate really lowered, decision really recorded.
            self.assertEqual(result.returncode, 0)
            self.assertIn("gate decision → none", result.stdout)
            readme = self.card_readme(cwd, "gated-card").read_text()
            self.assertIn("human_gate: none", readme)
            self.assertIn("## Decision", readme)
            log = (
                cwd / ".game-of-cards" / "deck" / "gated-card" / "log.md"
            ).read_text()
            self.assertIn("decision recorded", log)

    def test_no_advisory_when_every_prerequisite_is_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.make_deck(cwd, prereq_status="done")
            result = self.decide(cwd)
            self.assert_goc_ok(result)
            out = result.stdout + result.stderr
            self.assertNotIn("unclosed prerequisite", out)
            self.assertIn("gate decision → none", result.stdout)

    def test_no_advisory_when_card_has_no_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.make_deck(cwd, wire_edge=False)
            result = self.decide(cwd)
            self.assert_goc_ok(result)
            out = result.stdout + result.stderr
            self.assertNotIn("unclosed prerequisite", out)
            self.assertNotIn("prereq-card", out)
            self.assertIn("gate decision → none", result.stdout)


if __name__ == "__main__":
    unittest.main()
