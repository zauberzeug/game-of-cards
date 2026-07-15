"""Regression: draft-state guard + lifecycle for unauthored scaffolds.

Covers the placeholder-cards-superseded-before-they-are-authored fix:

- `goc new` stamps `draft: true` (B).
- `goc status {superseded,disproved}` refuses on a draft (A), and succeeds
  once the card is authored + published.
- `goc publish` clears the flag, but refuses on a pure scaffold.
- `goc status active` and `goc done` auto-clear the flag.
- `goc validate` rejects `draft: true` on a terminal card.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DraftGuardAndLifecycleTest(unittest.TestCase):
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

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode, 0, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )

    def readme(self, cwd: Path, title: str) -> str:
        return (cwd / ".game-of-cards" / "deck" / title / "README.md").read_text()

    def author(self, cwd: Path, title: str) -> None:
        """Replace both generated placeholders so the card is no longer a
        scaffold (DoD checked off, body written)."""
        path = cwd / ".game-of-cards" / "deck" / title / "README.md"
        text = path.read_text()
        text = text.replace(
            "- [ ] (replace with real criteria)", "- [x] MECHANICAL: real criterion met"
        )
        text = text.replace("(write the design doc here)", "Real authored body.")
        path.write_text(text)

    def test_new_stamps_draft_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.assertIn("\ndraft: true\n", self.readme(cwd, "card-a"))

    def test_superseded_refused_on_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.assert_ok(self.run_goc(cwd, "new", "card-b", "--gate", "none", "--tag", "story"))
            result = self.run_goc(cwd, "status", "card-a", "superseded", "--by", "card-b", "--no-commit")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("unauthored draft scaffold", result.stderr)
            # The card must NOT have been mutated.
            self.assertIn("status: open", self.readme(cwd, "card-a"))
            self.assertNotIn("superseded_by", self.readme(cwd, "card-a"))

    def test_disproved_refused_on_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            result = self.run_goc(cwd, "status", "card-a", "disproved", "--no-commit")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("unauthored draft scaffold", result.stderr)
            self.assertIn("status: open", self.readme(cwd, "card-a"))

    def test_publish_refuses_pure_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            result = self.run_goc(cwd, "publish", "card-a", "--no-commit")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("unauthored scaffold", result.stderr)
            self.assertIn("\ndraft: true\n", self.readme(cwd, "card-a"))

    def test_publish_clears_flag_on_authored_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.author(cwd, "card-a")
            self.assert_ok(self.run_goc(cwd, "publish", "card-a", "--no-commit"))
            self.assertNotIn("draft:", self.readme(cwd, "card-a"))

    def test_publish_noop_on_authored_non_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.author(cwd, "card-a")
            self.assert_ok(self.run_goc(cwd, "publish", "card-a", "--no-commit"))
            second = self.run_goc(cwd, "publish", "card-a", "--no-commit")
            self.assert_ok(second)
            self.assertIn("not a draft", second.stdout)

    def test_status_active_auto_clears_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.assert_ok(self.run_goc(cwd, "status", "card-a", "active", "--no-commit"))
            self.assertNotIn("draft:", self.readme(cwd, "card-a"))

    def test_done_auto_clears_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.author(cwd, "card-a")  # DoD checked so `done` is allowed
            self.assert_ok(self.run_goc(cwd, "done", "card-a"))
            readme = self.readme(cwd, "card-a")
            self.assertNotIn("draft:", readme)
            self.assertIn("status: done", readme)

    def test_superseded_allowed_after_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            self.assert_ok(self.run_goc(cwd, "new", "card-b", "--gate", "none", "--tag", "story"))
            self.author(cwd, "card-a")
            self.assert_ok(self.run_goc(cwd, "publish", "card-a", "--no-commit"))
            result = self.run_goc(cwd, "status", "card-a", "superseded", "--by", "card-b", "--no-commit")
            self.assert_ok(result)
            self.assertIn("superseded_by", self.readme(cwd, "card-a"))

    def test_validate_rejects_draft_true_on_terminal_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_ok(self.run_goc(cwd, "new", "card-a", "--gate", "none", "--tag", "story"))
            # Hand-corrupt: a terminal card that still carries draft: true.
            path = cwd / ".game-of-cards" / "deck" / "card-a" / "README.md"
            text = path.read_text().replace("status: open", "status: disproved")
            text = text.replace(
                "closed_at: null", 'closed_at: "2026-06-29T00:00:00Z"'
            )
            path.write_text(text)
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("draft", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
