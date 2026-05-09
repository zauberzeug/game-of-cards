from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAMES = tuple(
    sorted(p.name for p in (ROOT / "goc" / "templates" / "skills").iterdir() if (p / "SKILL.md").is_file())
)


class ClaudeHarnessInstallTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
        base_env = os.environ.copy()
        pythonpath = base_env.get("PYTHONPATH")
        base_env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        if env:
            base_env.update(env)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=base_env,
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

    # ── Default install (plugin path) ─────────────────────────────────────────

    def test_no_flag_install_defaults_to_claude_plugin_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run")

            self.assert_goc_ok(result)
            self.assertIn("agents: claude", result.stdout)
            self.assertNotIn(".claude/skills/", result.stdout)
            self.assertNotIn(".claude/hooks/", result.stdout)
            self.assertNotIn("settings.json", result.stdout)
            self.assertIn("shared write  .game-of-cards/config.yaml", result.stdout)
            self.assertIn("claude append CLAUDE.md", result.stdout)

    def test_default_install_creates_project_state_and_guidance_but_no_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install")

            self.assert_goc_ok(result)
            self.assertIn(f"goc {self._goc_version()} installed for agents: claude (default).", result.stdout)
            self.assertTrue((cwd / ".game-of-cards" / "deck" / ".goc-version").is_file())
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertTrue((cwd / "CLAUDE.md").is_file())
            self.assertFalse((cwd / ".claude" / "skills").exists())
            self.assertFalse((cwd / ".claude" / "hooks").exists())
            self.assertFalse((cwd / ".claude" / "settings.json").exists())
            self.assertFalse((cwd / ".codex").exists())

    def test_default_install_prints_plugin_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            # Ensure we're not inside Claude Code so we get the "next steps" variant
            env_without_claudecode = {k: v for k, v in os.environ.items()
                                      if k not in ("CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR")}
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "install"],
                cwd=cwd,
                env={**env_without_claudecode,
                     "PYTHONPATH": str(ROOT)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assert_goc_ok(result)
            self.assertIn("/plugin marketplace add zauberzeug/game-of-cards", result.stdout)
            self.assertIn("/plugin install game-of-cards@game-of-cards", result.stdout)

    def test_install_inside_claude_code_env_prints_agent_facing_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", env={"CLAUDECODE": "1"})

            self.assert_goc_ok(result)
            self.assertIn("GoC plugin", result.stdout)
            self.assertIn("/plugin marketplace add zauberzeug/game-of-cards", result.stdout)

    def test_install_help_describes_auto_detected_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--help")

            self.assert_goc_ok(result)
            self.assertIn("auto-detect Claude/Codex project markers", result.stdout)
            self.assertIn("defaults to claude", result.stdout)

    def test_install_help_documents_local_skills_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--help")

            self.assert_goc_ok(result)
            self.assertIn("--local-skills", result.stdout)

    def test_install_help_does_not_mention_no_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--help")

            self.assert_goc_ok(result)
            self.assertNotIn("--no-harness", result.stdout)

    # ── --local-skills (vendored layout, opt-in) ──────────────────────────────

    def test_local_skills_install_creates_skills_hooks_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--local-skills")

            self.assert_goc_ok(result)
            self.assertTrue((cwd / ".claude" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertTrue((cwd / ".claude" / "hooks" / "deck_prompt_router.py").is_file())
            self.assertTrue((cwd / ".claude" / "hooks" / "deck_session_start.py").is_file())
            self.assertTrue((cwd / ".claude" / "settings.json").is_file())
            self.assertFalse((cwd / ".codex").exists())

    def test_local_skills_dry_run_lists_all_three_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--local-skills")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("Project state:", planned)
            self.assertIn("Guidance:", planned)
            self.assertIn("Runtime affordances:", planned)
            state_pos = planned.index("Project state:")
            guidance_pos = planned.index("Guidance:")
            harness_pos = planned.index("Runtime affordances:")
            self.assertLess(state_pos, guidance_pos)
            self.assertLess(guidance_pos, harness_pos)
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", planned)
            self.assertIn("claude write  .claude/hooks/deck_prompt_router.py", planned)
            self.assertIn("claude merge  .claude/settings.json", planned)

    def test_local_skills_does_not_print_plugin_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--local-skills")

            self.assert_goc_ok(result)
            self.assertNotIn("/plugin marketplace add", result.stdout)

    def test_local_skills_smoke_creates_valid_deck_with_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            install = self.run_goc(cwd, "install", "--local-skills")
            self.assert_goc_ok(install)
            self.assertFalse((cwd / ".codex").exists())
            self.assertTrue((cwd / ".claude" / "hooks" / "deck_prompt_router.py").is_file())
            self.assertTrue((cwd / ".claude" / "hooks" / "deck_session_start.py").is_file())
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

    # ── --agents codex (vendored, unchanged) ──────────────────────────────────

    def test_codex_install_smoke_generates_codex_frontmatter_without_claude_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            install = self.run_goc(cwd, "install", "--agents", "codex")
            self.assert_goc_ok(install)
            self.assertIn(
                'Next: ask your LLM agent to "expand the deck" — it audits the repo and files initial cards.',
                install.stdout,
            )
            self.assertFalse((cwd / ".claude").exists())
            self.assertTrue(os.access(cwd / ".codex" / "skills" / "_goc-bootstrap.sh", os.X_OK))
            self.assertTrue((cwd / ".codex" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertFalse((cwd / "CLAUDE.md").exists())

            codex_skill = (cwd / ".codex" / "skills" / "pull-card" / "SKILL.md").read_text()
            self.assertIn("name: pull-card", codex_skill)
            self.assertIn("description: ", codex_skill)
            self.assertIn("# Pull a card", codex_skill)
            self.assertIn("!`goc", codex_skill)
            self.assertNotIn("_goc-bootstrap.sh", codex_skill)
            self.assertNotIn("CLAUDE_SKILL_DIR", codex_skill)

            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_codex_dry_run_lists_harness_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--agents", "codex")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("agents: codex", planned)
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", planned)
            self.assertNotIn(".claude/", planned)

    # ── --agents claude,codex (mixed: claude plugin, codex vendored) ──────────

    def test_mixed_claude_codex_install_vendors_codex_not_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--agents", "claude,codex")

            self.assert_goc_ok(result)
            # Codex: vendored
            self.assertTrue((cwd / ".codex" / "skills" / "pull-card" / "SKILL.md").is_file())
            # Claude: plugin path (no checked-in skills/hooks)
            self.assertFalse((cwd / ".claude" / "skills").exists())
            self.assertFalse((cwd / ".claude" / "hooks").exists())
            # Guidance written for both
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertTrue((cwd / "CLAUDE.md").is_file())

    def test_mixed_dry_run_shows_codex_harness_not_claude_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--agents", "claude,codex")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("agents: claude,codex", planned)
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", planned)
            self.assertNotIn(".claude/skills/", planned)
            self.assertNotIn(".claude/hooks/", planned)
            self.assertNotIn("settings.json", planned)
            # Claude guidance still appears
            self.assertIn("claude append CLAUDE.md", planned)

    def test_mixed_with_local_skills_vendors_both(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run", "--agents", "claude,codex", "--local-skills")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("claude write  .claude/skills/pull-card/SKILL.md", planned)
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", planned)

    # ── Auto-detection ─────────────────────────────────────────────────────────

    def test_install_auto_detects_claude_marker_uses_plugin_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "CLAUDE.md").write_text("# Existing Claude guidance\n")

            result = self.run_goc(cwd, "install", "--dry-run")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("agents: claude", planned)
            # Plugin path: no skills, no hooks
            self.assertNotIn(".claude/skills/", planned)
            self.assertNotIn(".claude/hooks/", planned)
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
            # Claude detected → plugin path (no skills)
            self.assertNotIn(".claude/skills/", detected.stdout)
            # Codex detected → vendored
            self.assertIn("codex  write  .codex/skills/pull-card/SKILL.md", detected.stdout)
            # Explicit --agents codex only
            self.assertIn("agents: codex", explicit.stdout)
            self.assertNotIn(".claude/", explicit.stdout)

    def test_default_plugin_path_dry_run_shows_only_project_state_and_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--dry-run")

            self.assert_goc_ok(result)
            planned = result.stdout
            self.assertIn("Project state:", planned)
            self.assertIn("Guidance:", planned)
            self.assertNotIn("Runtime affordances:", planned)
            self.assertNotIn(".claude/skills/", planned)
            self.assertNotIn(".claude/hooks/", planned)
            self.assertIn("shared write  .game-of-cards/config.yaml", planned)
            self.assertIn("claude append CLAUDE.md", planned)

    # ── Manifest integrity ────────────────────────────────────────────────────

    def test_v1_agent_manifests_register_claude_and_codex_shims(self) -> None:
        agents_root = ROOT / "goc" / "templates" / "agents"
        claude = json.loads((agents_root / "claude" / "manifest.json").read_text())
        codex = json.loads((agents_root / "codex" / "manifest.json").read_text())

        self.assertEqual(".claude/skills", claude["skills"]["target"])
        self.assertEqual("native", claude["skills"]["frontmatter"])
        self.assertEqual(".codex/skills", codex["skills"]["target"])
        self.assertEqual("codex", codex["skills"]["frontmatter"])
        self.assertIn(".claude/skills/_goc-bootstrap.sh", [file["target"] for file in claude["files"]])
        self.assertIn(".claude/hooks/deck_prompt_router.py", [file["target"] for file in claude["files"]])
        self.assertIn(".claude/hooks/deck_session_start.py", [file["target"] for file in claude["files"]])
        self.assertEqual(".claude/settings.json", claude.get("settings_json"))

    # ── Upgrade: migration (vendored → plugin path) ───────────────────────────

    def test_upgrade_migrates_vendored_claude_to_plugin_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            self.assertTrue((cwd / ".claude" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertTrue((cwd / ".claude" / "settings.json").is_file())

            # Upgrade with migration confirmed (input "y")
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "upgrade"],
                cwd=cwd,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                input="y\n",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertFalse((cwd / ".claude" / "skills").exists())
            self.assertFalse((cwd / ".claude" / "hooks").exists())
            settings_path = cwd / ".claude" / "settings.json"
            if settings_path.exists():
                settings = json.loads(settings_path.read_text())
                hooks = settings.get("hooks", {})
                all_commands = [
                    h.get("command")
                    for event_hooks in hooks.values()
                    for group in event_hooks
                    for h in group.get("hooks", [])
                ]
                goc_cmds = [c for c in all_commands if c and ".claude/hooks/" in c]
                self.assertEqual([], goc_cmds, "GoC hook registrations should be stripped after migration")

    def test_upgrade_keep_local_skills_preserves_vendored_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            stale_skill = cwd / ".claude" / "skills" / "pull-card" / "SKILL.md"
            stale_skill.write_text("stale claude skill\n")

            result = self.run_goc(cwd, "upgrade", "--keep-local-skills")

            self.assert_goc_ok(result)
            self.assertIn("# Pull a card", stale_skill.read_text())
            self.assertTrue((cwd / ".claude" / "hooks" / "deck_session_start.py").is_file())

    def test_upgrade_keep_local_skills_does_not_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))

            result = self.run_goc(cwd, "upgrade", "--keep-local-skills")

            self.assert_goc_ok(result)
            self.assertNotIn("Migrate", result.stdout)

    def test_upgrade_migration_dry_run_shows_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))

            result = self.run_goc(cwd, "upgrade", "--dry-run")

            self.assert_goc_ok(result)
            self.assertIn("plugin path", result.stdout)

    def test_upgrade_migration_decline_preserves_vendored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            stale_skill = cwd / ".claude" / "skills" / "pull-card" / "SKILL.md"
            stale_skill.write_text("custom skill content\n")

            # Decline migration with "n"
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "upgrade"],
                cwd=cwd,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                input="n\n",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertTrue((cwd / ".claude" / "skills").exists())
            self.assertIn("# Pull a card", stale_skill.read_text())

    def test_upgrade_on_plugin_path_repo_needs_no_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            self.assertFalse((cwd / ".claude" / "skills").exists())

            result = self.run_goc(cwd, "upgrade")

            self.assert_goc_ok(result)
            self.assertNotIn("Migrate", result.stdout)
            self.assertFalse((cwd / ".claude" / "skills").exists())

    # ── Upgrade: general behavior ─────────────────────────────────────────────

    def test_upgrade_migrates_legacy_deck_config_without_clobbering_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            config = cwd / ".game-of-cards" / "config.yaml"
            legacy = cwd / ".claude" / "deck-config.yaml"
            config.unlink()
            legacy.write_text("layer_3_goc_dod:\n  - name: legacy-check\n    kind: derived\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--keep-local-skills"))

            self.assertIn("legacy-check", config.read_text())

            config.write_text("layer_3_goc_dod:\n  - name: existing-check\n    kind: derived\n")
            legacy.write_text("layer_3_goc_dod:\n  - name: legacy-new\n    kind: derived\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--keep-local-skills"))

            self.assertIn("existing-check", config.read_text())
            self.assertNotIn("legacy-new", config.read_text())

    def test_upgrade_claude_does_not_clobber_cards_or_non_claude_harness_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--agents", "claude,codex", "--local-skills"))
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )

            claude_skill = cwd / ".claude" / "skills" / "pull-card" / "SKILL.md"
            codex_skill = cwd / ".codex" / "skills" / "pull-card" / "SKILL.md"
            claude_skill.write_text("stale claude skill\n")
            codex_skill.write_text("custom codex skill\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--agents", "claude", "--keep-local-skills"))

            self.assertIn("# Pull a card", claude_skill.read_text())
            self.assertEqual("custom codex skill\n", codex_skill.read_text())
            self.assertTrue((cwd / ".game-of-cards" / "deck" / "smoke-card" / "README.md").is_file())
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_upgrade_help_documents_keep_local_skills_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "upgrade", "--help")

            self.assert_goc_ok(result)
            self.assertIn("--keep-local-skills", result.stdout)
            self.assertNotIn("--no-harness", result.stdout)

    # ── Settings.json (local-skills only) ────────────────────────────────────

    def test_local_skills_install_writes_settings_json_with_hook_registrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))

            settings_path = cwd / ".claude" / "settings.json"
            self.assertTrue(settings_path.is_file())
            settings = json.loads(settings_path.read_text())
            hooks = settings.get("hooks", {})
            session_cmds = [
                h.get("command")
                for group in hooks.get("SessionStart", [])
                for h in group.get("hooks", [])
            ]
            prompt_cmds = [
                h.get("command")
                for group in hooks.get("UserPromptSubmit", [])
                for h in group.get("hooks", [])
            ]
            self.assertIn(
                "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
                session_cmds,
            )
            self.assertIn(
                "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
                prompt_cmds,
            )

    def test_local_skills_upgrade_merges_settings_json_without_clobbering_existing_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            settings_path = cwd / ".claude" / "settings.json"
            existing = json.loads(settings_path.read_text())
            existing["theme"] = "dark"
            existing["hooks"]["PreToolUse"] = [{"hooks": [{"type": "command", "command": "echo pre"}]}]
            settings_path.write_text(json.dumps(existing, indent=2))

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--keep-local-skills"))

            merged = json.loads(settings_path.read_text())
            self.assertEqual("dark", merged.get("theme"))
            self.assertIn("PreToolUse", merged["hooks"])
            session_cmds = [
                h.get("command")
                for group in merged["hooks"].get("SessionStart", [])
                for h in group.get("hooks", [])
            ]
            self.assertIn(
                "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
                session_cmds,
            )

    def test_local_skills_upgrade_does_not_duplicate_hook_registrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--keep-local-skills"))

            settings_path = cwd / ".claude" / "settings.json"
            settings = json.loads(settings_path.read_text())
            session_cmds = [
                h.get("command")
                for group in settings["hooks"].get("SessionStart", [])
                for h in group.get("hooks", [])
            ]
            goc_count = sum(1 for c in session_cmds if "deck_session_start" in (c or ""))
            self.assertEqual(1, goc_count)

    def test_strip_goc_settings_entries_removes_only_goc_hooks(self) -> None:
        from goc.install import _strip_goc_settings_entries

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings: dict = {
                "theme": "dark",
                "hooks": {
                    "SessionStart": [
                        {"hooks": [{"type": "command", "command": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"}]},
                        {"hooks": [{"type": "command", "command": "echo user-hook"}]},
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py"}]},
                    ],
                    "PreToolUse": [
                        {"hooks": [{"type": "command", "command": "echo pre"}]},
                    ],
                },
            }
            settings_path.write_text(json.dumps(settings, indent=2))
            _strip_goc_settings_entries(settings_path)
            result = json.loads(settings_path.read_text())

            self.assertEqual("dark", result.get("theme"))
            # User hook in SessionStart preserved
            self.assertIn("PreToolUse", result["hooks"])
            session_cmds = [
                h.get("command")
                for group in result["hooks"].get("SessionStart", [])
                for h in group.get("hooks", [])
            ]
            self.assertNotIn(
                "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
                session_cmds,
            )
            self.assertIn("echo user-hook", session_cmds)
            # UserPromptSubmit emptied → removed
            self.assertNotIn("UserPromptSubmit", result["hooks"])

    # ── Bootstrap wrapper ─────────────────────────────────────────────────────

    def test_bootstrap_wrapper_reports_missing_and_old_cli_and_execs_current_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
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
                f"(installed: 0.0.1, required: {self._goc_version()}). Run: pipx upgrade game-of-cards\n",
                old.stderr,
            )

            fake_goc.write_text(
                f'#!/bin/sh\n'
                f'if [ "$1" = "--version" ]; then echo "goc, version {self._goc_version()}"; exit 0; fi\n'
                f'printf "fake:%s\\n" "$*"\n'
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

    def test_skill_command_injections_call_goc_directly(self) -> None:
        # Skills shell out to `goc` directly (not via a bootstrap shim) so
        # plugin-installed skills don't trip Claude Code's bash-policy ban
        # on executing scripts shipped from a plugin cache directory.
        roots = [
            ROOT / "goc" / "templates" / "skills",
            ROOT / ".claude" / "skills",
            ROOT / ".codex" / "skills",
        ]
        for root in roots:
            for skill_name in SKILL_NAMES:
                skill = root / skill_name / "SKILL.md"
                text = skill.read_text()
                self.assertNotIn("_goc-bootstrap.sh", text, msg=str(skill))
                self.assertNotIn("CLAUDE_SKILL_DIR", text, msg=str(skill))

    # ── Other install/upgrade tests ───────────────────────────────────────────

    def test_install_writes_runtime_neutral_config_and_attest_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
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
            readme = cwd / ".game-of-cards" / "deck" / "smoke-card" / "README.md"
            readme.write_text(readme.read_text().replace("- [ ] (replace with real criteria)", "- [x] closure ok"))

            attest = self.run_goc(cwd, "attest", "smoke-card", "--non-interactive")

            self.assert_goc_ok(attest)
            self.assertIn("Layer-3 (GoC) checks", attest.stdout)
            self.assertIn("dod-100-percent", (cwd / ".game-of-cards" / "deck" / "smoke-card" / "log.md").read_text())

    def test_state_mutations_respect_auto_commit_config_and_cli_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=cwd, check=True)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
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
                " M .game-of-cards/deck/commit-card/README.md",
                subprocess.run(["git", "status", "--short"], cwd=cwd, text=True, capture_output=True).stdout,
            )

            subprocess.run(["git", "add", ".game-of-cards/deck/commit-card/README.md"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-m", "manual open"], cwd=cwd, check=True, capture_output=True)

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

            forced_again = self.run_goc(cwd, "status", "commit-card", "blocked", "--commit")
            self.assert_goc_ok(forced_again)
            self.assertIn("committed", forced_again.stdout)

    def test_install_uses_new_canonical_deck_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))

            self.assertTrue((cwd / ".game-of-cards" / "deck" / ".goc-version").is_file())
            self.assertFalse((cwd / "deck").exists())

    def test_legacy_root_deck_still_works_as_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            deck = cwd / "deck"
            deck.mkdir()
            (deck / "legacy-card").mkdir()
            (deck / "legacy-card" / "README.md").write_text(
                "---\ntitle: legacy-card\nsummary: legacy\nstatus: open\nstage: null\n"
                "contribution: low\ncreated: 2026-05-01\nclosed_at: null\nhuman_gate: none\n"
                "advances: []\nadvanced_by: []\ntags: [bug]\ndefinition_of_done: |\n  - [x] ok\n---\n"
            )

            result = self.run_goc(cwd, "--no-color")

            self.assert_goc_ok(result)
            self.assertIn("legacy-card", result.stdout)

    _LEGACY_CARD_FRONTMATTER = (
        "---\ntitle: legacy-card\nsummary: legacy\nstatus: open\nstage: null\n"
        "contribution: low\ncreated: 2026-05-01\nclosed_at: null\nhuman_gate: none\n"
        "advances: []\nadvanced_by: []\ntags: [bug]\ndefinition_of_done: |\n  - [x] ok\n---\n"
    )

    def _make_legacy_card(self, cwd: Path) -> Path:
        deck = cwd / "deck"
        deck.mkdir(exist_ok=True)
        (deck / "legacy-card").mkdir(exist_ok=True)
        (deck / "legacy-card" / "README.md").write_text(self._LEGACY_CARD_FRONTMATTER)
        return deck

    def _make_canonical_deck(self, cwd: Path) -> Path:
        deck = cwd / ".game-of-cards" / "deck"
        deck.mkdir(parents=True, exist_ok=True)
        return deck

    def test_dual_tree_blocks_all_commands_and_suggests_migrate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_legacy_card(cwd)
            canonical = self._make_canonical_deck(cwd)
            (canonical / "new-card").mkdir()
            (canonical / "new-card" / "README.md").write_text(
                "---\ntitle: new-card\nsummary: new\nstatus: open\nstage: null\n"
                "contribution: low\ncreated: 2026-05-01\nclosed_at: null\nhuman_gate: none\n"
                "advances: []\nadvanced_by: []\ntags: [story]\ndefinition_of_done: |\n  - [x] ok\n---\n"
            )

            for args in [["--no-color"], ["validate"], ["--status", "all", "--no-color"]]:
                result = self.run_goc(cwd, *args)
                self.assertNotEqual(0, result.returncode, msg=f"Expected failure for: {args}")
                self.assertIn("two deck trees found", result.stderr)
                self.assertIn("goc migrate", result.stderr)

    def test_migrate_moves_legacy_only_cards_and_removes_legacy_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_legacy_card(cwd)
            self._make_canonical_deck(cwd)

            result = self.run_goc(cwd, "migrate", "--yes")

            self.assert_goc_ok(result)
            self.assertIn("migrated: legacy-card", result.stdout)
            self.assertFalse((cwd / "deck").exists())
            self.assertTrue((cwd / ".game-of-cards" / "deck" / "legacy-card" / "README.md").is_file())
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_migrate_refuses_when_same_card_content_differs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_legacy_card(cwd)
            canonical = self._make_canonical_deck(cwd)
            (canonical / "legacy-card").mkdir()
            (canonical / "legacy-card" / "README.md").write_text(
                self._LEGACY_CARD_FRONTMATTER.replace("summary: legacy", "summary: diverged")
            )

            result = self.run_goc(cwd, "migrate", "--yes")

            self.assertNotEqual(0, result.returncode)
            self.assertIn("content drift", result.stderr)

    def test_migrate_dry_run_shows_plan_without_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_legacy_card(cwd)
            self._make_canonical_deck(cwd)

            result = self.run_goc(cwd, "migrate", "--dry-run")

            self.assert_goc_ok(result)
            self.assertIn("Dry run", result.stdout)
            self.assertIn("legacy-card", result.stdout)
            self.assertTrue((cwd / "deck").exists(), "dry run must not remove legacy tree")
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "legacy-card").exists())

    def test_migrate_no_legacy_reports_nothing_to_do(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_canonical_deck(cwd)

            result = self.run_goc(cwd, "migrate")

            self.assert_goc_ok(result)
            self.assertIn("No legacy deck/", result.stdout)

    def test_install_detects_legacy_deck_as_existing_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            legacy_deck = cwd / "deck"
            legacy_deck.mkdir()
            (legacy_deck / ".goc-version").write_text("0.0.1\n")

            result = self.run_goc(cwd, "install")

            self.assertEqual(1, result.returncode)
            self.assertIn("already installed", result.stderr)
            self.assertIn("deck/.goc-version", result.stderr)

    def test_upgrade_works_against_legacy_deck_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=cwd, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=cwd, check=True)
            legacy_deck = cwd / "deck"
            legacy_deck.mkdir()
            (legacy_deck / ".goc-version").write_text("0.0.1\n")
            (legacy_deck / "log.md").write_text("# Deck Log\n")

            result = self.run_goc(cwd, "upgrade")

            self.assert_goc_ok(result)
            self.assertTrue((legacy_deck / ".goc-version").is_file())

    def test_move_renames_without_redirect_and_rewrites_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "new", "child-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "advance", "child-card", "--by", "parent-card", "--no-commit"))

            move_result = self.run_goc(cwd, "move", "child-card", "renamed-card")

            self.assert_goc_ok(move_result)
            self.assertEqual("", move_result.stderr, "non-git move fallback must not leak git fatal to stderr")
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "child-card").exists())
            self.assertTrue((cwd / ".game-of-cards" / "deck" / "renamed-card" / "README.md").is_file())
            parent_readme = (cwd / ".game-of-cards" / "deck" / "parent-card" / "README.md").read_text()
            renamed_readme = (cwd / ".game-of-cards" / "deck" / "renamed-card" / "README.md").read_text()
            self.assertIn("advances:\n  - renamed-card\n", parent_readme)
            self.assertNotIn("child-card", parent_readme)
            self.assertIn("title: renamed-card", renamed_readme)
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "child-card" / "REDIRECT.md").exists())
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_validate_rejects_redirect_only_dirs_missing_readmes_and_stale_relations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "new", "source-card", "--gate", "none", "--tag", "story"))
            readme = cwd / ".game-of-cards" / "deck" / "source-card" / "README.md"
            readme.write_text(readme.read_text().replace("advances: []", "advances: [missing-card]"))
            redirect_dir = cwd / ".game-of-cards" / "deck" / "old-card"
            redirect_dir.mkdir()
            (redirect_dir / "REDIRECT.md").write_text("Moved to elsewhere.\n")
            stale_dir = cwd / ".game-of-cards" / "deck" / "stale-card"
            stale_dir.mkdir()
            (stale_dir / "notes.md").write_text("not a card\n")

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertNotEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("old-card: stale card directory contains REDIRECT.md but no README.md", result.stderr)
            self.assertIn("stale-card: card directory missing README.md", result.stderr)
            self.assertIn("source-card: advances: references unknown title 'missing-card'", result.stderr)

    def test_validate_flags_consumer_skill_dir_missing_template_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))

            stale_skill = SKILL_NAMES[0]
            shutil.rmtree(cwd / ".claude" / "skills" / stale_skill)

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertNotEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn(".claude/skills: missing skills", result.stderr)
            self.assertIn(stale_skill, result.stderr)
            self.assertIn("goc upgrade --keep-local-skills", result.stderr)

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--keep-local-skills"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

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

    def _goc_version(self) -> str:
        import importlib.metadata
        return importlib.metadata.version("game-of-cards")


class PluginContextRefusalTest(unittest.TestCase):
    """When the bundled engine runs from inside `claude-plugin/`, it must refuse
    `--local-skills` and `--keep-local-skills` so users don't end up with a
    duplicated source of truth (plugin skills + vendored .claude/skills/).
    """

    def _run_under_plugin_context(
        self, cwd: Path, *args: str
    ) -> subprocess.CompletedProcess[str]:
        """Run goc.cli with PYTHONPATH pointing at a fake `claude-plugin/` dir
        that bundles a copy of the goc package, mimicking the plugin layout.
        """
        plugin_root = cwd / "_plugin" / "claude-plugin"
        if not (plugin_root / "goc").exists():
            shutil.copytree(ROOT / "goc", plugin_root / "goc")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(plugin_root)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _run_under_pipx_context(
        self, cwd: Path, *args: str
    ) -> subprocess.CompletedProcess[str]:
        """Run goc.cli with PYTHONPATH pointing at the source tree (the parent
        directory of `goc/` is the repo root, not `claude-plugin/`)."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_plugin_context_install_rejects_local_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_plugin_context(cwd, "install", "--local-skills", "--dry-run")
            self.assertEqual(2, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("--local-skills is not supported when running under the plugin", result.stderr)
            self.assertIn("pipx install game-of-cards", result.stderr)
            self.assertFalse((cwd / ".game-of-cards").exists(), msg="install should not have run")

    def test_plugin_context_upgrade_rejects_keep_local_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_plugin_context(cwd, "upgrade", "--keep-local-skills")
            self.assertEqual(2, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("--keep-local-skills is not supported when running under the plugin", result.stderr)
            self.assertIn("pipx install game-of-cards", result.stderr)

    def test_plugin_context_install_without_flag_still_works(self) -> None:
        """The refusal must be flag-gated: default install (no --local-skills)
        is the common path under the plugin and must continue to work."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_plugin_context(cwd, "install", "--dry-run")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("agents: claude", result.stdout)
            self.assertNotIn(".claude/skills/", result.stdout)

    def test_pipx_context_install_still_accepts_local_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_pipx_context(cwd, "install", "--local-skills", "--dry-run")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn(".claude/skills/", result.stdout)


if __name__ == "__main__":
    unittest.main()
