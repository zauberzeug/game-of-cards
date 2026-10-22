"""Regression: the `--ready` leverage line's gated half shares the query's scope.

`goc --ready` ends with `Pulling <title> (value N). Highest gated card:
<title> (value M, gate <kind>).`. The "Pulling" half comes from the filtered
queue. The gated half used to come from the whole deck, so a runner scoped by
`GOC_WORKER` was told to ping a human about another worker's parked card.
That is a card it could never pull, and its own parked card went unnamed. The
gated half now answers the same query with only the gate conjunct inverted.

Each deck below holds an in-scope ready card, an in-scope gated card, and an
out-of-scope gated card that outranks it. A gated half that ignores a scope
flag names the out-of-scope card.

Regression for
ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LeverageLineQueryScopeTest(unittest.TestCase):
    def run_goc(
        self, cwd: Path, *args: str, goc_worker: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("GOC_WORKER", None)
        if goc_worker is not None:
            env["GOC_WORKER"] = goc_worker
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
        gate: str = "none",
        contribution: str = "low",
        worker: str = "",
        tags: tuple[str, ...] = ("bug",),
        stage: str = "null",
        created: str = "2026-05-04",
        advances: tuple[str, ...] = (),
        advanced_by: tuple[str, ...] = (),
    ) -> None:
        def edge_block(field: str, targets: tuple[str, ...]) -> str:
            if not targets:
                return f"{field}: []\n"
            return f"{field}:\n" + "".join(f"- {t}\n" for t in targets)

        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            f"stage: {stage}\n"
            f"contribution: {contribution}\n"
            f"created: {created}\n"
            "closed_at: null\n"
            f"human_gate: {gate}\n"
            f"{edge_block('advances', advances)}"
            f"{edge_block('advanced_by', advanced_by)}"
            f"tags: [{', '.join(tags)}]\n"
            + (f"worker: {worker}\n" if worker else "")
            + "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def leverage_line(self, cwd: Path, *args: str, goc_worker: str | None = None) -> str:
        result = self.run_goc(cwd, "--ready", "--no-color", *args, goc_worker=goc_worker)
        self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
        return next(
            (ln for ln in result.stdout.splitlines() if ln.startswith("Pulling ")), ""
        )

    def assert_gated_half(self, line: str, expected: str) -> None:
        self.assertTrue(line.startswith("Pulling in-ready "), msg=line)
        gated = line.partition("Highest gated card: ")[2]
        self.assertTrue(gated.startswith(f"{expected} "), msg=line)

    def test_worker_flag_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready", worker="alice")
            self.write_card(cwd, "in-parked", gate="decision", contribution="medium", worker="alice")
            self.write_card(cwd, "out-parked", gate="decision", contribution="high", worker="bob")

            self.assert_gated_half(self.leverage_line(cwd, "--worker", "alice"), "in-parked")

    def test_goc_worker_env_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready", worker="alice")
            self.write_card(cwd, "in-parked", gate="decision", contribution="medium", worker="alice")
            self.write_card(cwd, "out-parked", gate="decision", contribution="high", worker="bob")
            self.write_card(cwd, "bob-ready", worker="bob")

            self.assert_gated_half(self.leverage_line(cwd, goc_worker="alice"), "in-parked")

    def test_tag_flag_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready", tags=("documentation",))
            self.write_card(
                cwd, "in-parked", gate="decision", contribution="medium",
                tags=("documentation",),
            )
            self.write_card(cwd, "out-parked", gate="decision", contribution="high", tags=("infra",))

            self.assert_gated_half(
                self.leverage_line(cwd, "--tag", "documentation"), "in-parked"
            )

    def test_contribution_flag_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready")
            self.write_card(cwd, "in-parked", gate="decision")
            self.write_card(cwd, "out-parked", gate="decision", contribution="high")

            self.assert_gated_half(
                self.leverage_line(cwd, "--contribution", "low"), "in-parked"
            )

    def test_stage_flag_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready", stage="alpha")
            self.write_card(cwd, "in-parked", gate="decision", contribution="medium", stage="alpha")
            self.write_card(cwd, "out-parked", gate="decision", contribution="high", stage="beta")

            self.assert_gated_half(self.leverage_line(cwd, "--stage", "alpha"), "in-parked")

    def test_advances_flag_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "epic", advanced_by=("in-ready", "in-parked"))
            self.write_card(cwd, "in-ready", advances=("epic",))
            self.write_card(
                cwd, "in-parked", gate="decision", contribution="medium", advances=("epic",)
            )
            self.write_card(cwd, "out-parked", gate="decision", contribution="high")

            self.assert_gated_half(self.leverage_line(cwd, "--advances", "epic"), "in-parked")

    def test_advanced_by_flag_scopes_the_gated_half(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "root", advances=("in-ready", "in-parked"))
            self.write_card(cwd, "in-ready", advanced_by=("root",))
            self.write_card(
                cwd, "in-parked", gate="decision", contribution="medium", advanced_by=("root",)
            )
            self.write_card(cwd, "out-parked", gate="decision", contribution="high")

            self.assert_gated_half(
                self.leverage_line(cwd, "--advanced-by", "root"), "in-parked"
            )

    def test_unscoped_query_compares_against_the_whole_deck(self) -> None:
        # No scope flag: every gated card is in scope, so the deck-wide highest
        # is named, exactly as before the fix.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready", worker="alice")
            self.write_card(cwd, "in-parked", gate="decision", contribution="medium", worker="alice")
            self.write_card(cwd, "out-parked", gate="decision", contribution="high", worker="bob")

            self.assert_gated_half(self.leverage_line(cwd), "out-parked")

    def test_human_gate_flag_does_not_empty_the_gated_half(self) -> None:
        # The gate is the one conjunct the two halves differ on, so the gate
        # filter of the query must not reach the gated half. `--human-gate
        # none` is redundant with `--ready`; it must not silence the line.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready")
            self.write_card(cwd, "in-parked", gate="session", contribution="medium")

            self.assert_gated_half(
                self.leverage_line(cwd, "--human-gate", "none"), "in-parked"
            )

    def test_scope_without_gated_cards_omits_the_line(self) -> None:
        # carol has nothing parked, so there is nothing to compare her pick
        # against. bob's parked card must not stand in for one.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "carol-ready", worker="carol")
            self.write_card(cwd, "out-parked", gate="decision", contribution="high", worker="bob")

            self.assertEqual("", self.leverage_line(cwd, goc_worker="carol"))

    def test_worker_scoped_tiebreak_counts_full_deck_live_flow(self) -> None:
        # alice has two equal-value gated cards. g1 advances two live cards
        # owned by bob and g2 advances one, but g2 is older. g1 unblocks more
        # flow and must win the tiebreak, even though bob's downstream cards
        # are outside the worker scope the gated half is drawn from.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "in-ready", worker="alice")
            self.write_card(
                cwd, "g1-parked-two-live", gate="decision", contribution="medium",
                worker="alice", created="2026-06-02", advances=("d1-open", "d2-open"),
            )
            self.write_card(
                cwd, "g2-parked-one-live", gate="decision", contribution="medium",
                worker="alice", created="2026-06-01", advances=("d1-open",),
            )
            self.write_card(
                cwd, "d1-open", contribution="medium", worker="bob",
                advanced_by=("g1-parked-two-live", "g2-parked-one-live"),
            )
            self.write_card(
                cwd, "d2-open", contribution="medium", worker="bob",
                advanced_by=("g1-parked-two-live",),
            )

            self.assert_gated_half(
                self.leverage_line(cwd, "--worker", "alice"), "g1-parked-two-live"
            )


if __name__ == "__main__":
    unittest.main()
