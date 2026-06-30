from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TriageHidesDraftScaffoldsTest(unittest.TestCase):
    """`goc triage` must hide unauthored draft scaffolds, exactly as the
    canonical `filter_cards` path (queue / --status / board / json) does.
    A `goc new <title> --gate decision` card is open + gated + draft; it
    has no authored scope to decide on and must not surface in the
    "Waiting on you" view."""

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

    def write_card(self, cwd: Path, title: str, *, draft: bool) -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        draft_line = "draft: true\n" if draft else ""
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: decision\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            f"{draft_line}"
            "definition_of_done: |\n"
            "  - [ ] decide\n"
            "---\n\n"
            f"# {title}\n\n"
            "## Decision required\n\n"
            "Pick A or B.\n"
        )
        (card_dir / "log.md").write_text("")

    def test_triage_text_omits_draft_keeps_authored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "authored-parked-card", draft=False)
            self.write_card(cwd, "draft-scaffold-card", draft=True)

            result = self.run_goc(cwd, "--no-color", "triage")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("authored-parked-card", result.stdout)
            self.assertNotIn("draft-scaffold-card", result.stdout)

    def test_triage_json_omits_draft_keeps_authored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "authored-parked-card", draft=False)
            self.write_card(cwd, "draft-scaffold-card", draft=True)

            result = self.run_goc(cwd, "--no-color", "triage", "--json")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            titles = {entry["title"] for entry in json.loads(result.stdout)}
            self.assertIn("authored-parked-card", titles)
            self.assertNotIn("draft-scaffold-card", titles)


if __name__ == "__main__":
    unittest.main()
