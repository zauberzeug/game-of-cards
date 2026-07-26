from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StageFilterTest(unittest.TestCase):
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

    def write_card(self, cwd: Path, title: str, stage: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            f"stage: {stage}\n"
            "contribution: medium\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_hyphenated_enum_value_is_addressable(self) -> None:
        from goc import engine

        enum = ["null", "pre-alpha", "alpha", "beta", "stable"]
        with unittest.mock.patch.object(engine, "STAGE_ORDER", enum):
            self.assertEqual(["pre-alpha"], engine.parse_stage_filter("pre-alpha"))

    def test_range_and_rejection_survive_exact_match_first(self) -> None:
        from goc import engine

        enum = ["null", "pre-alpha", "alpha", "beta", "stable"]
        with unittest.mock.patch.object(engine, "STAGE_ORDER", enum):
            self.assertEqual(
                ["alpha", "beta", "stable"], engine.parse_stage_filter("alpha-stable")
            )
            err = io.StringIO()
            with self.assertRaises(SystemExit) as caught, redirect_stderr(err):
                engine.parse_stage_filter("nope-alpha")
            self.assertEqual(2, caught.exception.code)
            self.assertIn("--stage", err.getvalue())

    def test_range_over_hyphenated_left_endpoint_is_spellable(self) -> None:
        from goc import engine

        enum = ["null", "pre-alpha", "alpha", "beta", "stable"]
        with unittest.mock.patch.object(engine, "STAGE_ORDER", enum):
            self.assertEqual(
                ["pre-alpha", "alpha", "beta", "stable"],
                engine.parse_stage_filter("pre-alpha-stable"),
            )
            self.assertEqual(
                ["null", "pre-alpha"], engine.parse_stage_filter("null-pre-alpha")
            )
            for spec in ("nope-alpha", "alpha-nope"):
                err = io.StringIO()
                with self.assertRaises(SystemExit) as caught, redirect_stderr(err):
                    engine.parse_stage_filter(spec)
                self.assertEqual(2, caught.exception.code, msg=spec)
                self.assertIn("expected one of", err.getvalue())

    def test_ambiguous_range_is_reported_not_guessed(self) -> None:
        from goc import engine

        # `alpha-beta-stable` reads as both `alpha`..`beta-stable` and
        # `alpha-beta`..`stable` over this enum.
        enum = ["null", "alpha", "beta", "alpha-beta", "beta-stable", "stable"]
        err = io.StringIO()
        with unittest.mock.patch.object(engine, "STAGE_ORDER", enum):
            with self.assertRaises(SystemExit) as caught, redirect_stderr(err):
                engine.parse_stage_filter("alpha-beta-stable")
        self.assertEqual(2, caught.exception.code)
        self.assertIn("ambiguous range", err.getvalue())
        self.assertIn("'alpha'..'beta-stable'", err.getvalue())
        self.assertIn("'alpha-beta'..'stable'", err.getvalue())

    def test_invalid_stage_range_rejects_unknown_stages_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "--stage", "foo-bar")

            combined = f"{result.stdout}\n{result.stderr}"
            self.assertEqual(2, result.returncode, msg=combined)
            self.assertIn("--stage", result.stderr)
            self.assertNotIn("Traceback", combined)
            self.assertNotIn("ValueError", combined)

    def test_valid_stage_values_and_ranges_still_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "alpha-card", "alpha")
            self.write_card(cwd, "beta-card", "beta")
            self.write_card(cwd, "stable-card", "stable")

            alpha = self.run_goc(cwd, "--stage", "alpha")
            reverse_range = self.run_goc(cwd, "--stage", "stable-alpha")

            self.assertEqual(0, alpha.returncode, msg=alpha.stderr)
            self.assertIn("alpha-card", alpha.stdout)
            self.assertNotIn("beta-card", alpha.stdout)
            self.assertEqual(0, reverse_range.returncode, msg=reverse_range.stderr)
            self.assertIn("alpha-card", reverse_range.stdout)
            self.assertIn("beta-card", reverse_range.stdout)
            self.assertIn("stable-card", reverse_range.stdout)


if __name__ == "__main__":
    unittest.main()
