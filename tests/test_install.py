from __future__ import annotations

import json
import os
import re
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
            self.assertIn("shared write  .game-of-cards/config.yaml", default.stdout)

    def test_install_help_describes_auto_detected_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--help")

            self.assert_goc_ok(result)
            self.assertIn("auto-detect Claude/Codex project markers", result.stdout)
            self.assertIn("no marker defaults", result.stdout)
            self.assertIn("to claude", result.stdout)

    def test_install_auto_detects_claude_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "CLAUDE.md").write_text("# Existing Claude guidance\n")

            result = self.run_goc(cwd, "install", "--dry-run")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("agents: claude", planned)
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", planned)
            self.assertNotIn(".codex/", planned)

    def test_install_auto_detects_codex_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "AGENTS.md").write_text("# Existing agent guidance\n")

            result = self.run_goc(cwd, "install", "--dry-run")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("agents: codex", planned)
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", planned)
            self.assertNotIn(".claude/", planned)

    def test_install_auto_detects_both_markers_and_explicit_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "CLAUDE.md").write_text("# Existing Claude guidance\n")
            (cwd / ".codex").mkdir()

            detected = self.run_goc(cwd, "install", "--dry-run")
            explicit = self.run_goc(cwd, "install", "--dry-run", "--agents", "codex")

            self.assert_goc_ok(detected)
            self.assert_goc_ok(explicit)
            self.assertIn("agents: claude,codex", detected.stdout)
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", detected.stdout)
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", detected.stdout)
            self.assertIn("agents: codex", explicit.stdout)
            self.assertNotIn(".claude/", explicit.stdout)

    def test_no_marker_install_output_leads_with_llm_prompt_and_defaults_to_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install")

            self.assert_goc_ok(result)
            self.assertIn("goc 0.0.3 installed for agents: claude (default).", result.stdout)
            self.assertIn('Next: ask your LLM agent: "create a card for the next change I want to make."', result.stdout)
            self.assertIn("Engine/debug: `goc` shows the queue; `goc validate` checks cards.", result.stdout)
            self.assertTrue((cwd / ".claude" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertFalse((cwd / ".codex").exists())

    def test_claude_dry_run_lists_only_claude_harness_and_shared_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--agents", "claude")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("shared write  deck/.goc-version", planned)
            self.assertIn("shared append AGENTS.md", planned)
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", planned)
            self.assertIn("claude write  .claude/skills/_goc-bootstrap.sh", planned)
            self.assertIn("claude write  .claude/hooks/user-prompt-submit-goc.py", planned)
            self.assertIn("claude append CLAUDE.md", planned)
            self.assertNotIn(".codex/", planned)

    def test_v1_agent_manifests_register_claude_and_codex_shims(self) -> None:
        agents_root = ROOT / "goc" / "templates" / "agents"
        claude = json.loads((agents_root / "claude" / "manifest.json").read_text())
        codex = json.loads((agents_root / "codex" / "manifest.json").read_text())

        self.assertEqual(".claude/skills", claude["skills"]["target"])
        self.assertEqual("native", claude["skills"]["frontmatter"])
        self.assertEqual(".codex/skills", codex["skills"]["target"])
        self.assertEqual("codex", codex["skills"]["frontmatter"])
        self.assertIn(".claude/skills/_goc-bootstrap.sh", [file["target"] for file in claude["files"]])
        self.assertIn(".claude/hooks/user-prompt-submit-goc.py", [file["target"] for file in claude["files"]])

    def test_multi_agent_dry_run_lists_both_registered_harnesses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--agents", "claude,codex")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("agents: claude,codex", planned)
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", planned)
            self.assertIn("claude write  .claude/hooks/user-prompt-submit-goc.py", planned)
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", planned)
            self.assertNotIn("openclaw", planned.lower())

    def test_claude_install_smoke_creates_valid_deck_and_matching_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            install = self.run_goc(cwd, "install", "--agents", "claude")
            self.assert_goc_ok(install)
            self.assertIn('Next: ask your LLM agent: "create a card for the next change I want to make."', install.stdout)
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

    def test_codex_install_smoke_generates_codex_frontmatter_without_claude_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            install = self.run_goc(cwd, "install", "--agents", "codex")
            self.assert_goc_ok(install)
            self.assertIn('Next: ask your LLM agent: "create a card for the next change I want to make."', install.stdout)
            self.assertFalse((cwd / ".claude").exists())
            self.assertTrue(os.access(cwd / ".codex" / "skills" / "_goc-bootstrap.sh", os.X_OK))
            self.assertTrue((cwd / ".codex" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertFalse((cwd / "CLAUDE.md").exists())

            codex_skill = (cwd / ".codex" / "skills" / "pull-card" / "SKILL.md").read_text()
            self.assertIn("name: pull-card", codex_skill)
            self.assertIn("description: ", codex_skill)
            self.assertIn("# Pull a card", codex_skill)
            self.assertIn(".codex/skills/_goc-bootstrap.sh", codex_skill)

            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_install_writes_runtime_neutral_config_and_attest_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude"))
            config = cwd / ".game-of-cards" / "config.yaml"
            self.assertTrue(config.is_file())
            config.write_text(
                "layer_2_project_dod: []\n"
                "layer_3_goc_dod:\n"
                "  - name: dod-100-percent\n"
                "    kind: derived\n"
            )
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            readme = cwd / "deck" / "smoke-card" / "README.md"
            readme.write_text(readme.read_text().replace("- [ ] (replace with real criteria)", "- [x] closure ok"))

            attest = self.run_goc(cwd, "attest", "smoke-card", "--non-interactive")

            self.assert_goc_ok(attest)
            self.assertIn("Layer-3 (GoC) checks", attest.stdout)
            self.assertIn("dod-100-percent", (cwd / "deck" / "smoke-card" / "log.md").read_text())

    def test_upgrade_migrates_legacy_deck_config_without_clobbering_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude"))
            config = cwd / ".game-of-cards" / "config.yaml"
            legacy = cwd / ".claude" / "deck-config.yaml"
            config.unlink()
            legacy.write_text("layer_3_goc_dod:\n  - name: legacy-check\n    kind: derived\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--agents", "claude"))

            self.assertIn("legacy-check", config.read_text())

            config.write_text("layer_3_goc_dod:\n  - name: existing-check\n    kind: derived\n")
            legacy.write_text("layer_3_goc_dod:\n  - name: legacy-new\n    kind: derived\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--agents", "claude"))

            self.assertIn("existing-check", config.read_text())
            self.assertNotIn("legacy-new", config.read_text())

    def test_state_mutations_respect_auto_commit_config_and_cli_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=cwd, check=True)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude"))
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "commit-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            subprocess.run(["git", "add", "."], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=cwd, check=True, capture_output=True)

            committed = self.run_goc(cwd, "status", "commit-card", "active")
            self.assert_goc_ok(committed)
            self.assertIn("committed", committed.stdout)
            self.assertEqual("", subprocess.run(["git", "status", "--short"], cwd=cwd, text=True, capture_output=True).stdout)

            skipped = self.run_goc(cwd, "status", "commit-card", "open", "--no-commit")
            self.assert_goc_ok(skipped)
            self.assertNotIn("committed", skipped.stdout)
            self.assertIn(
                " M deck/commit-card/README.md",
                subprocess.run(["git", "status", "--short"], cwd=cwd, text=True, capture_output=True).stdout,
            )

            subprocess.run(["git", "add", "deck/commit-card/README.md"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "manual open"], cwd=cwd, check=True, capture_output=True)
            self.assertEqual("", subprocess.run(["git", "status", "--short"], cwd=cwd, text=True, capture_output=True).stdout)

            (cwd / ".game-of-cards" / "config.yaml").write_text(
                "layer_2_project_dod: []\n"
                "layer_3_goc_dod: []\n"
                "workflow:\n"
                "  auto_commit: false\n"
            )
            subprocess.run(["git", "add", ".game-of-cards/config.yaml"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "disable auto commit"], cwd=cwd, check=True, capture_output=True)

            disabled = self.run_goc(cwd, "status", "commit-card", "active")
            self.assert_goc_ok(disabled)
            self.assertNotIn("committed", disabled.stdout)
            self.assertIn(
                " M deck/commit-card/README.md",
                subprocess.run(["git", "status", "--short"], cwd=cwd, text=True, capture_output=True).stdout,
            )

            forced_again = self.run_goc(cwd, "status", "commit-card", "blocked", "--commit")
            self.assert_goc_ok(forced_again)
            self.assertIn("committed", forced_again.stdout)
            self.assertEqual("", subprocess.run(["git", "status", "--short"], cwd=cwd, text=True, capture_output=True).stdout)

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

    def test_bootstrap_wrapper_reports_missing_and_old_cli_and_execs_current_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude"))
            wrapper = cwd / ".claude" / "skills" / "_goc-bootstrap.sh"
            self.assertTrue(os.access(wrapper, os.X_OK))

            missing_env = os.environ.copy()
            missing_env["PATH"] = ""
            missing = subprocess.run(
                [str(wrapper), "new", "anything"],
                cwd=cwd,
                env=missing_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(127, missing.returncode)
            self.assertEqual("", missing.stdout)
            self.assertEqual(
                "Game of Cards CLI not found. Install with: pipx install game-of-cards\n",
                missing.stderr,
            )

            bin_dir = cwd / "bin"
            bin_dir.mkdir()
            fake_goc = bin_dir / "goc"
            fake_goc.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = "--version" ]; then echo "goc, version 0.0.1"; exit 0; fi\n'
                'echo "old goc should not run"\n'
            )
            fake_goc.chmod(0o755)
            fake_env = os.environ.copy()
            fake_env["PATH"] = f"{bin_dir}:/usr/bin:/bin"

            old = subprocess.run(
                [str(wrapper), "new", "anything"],
                cwd=cwd,
                env=fake_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, old.returncode)
            self.assertEqual("", old.stdout)
            self.assertEqual(
                "Game of Cards CLI is older than this repo's schema "
                "(installed: 0.0.1, required: 0.0.3). Run: pipx upgrade game-of-cards\n",
                old.stderr,
            )

            fake_goc.write_text(
                '#!/bin/sh\n'
                'if [ "$1" = "--version" ]; then echo "goc, version 0.0.3"; exit 0; fi\n'
                'printf "fake:%s\\n" "$*"\n'
            )
            fake_goc.chmod(0o755)
            current = subprocess.run(
                [str(wrapper), "show", "smoke-card"],
                cwd=cwd,
                env=fake_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, current.returncode)
            self.assertEqual("fake:show smoke-card\n", current.stdout)
            self.assertEqual("", current.stderr)

    def test_skill_command_injections_use_bootstrap_wrapper(self) -> None:
        roots = [
            ROOT / "goc" / "templates" / "skills",
            ROOT / ".claude" / "skills",
            ROOT / ".codex" / "skills",
        ]
        for root in roots:
            for skill_name in SKILL_NAMES:
                skill = root / skill_name / "SKILL.md"
                text = skill.read_text()
                self.assertIsNone(re.search(r"^!`goc\b", text, flags=re.MULTILINE), msg=str(skill))

    def test_move_renames_without_redirect_and_rewrites_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "new", "child-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "advance", "child-card", "--by", "parent-card", "--no-commit"))

            move_result = self.run_goc(cwd, "move", "child-card", "renamed-card")

            self.assert_goc_ok(move_result)
            self.assertFalse((cwd / "deck" / "child-card").exists())
            self.assertTrue((cwd / "deck" / "renamed-card" / "README.md").is_file())
            parent_readme = (cwd / "deck" / "parent-card" / "README.md").read_text()
            renamed_readme = (cwd / "deck" / "renamed-card" / "README.md").read_text()
            self.assertIn("advances: [renamed-card]", parent_readme)
            self.assertNotIn("child-card", parent_readme)
            self.assertIn("title: renamed-card", renamed_readme)
            self.assertFalse((cwd / "deck" / "child-card" / "REDIRECT.md").exists())
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

            help_result = self.run_goc(cwd, "move", "--help")
            self.assert_goc_ok(help_result)
            self.assertNotIn("REDIRECT", help_result.stdout)
            self.assertNotIn("redirect", help_result.stdout.lower())

    def test_validate_rejects_redirect_only_dirs_missing_readmes_and_stale_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "new", "source-card", "--gate", "none", "--tag", "story"))
            readme = cwd / "deck" / "source-card" / "README.md"
            readme.write_text(readme.read_text().replace("advances: []", "advances: [missing-card]"))
            redirect_dir = cwd / "deck" / "old-card"
            redirect_dir.mkdir()
            (redirect_dir / "REDIRECT.md").write_text("Moved to elsewhere.\n")
            stale_dir = cwd / "deck" / "stale-card"
            stale_dir.mkdir()
            (stale_dir / "notes.md").write_text("not a card\n")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertNotEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("old-card: stale card directory contains REDIRECT.md but no README.md", result.stderr)
            self.assertIn("stale-card: card directory missing README.md", result.stderr)
            self.assertIn("source-card: advances: references unknown title 'missing-card'", result.stderr)

    def test_board_and_open_queue_surface_active_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "new", "open-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "new", "active-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "status", "active-card", "active", "--no-commit"))

            board = self.run_goc(cwd, "--board", "--no-color")
            active = self.run_goc(cwd, "--status", "active", "--no-color")
            default_queue = self.run_goc(cwd, "--no-color")
            open_queue = self.run_goc(cwd, "--status", "open", "--no-color")
            full_deck = self.run_goc(cwd, "--status", "all", "--no-color")

            self.assert_goc_ok(board)
            self.assert_goc_ok(active)
            self.assert_goc_ok(default_queue)
            self.assert_goc_ok(open_queue)
            self.assert_goc_ok(full_deck)

            self.assertIn("ACTIVE", board.stdout)
            self.assertIn("active-card", board.stdout)
            self.assertIn("open-card", board.stdout)
            self.assertIn("active-card", active.stdout)
            self.assertIn("ACTIVE: 1 claimed card outside this open queue: active-card.", default_queue.stdout)
            self.assertIn("open-card", default_queue.stdout)
            self.assertIn("ACTIVE: 1 claimed card outside this open queue: active-card.", open_queue.stdout)
            self.assertIn("active-card", full_deck.stdout)
            self.assertIn("open-card", full_deck.stdout)
            self.assertIn("active", full_deck.stdout)


if __name__ == "__main__":
    unittest.main()
