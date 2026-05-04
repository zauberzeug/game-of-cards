from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAMES = (
    "advance-card",
    "card-schema",
    "create-card",
    "decide-card",
    "deck",
    "extend-deck",
    "finish-card",
    "improve-deck",
    "next-card",
    "pull-card",
    "scan-deck",
)


class ClaudeHarnessInstallTest(unittest.TestCase):
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

    def assert_goc_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
        )

    def test_no_flag_install_default_matches_explicit_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            default = self.run_goc(cwd, "install", "--dry-run")
            explicit = self.run_goc(cwd, "install", "--dry-run", "--agents", "claude")

            self.assert_goc_ok(default)
            self.assert_goc_ok(explicit)
            self.assertEqual(default.stdout, explicit.stdout)
            self.assertIn("agents: claude", default.stdout)

    def test_claude_dry_run_lists_only_claude_harness_and_shared_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--agents", "claude")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("shared write  deck/.goc-version", planned)
            self.assertIn("shared append AGENTS.md", planned)
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", planned)
            self.assertIn("claude write  .claude/hooks/user-prompt-submit-goc.py", planned)
            self.assertIn("claude append CLAUDE.md", planned)
            self.assertNotIn(".codex/", planned)

    def test_claude_install_smoke_creates_valid_deck_and_matching_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude"))
            self.assertFalse((cwd / ".codex").exists())
            self.assertTrue((cwd / ".claude" / "hooks" / "user-prompt-submit-goc.py").is_file())
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertTrue((cwd / "CLAUDE.md").is_file())

            claude_text = (cwd / "CLAUDE.md").read_text()
            for skill_name in SKILL_NAMES:
                self.assertTrue((cwd / ".claude" / "skills" / skill_name / "SKILL.md").is_file())
                self.assertIn(f"Skill({skill_name})", claude_text)

            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_upgrade_claude_does_not_clobber_cards_or_non_claude_harness_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude,codex"))
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )

            claude_skill = cwd / ".claude" / "skills" / "pull-card" / "SKILL.md"
            codex_skill = cwd / ".codex" / "skills" / "pull-card" / "SKILL.md"
            claude_skill.write_text("stale claude skill\n")
            codex_skill.write_text("custom codex skill\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--agents", "claude"))

            self.assertIn("# Pull a card", claude_skill.read_text())
            self.assertEqual("custom codex skill\n", codex_skill.read_text())
            self.assertTrue((cwd / "deck" / "smoke-card" / "README.md").is_file())
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))


if __name__ == "__main__":
    unittest.main()
