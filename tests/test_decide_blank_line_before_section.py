from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReplaceOrAppendDecisionTest(unittest.TestCase):
    """`replace_or_append_decision` must leave a blank line between the new
    `## Decision` block and any following `## ` heading, in both the replace
    branch (existing `## Decision required` section) and the append branch."""

    def test_replace_branch_preserves_blank_line_before_next_section(self) -> None:
        from goc.engine import replace_or_append_decision

        body = (
            "Pre-content.\n"
            "\n"
            "## Decision required\n"
            "\n"
            "What should we do?\n"
            "\n"
            "## Notes\n"
            "\n"
            "Some appendix material.\n"
        )
        result = replace_or_append_decision(body, "Pick A", "Simpler", "2026-05-29")
        lines = result.splitlines()
        reasoning_idx = next(
            i for i, line in enumerate(lines) if line.startswith("*Reasoning:*")
        )
        self.assertEqual(
            lines[reasoning_idx + 1],
            "",
            msg=f"expected blank line after *Reasoning:* but got {lines[reasoning_idx + 1]!r}\n"
            f"full output:\n{result}",
        )
        self.assertEqual(lines[reasoning_idx + 2], "## Notes")

    def test_replace_branch_as_last_section_no_double_trailing_blank(self) -> None:
        from goc.engine import replace_or_append_decision

        body = (
            "Pre-content.\n"
            "\n"
            "## Decision required\n"
            "\n"
            "What should we do?\n"
        )
        result = replace_or_append_decision(body, "Pick A", "Simpler", "2026-05-29")
        self.assertFalse(
            result.endswith("\n\n\n"),
            msg=f"unexpected triple-newline tail: {result!r}",
        )
        self.assertTrue(result.endswith("\n"))

    def test_append_branch_unchanged_no_double_blank(self) -> None:
        from goc.engine import replace_or_append_decision

        body = "Some pre-content.\n\nNo decision section yet.\n"
        result = replace_or_append_decision(body, "Pick B", "Faster", "2026-05-29")
        self.assertIn("## Decision\n", result)
        self.assertNotIn("\n\n\n\n", result)
        self.assertTrue(result.endswith("\n"))


class DecideBlankLineEndToEndTest(unittest.TestCase):
    """End-to-end: `goc decide` on a card whose body contains `## Decision
    required` followed by `## Notes` must produce markdown with the new
    `## Decision` block visually separated from `## Notes` by a blank line."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "new":
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

    def card_dir(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title

    def test_decide_separates_decision_block_from_next_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "card-with-following-section"
            self.assert_goc_ok(
                self.run_goc(cwd, "new", title, "--gate", "decision", "--tag", "story")
            )
            readme = self.card_dir(cwd, title) / "README.md"
            text = readme.read_text()
            body_tail = (
                "## Decision required\n"
                "\n"
                "What should we do?\n"
                "\n"
                "## Notes\n"
                "\n"
                "Some appendix material.\n"
            )
            readme.write_text(text.rstrip("\n") + "\n\n" + body_tail)

            self.assert_goc_ok(
                self.run_goc(
                    cwd,
                    "decide",
                    title,
                    "--decision",
                    "Pick A",
                    "--because",
                    "Simpler",
                )
            )

            new_text = readme.read_text()
            lines = new_text.splitlines()
            reasoning_idx = next(
                i for i, line in enumerate(lines) if line.startswith("*Reasoning:*")
            )
            self.assertEqual(
                lines[reasoning_idx + 1],
                "",
                msg=f"missing blank line after *Reasoning:*; full README:\n{new_text}",
            )
            self.assertEqual(lines[reasoning_idx + 2], "## Notes")

            # Basic markdown-rendering sanity: a CommonMark-style heading needs
            # a preceding blank line. We assert the textual property directly
            # without pulling in a renderer dependency: every `## ` heading
            # other than one at byte-0 should be preceded by a blank line.
            for i, line in enumerate(lines):
                if i == 0 or not line.startswith("## "):
                    continue
                self.assertEqual(
                    lines[i - 1],
                    "",
                    msg=f"heading {line!r} at line {i + 1} not preceded by blank line\n"
                    f"full README:\n{new_text}",
                )


if __name__ == "__main__":
    unittest.main()
