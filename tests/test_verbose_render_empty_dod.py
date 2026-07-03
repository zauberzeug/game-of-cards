"""Regression: `goc -vv` must not crash on a card whose
`definition_of_done` frontmatter key is present but empty (parsed as
None). Before the fix, `render_table`'s verbose>=2 branch did
`fm.get("definition_of_done", "").splitlines()`, and the ""-default
only applies when the key is absent — an empty value yields None and
`None.splitlines()` raised AttributeError, blanking the whole -vv view.

Also covers a *truthy* non-string DoD (a YAML block list): the `or ""`
guard that fixed the None case is falsy-only, so a list value slips
through and `list.splitlines()` raises. The fix coerces with
`isinstance(..., str)`, matching `count_dod_boxes`/`untagged_dod_items`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VerboseRenderEmptyDodTest(unittest.TestCase):
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

    def write_empty_dod_card(self, cwd: Path, title: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            "created: 2026-06-03\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done:\n"  # empty value -> parses to None
            "---\n\n"
            f"# {title}\n"
        )

    def write_list_dod_card(self, cwd: Path, title: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            "created: 2026-06-03\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done:\n"  # block list -> parses to a Python list
            "  - a\n"
            "  - b\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_verbose_render_survives_empty_dod(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "empty-dod-card"
            self.write_empty_dod_card(cwd, title)

            result = self.run_goc(cwd, "-vv", "--no-color")

            self.assertEqual(
                result.returncode,
                0,
                msg=f"`goc -vv` crashed on empty DoD card:\n{result.stderr}",
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn(title, result.stdout)

    def test_verbose_render_survives_list_dod(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "list-dod-card"
            self.write_list_dod_card(cwd, title)

            result = self.run_goc(cwd, "-vv", "--no-color")

            self.assertEqual(
                result.returncode,
                0,
                msg=f"`goc -vv` crashed on list DoD card:\n{result.stderr}",
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn(title, result.stdout)


if __name__ == "__main__":
    unittest.main()
