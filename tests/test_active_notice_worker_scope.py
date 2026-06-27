from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ActiveNoticeWorkerScopeTest(unittest.TestCase):
    """The `ACTIVE:` heads-up banner must honor `--worker`, mirroring the
    board path. Regression for active-card-banner-ignores-worker-filter."""

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
        worker: str,
        *,
        contribution: str = "low",
        created: str = "2026-05-04",
        advances: tuple[str, ...] = (),
    ) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        closed_at = "2026-05-04" if status == "done" else "null"
        if advances:
            advances_block = "advances:\n" + "".join(f"- {a}\n" for a in advances)
        else:
            advances_block = "advances: []\n"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            f"contribution: {contribution}\n"
            f"created: {created}\n"
            f"closed_at: {closed_at}\n"
            "human_gate: none\n"
            f"{advances_block}"
            "advanced_by: []\n"
            "tags: [bug]\n"
            f"worker: {worker}\n"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def _banner(self, stdout: str) -> str:
        return next((ln for ln in stdout.splitlines() if ln.startswith("ACTIVE:")), "")

    def _make_deck(self, cwd: Path) -> None:
        self.write_card(cwd, "alice-active", "active", "alice")
        self.write_card(cwd, "bob-active", "active", "bob")
        self.write_card(cwd, "alice-open", "open", "alice")

    def test_worker_filter_scopes_active_banner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_deck(cwd)

            result = self.run_goc(cwd, "--worker", "alice")

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            banner = self._banner(result.stdout)
            self.assertIn("alice-active", banner)
            self.assertNotIn("bob-active", banner)

    def test_worker_banner_tiebreak_counts_full_deck_live_flow(self) -> None:
        """Regression: under --worker, the active banner's near-term-flow
        tiebreak must count live downstream cards the worker filter hides.

        alice has two equal-value active cards: a1 advances two live open
        cards owned by bob, a2 advances one and is older. a1 unblocks more
        live flow and must rank first — even though bob's downstream cards
        are absent from the worker-scoped subset handed to the banner."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd, "a1-active-two-live", "active", "alice",
                contribution="medium", created="2026-06-02",
                advances=("d1-open", "d2-open"),
            )
            self.write_card(
                cwd, "a2-active-one-live", "active", "alice",
                contribution="medium", created="2026-06-01",
                advances=("d1-open",),
            )
            self.write_card(
                cwd, "d1-open", "open", "bob", contribution="medium",
            )
            self.write_card(
                cwd, "d2-open", "open", "bob", contribution="medium",
            )

            result = self.run_goc(cwd, "--worker", "alice")

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            banner = self._banner(result.stdout)
            a1 = banner.find("a1-active-two-live")
            a2 = banner.find("a2-active-one-live")
            self.assertNotEqual(-1, a1, msg=banner)
            self.assertNotEqual(-1, a2, msg=banner)
            self.assertLess(
                a1, a2,
                msg=f"higher-live-flow card must rank first; banner: {banner!r}",
            )

    def test_unfiltered_banner_lists_all_active_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_deck(cwd)

            result = self.run_goc(cwd)

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            banner = self._banner(result.stdout)
            self.assertIn("alice-active", banner)
            self.assertIn("bob-active", banner)


if __name__ == "__main__":
    unittest.main()
