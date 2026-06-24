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
sys.path.insert(0, str(ROOT))
from goc.install import skill_for_agent  # noqa: E402

SKILL_NAMES = tuple(
    sorted(p.name for p in (ROOT / "goc" / "templates" / "skills").iterdir() if (p / "SKILL.md").is_file())
)
CLAUDE_SHIPPED_SKILLS = tuple(name for name in SKILL_NAMES if skill_for_agent(name, "claude"))


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
            self.assertIn("shared append AGENTS.md", result.stdout)
            self.assertIn("claude append CLAUDE.md", result.stdout)

    def test_default_install_creates_project_state_and_guidance_but_no_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install")

            self.assert_goc_ok(result)
            self.assertIn(f"goc {self._goc_version()} installed for agents: claude (default).", result.stdout)
            self.assertTrue((cwd / ".game-of-cards" / "deck" / ".goc-version").is_file())
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertEqual("@AGENTS.md\n", (cwd / "CLAUDE.md").read_text())
            self.assertFalse((cwd / ".claude" / "skills").exists())
            self.assertFalse((cwd / ".claude" / "hooks").exists())
            self.assertFalse((cwd / ".claude" / "settings.json").exists())
            self.assertFalse((cwd / ".codex").exists())

    def test_claude_only_briefing_target_omits_agents_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "install", "--briefing-target", "CLAUDE.md")

            self.assert_goc_ok(result)
            self.assertFalse((cwd / "AGENTS.md").exists())
            claude_text = (cwd / "CLAUDE.md").read_text()
            self.assertIn("<!-- BEGIN GOC", claude_text)
            self.assertNotIn("@AGENTS.md", claude_text)

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
            self.assertTrue((cwd / ".claude" / "hooks" / "pattern_generalization_check.py").is_file())
            self.assertTrue((cwd / ".claude" / "settings.json").is_file())
            self.assertFalse((cwd / ".codex").exists())

    def test_local_skills_install_pattern_generalization_hook_is_registered_and_present(self) -> None:
        """Regression: --local-skills must copy pattern_generalization_check.py
        to .claude/hooks/ alongside registering its Stop hook in settings.json.
        Previously the manifest's files array stopped at deck_session_start.py,
        so every code-mutating turn ended with a FileNotFoundError on the Stop
        hook command."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))

            hook_path = cwd / ".claude" / "hooks" / "pattern_generalization_check.py"
            self.assertTrue(hook_path.is_file(),
                            "manifest must copy pattern_generalization_check.py to .claude/hooks/")
            settings = json.loads((cwd / ".claude" / "settings.json").read_text())
            stop_cmds = [
                h.get("command")
                for group in settings.get("hooks", {}).get("Stop", [])
                for h in group.get("hooks", [])
            ]
            self.assertIn(
                "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
                stop_cmds,
            )

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
            self.assertEqual("@AGENTS.md\n", (cwd / "CLAUDE.md").read_text())

            for skill_name in CLAUDE_SHIPPED_SKILLS:
                self.assertTrue((cwd / ".claude" / "skills" / skill_name / "SKILL.md").is_file())

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
            self.assertIn("## Codex GoC Command", codex_skill)
            self.assertIn("!`goc", codex_skill)
            self.assertIn("_goc-bootstrap.sh", codex_skill)
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
            # Guidance lives in AGENTS.md; Claude gets a one-line import pointer.
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertEqual("@AGENTS.md\n", (cwd / "CLAUDE.md").read_text())

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
            # Briefing block lands in the default briefing target (AGENTS.md).
            self.assertIn("shared append AGENTS.md", planned)
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
            self.assertIn("shared append AGENTS.md", planned)
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
        self.assertEqual(".claude/settings.json", claude.get("settings_json"))

        # Hook entries are derived from goc/templates/hooks/*.py, not listed
        # in the manifest — verify the loaded shim still surfaces them.
        from goc.install import _load_agent_shim, _templates_root
        shim = _load_agent_shim(_templates_root(), "claude")
        targets = {str(f.target) for f in shim.files}
        self.assertIn(".claude/skills/_goc-bootstrap.sh", targets)
        self.assertIn(".claude/hooks/deck_prompt_router.py", targets)
        self.assertIn(".claude/hooks/deck_session_start.py", targets)
        self.assertIn(".claude/hooks/pattern_generalization_check.py", targets)

    # ── Upgrade: migration (vendored → plugin path) ───────────────────────────

    def test_upgrade_migrates_vendored_claude_to_plugin_path(self) -> None:
        """Migration is opt-in via config edit, not an upgrade-time prompt.

        Flipping `skills_source: vendored` → `plugin` in config and re-running
        upgrade prompts for cleanup; confirming removes the leftover vendored
        layout (skills, hooks, GoC settings entries).
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            self.assertTrue((cwd / ".claude" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertTrue((cwd / ".claude" / "settings.json").is_file())

            # User opts into plugin mode by editing config.
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.write_text(
                config_path.read_text().replace("skills_source: vendored", "skills_source: plugin")
            )

            # Upgrade with cleanup confirmed (input "y")
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

    def test_strip_vendored_harness_survives_absent_template_skill_tree(self) -> None:
        """Cleanup must not crash when the engine omits templates/skills/.

        The bundled plugin engine deliberately ships no templates/skills/
        subdir. The vendored->plugin cleanup iterates that tree to learn the
        GoC-owned skill names; with the tree absent it must yield an empty set
        (skip skill-dir removal, never destroy authored content) rather than
        raising FileNotFoundError.
        """
        from goc.install import _strip_claude_vendored_harness, _templates_root

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Mimic the plugin payload: every template subtree EXCEPT skills/.
            templates = tmp / "templates"
            shutil.copytree(
                _templates_root(), templates, ignore=shutil.ignore_patterns("skills")
            )
            self.assertFalse((templates / "skills").exists())

            target = tmp / "repo"
            goc_skill = target / ".claude" / "skills" / "deck"
            goc_skill.mkdir(parents=True)
            (goc_skill / "SKILL.md").write_text("goc-managed\n")
            user_skill = target / ".claude" / "skills" / "my-custom-skill"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("user-authored\n")

            # Must not raise FileNotFoundError.
            _strip_claude_vendored_harness(target, templates)

            # Authored content is never destroyed when GoC-owned names are unknown.
            self.assertTrue(user_skill.exists())
            self.assertTrue(goc_skill.exists())

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

    def test_upgrade_dry_run_announces_cleanup_when_mode_switches_to_plugin(self) -> None:
        """After flipping config to plugin, dry-run announces the cleanup opportunity."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.write_text(
                config_path.read_text().replace("skills_source: vendored", "skills_source: plugin")
            )

            result = self.run_goc(cwd, "upgrade", "--dry-run")

            self.assert_goc_ok(result)
            self.assertIn("cleanup", result.stdout)

    def test_upgrade_in_vendored_mode_does_not_prompt(self) -> None:
        """Once `skills_source: vendored` is pinned, upgrade never prompts.

        The historical interactive migration prompt was the surface that
        leaked the buggy decline-re-vendors behavior. With config-driven
        mode resolution, vendored is a stable terminal state — no prompt
        fires, no destructive default exists.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            (cwd / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.0\n")

            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "upgrade"],
                cwd=cwd,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                input="",
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertNotIn("Migrate", result.stdout)
            self.assertNotIn("Remove leftover", result.stdout)
            self.assertTrue((cwd / ".claude" / "skills").exists())

    def test_upgrade_on_plugin_path_repo_needs_no_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            self.assertFalse((cwd / ".claude" / "skills").exists())

            result = self.run_goc(cwd, "upgrade")

            self.assert_goc_ok(result)
            self.assertNotIn("Migrate", result.stdout)
            self.assertFalse((cwd / ".claude" / "skills").exists())

    def test_upgrade_refreshes_claude_import_for_agents_briefing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            (cwd / "CLAUDE.md").write_text("@CLAUDE.local.md\n")

            result = self.run_goc(cwd, "upgrade", "--briefing-target", "AGENTS.md")

            self.assert_goc_ok(result)
            self.assertEqual("@AGENTS.md\n", (cwd / "CLAUDE.md").read_text())
            self.assertTrue((cwd / "AGENTS.md").is_file())

    # ── skills_source config: write-on-install, read-on-upgrade ───────────────

    def test_install_default_writes_skills_source_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install"))
            config = (cwd / ".game-of-cards" / "config.yaml").read_text()
            self.assertIn("\nskills_source: plugin\n", config)

    def test_install_local_skills_writes_skills_source_vendored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            config = (cwd / ".game-of-cards" / "config.yaml").read_text()
            self.assertIn("\nskills_source: vendored\n", config)

    def test_write_skills_source_preserves_blank_separators_and_comments(self) -> None:
        """Regression: the rewrite regex must not back-consume blank lines.

        `[#\\s]*` matched `\\n` under MULTILINE, so `pattern.sub` ate the
        blank-line separators (and a preceding comment body) above the key —
        falsifying the docstring's "preserves comments and ordering" promise.
        """
        from goc.install import _write_skills_source

        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.parent.mkdir(parents=True)

            config_path.write_text("auto_commit: true\n\n\nskills_source: auto\n")
            _write_skills_source(cwd, "plugin")
            self.assertEqual(
                config_path.read_text(),
                "auto_commit: true\n\n\nskills_source: plugin\n",
            )

            config_path.write_text("# top comment\n\n# skills_source: vendored\n")
            _write_skills_source(cwd, "plugin")
            self.assertEqual(
                config_path.read_text(),
                "# top comment\n\nskills_source: plugin\n",
            )

    def test_write_skills_source_rewrites_active_key_not_preceding_comment(self) -> None:
        """Regression: prefer the active key over a preceding comment example.

        A single `#?`-optional pattern with `count=1` rewrote whichever
        `skills_source:` line came first in document order. When a commented
        documentation example preceded the active key, the comment got
        un-commented to the new value while the real active line was left
        stale — producing two conflicting `skills_source:` keys and silently
        dropping the requested mode switch.
        """
        from goc.install import _write_skills_source

        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.parent.mkdir(parents=True)

            # Commented doc example FIRST, active key SECOND: the active key
            # must be rewritten, the comment must stay a comment, and there
            # must be exactly one active `skills_source:` key.
            config_path.write_text(
                "# skills_source: auto\n\nskills_source: vendored\n"
            )
            _write_skills_source(cwd, "plugin")
            result = config_path.read_text()
            self.assertEqual(result, "# skills_source: auto\n\nskills_source: plugin\n")
            active_keys = [
                ln
                for ln in result.splitlines()
                if ln.lstrip().startswith("skills_source")
                and not ln.lstrip().startswith("#")
            ]
            self.assertEqual(len(active_keys), 1)

            # Comment-only config still un-comments to an active key.
            config_path.write_text("# skills_source: auto\n")
            _write_skills_source(cwd, "plugin")
            self.assertEqual(config_path.read_text(), "skills_source: plugin\n")

    def test_write_skills_source_preserves_crlf_line_endings(self) -> None:
        """Regression: a CRLF-authored config.yaml must keep its CRLF endings.

        `_write_skills_source` read with `Path.read_text()` (universal-newline
        translation: CRLF -> LF) and wrote back with `Path.write_text()` (LF
        only), so the first install/upgrade/mode-switch silently rewrote a
        Windows consumer's whole config to LF. It must route through
        `_read_text_keep_newline` / `_write_text_keep_newline` so only the
        targeted `skills_source:` line changes.
        """
        from goc.install import _write_skills_source

        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.parent.mkdir(parents=True)

            # CRLF-authored config with a commented example line.
            raw = (
                "# GoC project config\r\n"
                "deck_dir: .game-of-cards/deck\r\n"
                "# skills_source: auto\r\n"
                "some_key: value\r\n"
            ).encode("utf-8")
            config_path.write_bytes(raw)

            before = config_path.read_bytes().count(b"\r")
            _write_skills_source(cwd, "vendored")
            after_bytes = config_path.read_bytes()

            self.assertEqual(
                after_bytes.count(b"\r"),
                before,
                "CRLF line endings must be preserved across the rewrite",
            )
            self.assertIn(b"skills_source: vendored\r\n", after_bytes)
            # The untouched lines keep their CRLF too.
            self.assertIn(b"# GoC project config\r\n", after_bytes)

    def test_write_skills_source_lf_config_stays_lf(self) -> None:
        """An LF-authored config must not gain spurious CR bytes."""
        from goc.install import _write_skills_source

        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.parent.mkdir(parents=True)

            config_path.write_bytes(b"# header\nskills_source: auto\n")
            _write_skills_source(cwd, "plugin")
            after_bytes = config_path.read_bytes()

            self.assertEqual(after_bytes.count(b"\r"), 0)
            self.assertEqual(after_bytes, b"# header\nskills_source: plugin\n")

    def test_plugin_mode_upgrade_preserves_non_goc_skills(self) -> None:
        """Regression: upgrade in plugin mode must not delete user-owned skills.

        The earlier bug had `_sync_skill_tree(replace_skills=True)` rmtreeing
        any skill directory whose name wasn't in the GoC template set,
        collateral-deleting non-GoC user skills. With plugin mode, no skill
        write should happen at all in `.claude/skills/`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install"))
            user_skill = cwd / ".claude" / "skills" / "my-tool"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# My custom tool\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade"))

            self.assertTrue((user_skill / "SKILL.md").is_file())
            self.assertIn("# My custom tool", (user_skill / "SKILL.md").read_text())

    def test_vendored_mode_upgrade_preserves_non_goc_skills(self) -> None:
        """Regression: replace_skills=True must never touch non-eligible dirs.

        Even in vendored mode where eligible skills DO get refreshed in place,
        directories outside the GoC template set are user-owned and must be
        left strictly alone.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            user_skill = cwd / ".claude" / "skills" / "my-tool"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# My custom tool\n")

            self.assert_goc_ok(self.run_goc(cwd, "upgrade", "--keep-local-skills"))

            self.assertTrue((user_skill / "SKILL.md").is_file())
            self.assertIn("# My custom tool", (user_skill / "SKILL.md").read_text())

    def test_validate_skips_skill_parity_in_plugin_mode(self) -> None:
        """Regression for the false-positive `goc validate` failure.

        In plugin mode the user keeps non-GoC skills under `.claude/skills/`;
        the GoC skills live under `${CLAUDE_PLUGIN_ROOT}/skills/`. The
        parity check must skip rather than report all template skills as
        missing.
        """
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install"))
            user_skill = cwd / ".claude" / "skills" / "my-tool"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# My custom tool\n")

            result = self.run_goc(cwd, "validate")

            self.assert_goc_ok(result)
            self.assertNotIn("missing skills", result.stderr + result.stdout)

    def test_plugin_mode_cleanup_confirm_preserves_user_skills(self) -> None:
        """Confirmed cleanup removes GoC-owned skills but leaves user skills alone."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.write_text(
                config_path.read_text().replace("skills_source: vendored", "skills_source: plugin")
            )
            user_skill = cwd / ".claude" / "skills" / "my-custom-tool"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# Custom\n")

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
            self.assertTrue((user_skill / "SKILL.md").is_file())
            self.assertFalse((cwd / ".claude" / "skills" / "pull-card").exists())
            self.assertFalse((cwd / ".claude" / "hooks" / "deck_session_start.py").exists())

    def test_plugin_mode_cleanup_decline_is_a_no_op(self) -> None:
        """Cleanup prompt's decline path is a true no-op — no re-vendor."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install", "--local-skills"))
            config_path = cwd / ".game-of-cards" / "config.yaml"
            config_path.write_text(
                config_path.read_text().replace("skills_source: vendored", "skills_source: plugin")
            )
            user_skill = cwd / ".claude" / "skills" / "my-tool"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("# My custom tool\n")

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
            self.assertTrue((cwd / ".claude" / "skills" / "pull-card" / "SKILL.md").is_file())
            self.assertTrue((user_skill / "SKILL.md").is_file())
            self.assertIn("# My custom tool", (user_skill / "SKILL.md").read_text())

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
                "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
                session_cmds,
            )
            self.assertIn(
                "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
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
                "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
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

    def test_merge_claude_settings_idempotent_merge_leaves_file_untouched(self) -> None:
        from goc.install import GOC_CLAUDE_HOOKS, _merge_claude_settings

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)

            # A user-owned file that already carries every GoC hook, written
            # with the user's own 4-space indentation and key ordering.
            hooks: dict = {}
            for event, command in GOC_CLAUDE_HOOKS.items():
                hooks.setdefault(event, []).append(
                    {"hooks": [{"type": "command", "command": command}]}
                )
            original = json.dumps(
                {
                    "permissions": {"allow": ["Bash(uv run goc:*)"]},
                    "hooks": hooks,
                    "env": {"MY_VAR": "1"},
                },
                indent=4,
            ) + "\n"
            settings_path.write_text(original)

            _merge_claude_settings(settings_path)

            # No hook needed adding -> the user's bytes are preserved verbatim
            # (indentation, key order, trailing newline), not reflowed.
            self.assertEqual(original, settings_path.read_text())

    def test_merge_claude_settings_idempotent_merge_with_non_object_item_makes_no_backup(self) -> None:
        """A settings file that already carries every GoC hook AND contains a
        non-object item in a `hooks[event][].hooks` list is fully idempotent.
        The merge must not spawn a `.bak` sibling or rewrite the file — the
        no-op non-object-items branch used to back up on every run.
        """
        from goc.install import GOC_CLAUDE_HOOKS, _merge_claude_settings

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)

            hooks: dict = {}
            for event, command in GOC_CLAUDE_HOOKS.items():
                hooks.setdefault(event, []).append(
                    {"hooks": [{"type": "command", "command": command}]}
                )
            first_event = next(iter(GOC_CLAUDE_HOOKS))
            hooks[first_event][0]["hooks"].append("literal-user-item")
            original = json.dumps({"hooks": hooks}, indent=2) + "\n"
            settings_path.write_text(original)

            _merge_claude_settings(settings_path)
            _merge_claude_settings(settings_path)

            backups = list(settings_path.parent.glob("settings.json.*.bak"))
            self.assertEqual([], backups, msg=f"backups={backups}")
            # Idempotent merge leaves the user's bytes untouched.
            self.assertEqual(original, settings_path.read_text())

    def test_merge_claude_settings_backs_up_non_object_item_when_rewriting(self) -> None:
        """The non-object-items safety copy must still be made when GoC
        actually rewrites the file (a GoC hook is missing). The backup is the
        pristine pre-reflow copy — deferring it to the write must not drop it.
        """
        from goc.install import GOC_CLAUDE_HOOKS, _merge_claude_settings

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)

            # A user group with a non-object item, but NO GoC hooks present —
            # so the merge must add them and rewrite the file.
            original = json.dumps(
                {"hooks": {"SessionStart": [{"hooks": ["literal-user-item"]}]}},
                indent=2,
            ) + "\n"
            settings_path.write_text(original)

            _merge_claude_settings(settings_path)

            # File was rewritten with GoC hooks added.
            merged = json.loads(settings_path.read_text())
            cmds = [
                h.get("command")
                for group in merged["hooks"].get("SessionStart", [])
                if isinstance(group, dict)
                for h in group.get("hooks", [])
                if isinstance(h, dict)
            ]
            self.assertIn(GOC_CLAUDE_HOOKS["SessionStart"], cmds)
            # Exactly one pristine backup of the original bytes was made.
            backups = list(settings_path.parent.glob("settings.json.*.bak"))
            self.assertEqual(1, len(backups), msg=f"backups={backups}")
            self.assertEqual(original, backups[0].read_text())
            # The non-object item survives the rewrite verbatim.
            self.assertIn(
                "literal-user-item",
                merged["hooks"]["SessionStart"][0]["hooks"],
            )

    def test_merge_claude_settings_writes_when_a_hook_is_missing(self) -> None:
        from goc.install import GOC_CLAUDE_HOOKS, _merge_claude_settings

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps({"theme": "dark"}, indent=2) + "\n")

            _merge_claude_settings(settings_path)

            merged = json.loads(settings_path.read_text())
            self.assertEqual("dark", merged.get("theme"))
            for event, command in GOC_CLAUDE_HOOKS.items():
                cmds = [
                    h.get("command")
                    for group in merged["hooks"].get(event, [])
                    for h in group.get("hooks", [])
                ]
                self.assertIn(command, cmds)

    def test_strip_goc_settings_entries_removes_only_goc_hooks(self) -> None:
        from goc.install import _strip_goc_settings_entries

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings: dict = {
                "theme": "dark",
                "hooks": {
                    "SessionStart": [
                        {"hooks": [{"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"}]},
                        {"hooks": [{"type": "command", "command": "echo user-hook"}]},
                    ],
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py"}]},
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
                "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
                session_cmds,
            )
            self.assertIn("echo user-hook", session_cmds)
            # UserPromptSubmit emptied → removed
            self.assertNotIn("UserPromptSubmit", result["hooks"])

    def test_strip_goc_settings_entries_preserves_user_authored_empty_event_lists(self) -> None:
        """A hook event the user authored as an empty placeholder (e.g.
        `"MyUserEvent": []`) must survive the strip pass. The cleanup loop
        should only delete events the function itself emptied — not ones
        that were empty before the strip began. Sibling of the
        emptied-by-us deletion path already covered above.
        """
        from goc.install import _strip_goc_settings_entries

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings: dict = {
                "hooks": {
                    # GoC-managed; sole hook → emptied → must be removed.
                    "SessionStart": [
                        {"hooks": [{"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"}]},
                    ],
                    # User-authored placeholder; already empty → must survive.
                    "MyUserEvent": [],
                },
            }
            settings_path.write_text(json.dumps(settings, indent=2))
            _strip_goc_settings_entries(settings_path)
            result = json.loads(settings_path.read_text())

            # GoC-emptied event removed by the cleanup pass.
            self.assertNotIn("SessionStart", result.get("hooks", {}))
            # User-authored empty placeholder preserved.
            self.assertEqual([], result["hooks"]["MyUserEvent"])

    def test_strip_goc_settings_entries_preserves_lone_user_authored_empty_event(self) -> None:
        """When the strip pass finds no GoC entries to remove (e.g. a repo
        whose only `hooks` entry is a user-authored empty placeholder),
        nothing should change. The previous behavior wiped the entire
        `hooks` key, silently deleting user state.
        """
        from goc.install import _strip_goc_settings_entries

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings: dict = {"hooks": {"MyUserEvent": []}}
            settings_path.write_text(json.dumps(settings, indent=2))
            _strip_goc_settings_entries(settings_path)
            result = json.loads(settings_path.read_text())

            self.assertEqual({"MyUserEvent": []}, result.get("hooks"))

    def test_strip_goc_settings_entries_preserves_user_authored_empty_hook_groups(self) -> None:
        """A user-authored hook *group* with `hooks: []` (e.g.
        `{"matcher": "startup", "hooks": []}`) must survive the strip pass.
        The per-group gate at the bottom of the filter must only drop groups
        whose `hooks` list the function itself emptied, not ones that were
        empty before the strip began. Sibling of the event-level guard
        already covered above, one layer deeper.
        """
        from goc.install import _strip_goc_settings_entries

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings: dict = {
                "hooks": {
                    "SessionStart": [
                        # GoC-managed group; only hook command is GoC-owned
                        # → filter empties it → must be dropped.
                        {"hooks": [{"type": "command", "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"}]},
                        # User-authored placeholder group; already empty → must survive.
                        {"matcher": "startup", "hooks": []},
                    ],
                },
            }
            settings_path.write_text(json.dumps(settings, indent=2))
            _strip_goc_settings_entries(settings_path)
            result = json.loads(settings_path.read_text())

            # User-authored placeholder group preserved verbatim;
            # GoC-managed group dropped.
            self.assertEqual(
                [{"matcher": "startup", "hooks": []}],
                result["hooks"]["SessionStart"],
            )

    def test_strip_goc_settings_entries_preserves_lone_user_authored_empty_group(self) -> None:
        """When the strip pass finds no GoC entries to remove (a repo whose
        only group under an event is a user-authored placeholder with
        `hooks: []`), nothing should change. The previous behavior dropped
        the group, then cleared the event, then wiped the entire `hooks`
        key — silently deleting user state.
        """
        from goc.install import _strip_goc_settings_entries

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings: dict = {
                "hooks": {
                    "SessionStart": [
                        {"matcher": "startup", "hooks": []},
                    ],
                },
            }
            settings_path.write_text(json.dumps(settings, indent=2))
            _strip_goc_settings_entries(settings_path)
            result = json.loads(settings_path.read_text())

            self.assertEqual(
                {"SessionStart": [{"matcher": "startup", "hooks": []}]},
                result.get("hooks"),
            )

    def test_merge_claude_settings_handles_non_dict_json_shapes(self) -> None:
        """Settings file containing valid JSON of a non-dict shape (`null`,
        list, string, number) must not crash `_merge_claude_settings`; the
        original bytes are preserved in a timestamped `.bak` sibling and a
        warning is printed, matching the existing `JSONDecodeError` branch.
        """
        from goc.install import _merge_claude_settings

        for body in ("null", "[]", '"hello"', "42"):
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _merge_claude_settings(settings_path)

                # The settings file is rewritten with a valid GoC-hooks dict.
                merged = json.loads(settings_path.read_text())
                self.assertIsInstance(merged, dict, msg=f"input={body!r}")
                self.assertIn("hooks", merged, msg=f"input={body!r}")
                # Original bytes preserved in a `.bak` sibling.
                backups = list(Path(tmp).glob("settings.json.*.bak"))
                self.assertEqual(1, len(backups), msg=f"input={body!r} backups={backups}")
                self.assertEqual(body + "\n", backups[0].read_text(), msg=f"input={body!r}")

    def test_strip_goc_settings_entries_handles_non_dict_json_shapes(self) -> None:
        """`_strip_goc_settings_entries` must warn and return — not crash —
        when the file is valid JSON but parses to a non-dict, mirroring the
        existing `JSONDecodeError` branch's behavior. The original bytes
        stay on disk (the strip path does not back up).
        """
        from goc.install import _strip_goc_settings_entries

        for body in ("null", "[]", '"hello"', "42"):
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _strip_goc_settings_entries(settings_path)

                # File left untouched.
                self.assertEqual(body + "\n", settings_path.read_text(), msg=f"input={body!r}")

    def test_merge_claude_settings_handles_non_dict_nested_hooks_shapes(self) -> None:
        """Wrong-shape nested `hooks` and `hooks[event]` values must surface a
        coherent warning, back up the user's original bytes, and let the merge
        proceed — not raise `AttributeError` from `setdefault`/`append` calls
        on the wrong type. Mirrors the closed top-level sibling at the layer
        below it.
        """
        from goc.install import _merge_claude_settings

        # hooks is a non-dict scalar / list / null — entire field is reset.
        for body in ('{"hooks": []}', '{"hooks": null}', '{"hooks": "oops"}', '{"hooks": 42}'):
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _merge_claude_settings(settings_path)

                merged = json.loads(settings_path.read_text())
                self.assertIsInstance(merged.get("hooks"), dict, msg=f"input={body!r}")
                # GoC's three hook events are now wired.
                self.assertIn("SessionStart", merged["hooks"], msg=f"input={body!r}")
                self.assertIn("UserPromptSubmit", merged["hooks"], msg=f"input={body!r}")
                self.assertIn("Stop", merged["hooks"], msg=f"input={body!r}")
                # Original bytes preserved in a single backup sibling.
                backups = list(Path(tmp).glob("settings.json.*.bak"))
                self.assertEqual(1, len(backups), msg=f"input={body!r} backups={backups}")
                self.assertEqual(body + "\n", backups[0].read_text(), msg=f"input={body!r}")

        # hooks is a dict but hooks[event] is the wrong shape — only that
        # event's value is reset; user data is preserved in a backup.
        for event_val in ('"oops"', "42", "null", '{"x": 1}'):
            body = '{"hooks": {"SessionStart": ' + event_val + '}}'
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _merge_claude_settings(settings_path)

                merged = json.loads(settings_path.read_text())
                self.assertIsInstance(merged["hooks"]["SessionStart"], list, msg=f"input={body!r}")
                # The GoC hook for SessionStart is registered.
                session_cmds = [
                    h.get("command")
                    for group in merged["hooks"]["SessionStart"]
                    for h in group.get("hooks", [])
                ]
                self.assertIn(
                    "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
                    session_cmds,
                    msg=f"input={body!r}",
                )
                # Backup preserved (single .bak even if multiple wrong-shape
                # event values triggered a reset).
                backups = list(Path(tmp).glob("settings.json.*.bak"))
                self.assertEqual(1, len(backups), msg=f"input={body!r} backups={backups}")
                self.assertEqual(body + "\n", backups[0].read_text(), msg=f"input={body!r}")

    def test_strip_goc_settings_entries_handles_non_dict_nested_hooks_shapes(self) -> None:
        """`_strip_goc_settings_entries` must NOT char-explode a wrong-shape
        nested value into a list of characters. When `hooks` itself is non-dict
        or `hooks[event]` is non-list, leave the file untouched and warn.
        """
        from goc.install import _strip_goc_settings_entries

        # hooks itself is a non-dict shape.
        for body in ('{"hooks": []}', '{"hooks": null}', '{"hooks": "oops"}', '{"hooks": 42}'):
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _strip_goc_settings_entries(settings_path)

                # File left untouched.
                self.assertEqual(body + "\n", settings_path.read_text(), msg=f"input={body!r}")

        # hooks[event] is non-list (the silent-char-explode regression).
        for event_val in ('"oops"', "42", "null", '{"x": 1}'):
            body = '{"hooks": {"SessionStart": ' + event_val + '}}'
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _strip_goc_settings_entries(settings_path)

                # File left untouched — specifically, the event value is NOT
                # char-exploded into a list of single-character strings.
                self.assertEqual(body + "\n", settings_path.read_text(), msg=f"input={body!r}")

    def test_merge_claude_settings_handles_non_dict_group_hooks_shapes(self) -> None:
        """Layer-4 guard: `hooks[event][i]["hooks"]` may itself be a wrong
        shape (`str`, `int`, `dict`, or list with non-dict items). Merge must
        back up the original bytes, sanitize the offending sub-value, and
        proceed — not raise `AttributeError`/`TypeError`.
        """
        from goc.install import _merge_claude_settings

        session_cmd = "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"

        # group["hooks"] is non-list scalar / dict.
        for inner_val in ('"oops"', "42", '{"x": 1}', "null"):
            body = (
                '{"hooks": {"SessionStart": [{"hooks": ' + inner_val + '}]}}'
            )
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _merge_claude_settings(settings_path)

                merged = json.loads(settings_path.read_text())
                self.assertIsInstance(merged["hooks"]["SessionStart"], list, msg=f"input={body!r}")
                session_cmds = [
                    h.get("command")
                    for group in merged["hooks"]["SessionStart"]
                    if isinstance(group, dict) and isinstance(group.get("hooks"), list)
                    for h in group["hooks"]
                    if isinstance(h, dict)
                ]
                self.assertIn(session_cmd, session_cmds, msg=f"input={body!r}")
                # Original bytes preserved in a backup sibling.
                backups = list(Path(tmp).glob("settings.json.*.bak"))
                self.assertEqual(1, len(backups), msg=f"input={body!r} backups={backups}")
                self.assertEqual(body + "\n", backups[0].read_text(), msg=f"input={body!r}")

        # group["hooks"] is a list with non-dict items mixed in.
        body = (
            '{"hooks": {"SessionStart": [{"hooks": ['
            '{"type": "command", "command": "echo user-hook"}, "literal"'
            ']}]}}'
        )
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(body + "\n")

            _merge_claude_settings(settings_path)

            merged = json.loads(settings_path.read_text())
            # Original bytes preserved in a backup sibling.
            backups = list(Path(tmp).glob("settings.json.*.bak"))
            self.assertEqual(1, len(backups), msg=f"backups={backups}")
            self.assertEqual(body + "\n", backups[0].read_text())
            # User's dict hook AND the non-dict "literal" survive verbatim;
            # GoC's hook is appended as a new group.
            session_groups = merged["hooks"]["SessionStart"]
            self.assertEqual(2, len(session_groups))
            self.assertEqual(
                [{"type": "command", "command": "echo user-hook"}, "literal"],
                session_groups[0]["hooks"],
            )
            self.assertEqual(
                [{"type": "command", "command": session_cmd}],
                session_groups[1]["hooks"],
            )

    def test_strip_goc_settings_entries_handles_non_dict_group_hooks_shapes(self) -> None:
        """Layer-4 guard for strip: when `hooks[event][i]["hooks"]` is a
        wrong shape, strip must leave the file untouched (no char-explode);
        when it is a list with non-dict items mixed with a GoC command, the
        non-dict items survive verbatim and only the GoC command is removed.
        """
        from goc.install import _strip_goc_settings_entries

        # group["hooks"] is non-list — file left untouched byte-for-byte.
        for inner_val in ('"oops"', "42", '{"x": 1}', "null"):
            body = (
                '{"hooks": {"SessionStart": [{"hooks": ' + inner_val + '}]}}'
            )
            with tempfile.TemporaryDirectory() as tmp:
                settings_path = Path(tmp) / "settings.json"
                settings_path.write_text(body + "\n")

                _strip_goc_settings_entries(settings_path)

                # File left untouched — specifically, the inner value is NOT
                # char-exploded into a list of single-character strings.
                self.assertEqual(body + "\n", settings_path.read_text(), msg=f"input={body!r}")

        # group["hooks"] is a list with non-dict items + a GoC command:
        # strip the GoC command, preserve the non-dict items verbatim.
        session_cmd = "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"
        settings: dict = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [
                        {"type": "command", "command": session_cmd},
                        "literal",
                        {"type": "command", "command": "echo user-hook"},
                    ]},
                ],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(json.dumps(settings, indent=2))

            _strip_goc_settings_entries(settings_path)

            result = json.loads(settings_path.read_text())
            session_groups = result["hooks"]["SessionStart"]
            self.assertEqual(1, len(session_groups))
            # GoC's command removed; user's dict hook and the non-dict
            # "literal" both preserved verbatim.
            self.assertEqual(
                [
                    {"type": "command", "command": "echo user-hook"},
                    "literal",
                ],
                session_groups[0]["hooks"],
            )

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

    def test_bootstrap_wrapper_execs_plugin_sibling_cli_without_path_goc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            downstream = tmp_path / "downstream"
            plugin_root = tmp_path / "plugin-cache" / "game-of-cards" / "0.0.99"
            downstream_deck = downstream / ".game-of-cards" / "deck"
            downstream_deck.mkdir(parents=True)
            (downstream_deck / ".goc-version").write_text(f"{self._goc_version()}\n")

            skills_dir = plugin_root / "skills"
            bin_dir = plugin_root / "bin"
            skills_dir.mkdir(parents=True)
            bin_dir.mkdir()
            wrapper_src = ROOT / "goc" / "templates" / "bootstrap" / "_goc-bootstrap.sh"
            wrapper = skills_dir / "_goc-bootstrap.sh"
            shutil.copy2(wrapper_src, wrapper)
            fake_goc = bin_dir / "goc"
            fake_goc.write_text(
                "#!/bin/sh\n"
                f'if [ "$1" = "--version" ]; then echo "goc, version {self._goc_version()}"; exit 0; fi\n'
                'printf "plugin:%s\\n" "$*"\n'
            )
            fake_goc.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = "/usr/bin:/bin"
            result = subprocess.run(
                [str(wrapper), "show", "smoke-card"],
                cwd=downstream,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual("plugin:show smoke-card\n", result.stdout)
            self.assertEqual("", result.stderr)

    def test_skill_command_injections_keep_claude_skills_direct_and_codex_skills_resolved(self) -> None:
        # Claude skills shell out to `goc` directly so plugin-installed Claude
        # skills don't trip Claude Code's bash-policy ban on executing scripts
        # shipped from a plugin cache directory. Codex skills carry a resolver
        # paragraph because Codex does not currently expose plugin bin/ on PATH.
        from goc.install import skill_for_agent

        roots = [
            (ROOT / "goc" / "templates" / "skills", None),
            (ROOT / ".claude" / "skills", "claude"),
            (ROOT / ".codex" / "skills", "codex"),
            (ROOT / "codex-plugin" / "skills", "codex"),
        ]
        for root, agent in roots:
            for skill_name in SKILL_NAMES:
                if agent is not None and not skill_for_agent(skill_name, agent):
                    continue
                skill = root / skill_name / "SKILL.md"
                text = skill.read_text()
                self.assertNotIn("CLAUDE_SKILL_DIR", text, msg=str(skill))
                if agent == "codex":
                    self.assertIn("## Codex GoC Command", text, msg=str(skill))
                    self.assertIn("_goc-bootstrap.sh", text, msg=str(skill))
                elif skill_name == "codex-kickoff":
                    self.assertIn("_goc-bootstrap.sh", text, msg=str(skill))
                else:
                    self.assertNotIn("_goc-bootstrap.sh", text, msg=str(skill))

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

    def test_attest_refuses_when_both_layers_are_empty_and_leaves_log_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            config = cwd / ".game-of-cards" / "config.yaml"
            config.write_text("layer_2_project_dod: []\nlayer_3_goc_dod: []\n")
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )

            attest = self.run_goc(cwd, "attest", "smoke-card", "--non-interactive")

            self.assertEqual(2, attest.returncode, msg=f"stdout:\n{attest.stdout}\n\nstderr:\n{attest.stderr}")
            self.assertIn("no closure checks configured", attest.stderr)
            self.assertNotIn("Attestation OK", attest.stdout)
            log_path = cwd / ".game-of-cards" / "deck" / "smoke-card" / "log.md"
            log_text = log_path.read_text() if log_path.exists() else ""
            self.assertNotIn(
                "## Closure verification",
                log_text,
                msg="log.md must not gain a Closure verification header when no checks are configured",
            )

    def test_attest_refuses_when_every_configured_check_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            config = cwd / ".game-of-cards" / "config.yaml"
            config.write_text(
                "layer_2_project_dod: []\n"
                "layer_3_goc_dod:\n"
                "  - name: advanced-by-closed\n"
                "    kind: derived\n"
                "  - name: dod-100-percent\n"
                "    kind: derived\n"
                "  - name: log-md-closure-entry\n"
                "    kind: derived\n"
            )
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )

            attest = self.run_goc(
                cwd,
                "attest",
                "smoke-card",
                "--skip",
                "advanced-by-closed",
                "--skip",
                "dod-100-percent",
                "--skip",
                "log-md-closure-entry",
                "--non-interactive",
            )

            self.assertEqual(2, attest.returncode, msg=f"stdout:\n{attest.stdout}\n\nstderr:\n{attest.stderr}")
            self.assertIn("every configured closure check was skipped", attest.stderr)
            self.assertNotIn("Attestation OK", attest.stdout)
            log_path = cwd / ".game-of-cards" / "deck" / "smoke-card" / "log.md"
            log_text = log_path.read_text() if log_path.exists() else ""
            self.assertNotIn(
                "## Closure verification",
                log_text,
                msg="log.md must not gain a Closure verification header when every check is skipped",
            )

    def test_attest_runs_when_only_some_checks_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            config = cwd / ".game-of-cards" / "config.yaml"
            config.write_text(
                "layer_2_project_dod: []\n"
                "layer_3_goc_dod:\n"
                "  - name: advanced-by-closed\n"
                "    kind: derived\n"
                "  - name: dod-100-percent\n"
                "    kind: derived\n"
            )
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            readme = cwd / ".game-of-cards" / "deck" / "smoke-card" / "README.md"
            readme.write_text(readme.read_text().replace("- [ ] (replace with real criteria)", "- [x] closure ok"))

            # One check skipped, one still runs — the guard must NOT fire.
            attest = self.run_goc(
                cwd,
                "attest",
                "smoke-card",
                "--skip",
                "advanced-by-closed",
                "--non-interactive",
            )

            self.assert_goc_ok(attest)
            self.assertIn("Attestation OK", attest.stdout)
            log_text = (cwd / ".game-of-cards" / "deck" / "smoke-card" / "log.md").read_text()
            self.assertIn("## Closure verification", log_text)

    def test_attest_skip_with_null_check_description_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            self.assert_goc_ok(self.run_goc(cwd, "install"))
            config = cwd / ".game-of-cards" / "config.yaml"
            # The skipped check carries an explicit `description: null`; a
            # sibling check still runs so the all-skipped guard does not fire
            # before the skip branch builds its summary.
            config.write_text(
                "layer_2_project_dod: []\n"
                "layer_3_goc_dod:\n"
                "  - name: dod-100-percent\n"
                "    kind: derived\n"
                "  - name: log-md-closure-entry\n"
                "    kind: derived\n"
                "    description: null\n"
                "  - name: advanced-by-closed\n"
                "    kind: derived\n"
                "    description: edge prereq check\n"
            )
            self.assert_goc_ok(
                self.run_goc(cwd, "new", "smoke-card", "--gate", "none", "--tag", "story", "--allow-jargon")
            )
            readme = cwd / ".game-of-cards" / "deck" / "smoke-card" / "README.md"
            readme.write_text(readme.read_text().replace("- [ ] (replace with real criteria)", "- [x] closure ok"))

            # Skip the null-description check (the crash trigger) and the
            # string-description check (no-regression); dod-100-percent runs.
            attest = self.run_goc(
                cwd,
                "attest",
                "smoke-card",
                "--skip",
                "log-md-closure-entry",
                "--skip",
                "advanced-by-closed",
                "--non-interactive",
            )

            self.assert_goc_ok(attest)
            self.assertNotIn("TypeError", attest.stderr)
            self.assertIn("log-md-closure-entry — SKIPPED", attest.stdout)
            self.assertIn("advanced-by-closed — SKIPPED", attest.stdout)
            self.assertIn("Attestation OK", attest.stdout)
            # The null description renders as an empty parenthetical; a string
            # description still renders its text (the pre-fix behavior).
            log_text = (cwd / ".game-of-cards" / "deck" / "smoke-card" / "log.md").read_text()
            self.assertIn("log-md-closure-entry SKIPPED — SKIPPED ()", log_text)
            self.assertIn("advanced-by-closed SKIPPED — SKIPPED (edge prereq check)", log_text)

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

    def test_migrate_dry_run_announces_removal_for_identical_only_tree(self) -> None:
        # When every legacy card is byte-identical to its canonical
        # counterpart, the real `goc migrate` still rmtree's the legacy
        # tree — so --dry-run must announce that deletion, not hide it.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_legacy_card(cwd)
            canonical = self._make_canonical_deck(cwd)
            (canonical / "legacy-card").mkdir()
            (canonical / "legacy-card" / "README.md").write_text(self._LEGACY_CARD_FRONTMATTER)

            result = self.run_goc(cwd, "migrate", "--dry-run")

            self.assert_goc_ok(result)
            self.assertIn("identical", result.stdout)
            self.assertIn("Would remove legacy tree", result.stdout)
            self.assertTrue((cwd / "deck").exists(), "dry run must not remove legacy tree")

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
            self.assert_goc_ok(
                self.run_goc(
                    cwd,
                    "status",
                    "active-card",
                    "active",
                    "--worker-who",
                    "bot",
                    "--no-commit",
                )
            )

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


class OpenClawPluginContextTest(unittest.TestCase):
    """Regression for `openclaw-kickoff-defaults-to-claude-install`.

    When the bundled engine runs from inside `openclaw-plugin/`, a no-flag
    install/upgrade must default to *no harness* — OpenClaw ships skills via its
    plugin runtime and has no Claude/Codex surface. Before the fix a fresh repo
    fell back to the documented Claude default and planned `agents: claude` plus
    a `CLAUDE.md` append, contradicting the kickoff's host-agnostic promise.

    These run against a copy of the *source* `goc/` placed under a fake
    `openclaw-plugin/` so they exercise the fix directly, independent of the
    auto-synced plugin mirror.
    """

    def _run_under_openclaw_context(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        plugin_root = cwd / "_plugin" / "openclaw-plugin"
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

    def test_fresh_repo_defaults_to_no_harness_not_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_openclaw_context(cwd, "install", "--dry-run")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("agents: none", result.stdout)
            self.assertIn("shared append AGENTS.md", result.stdout)
            self.assertNotIn("agents: claude", result.stdout)
            self.assertNotIn("claude append CLAUDE.md", result.stdout)
            self.assertNotIn(".claude/", result.stdout)

    def test_stray_agents_md_does_not_trigger_codex_detection(self) -> None:
        """A pre-existing AGENTS.md (the briefing home) must not be read as a
        Codex surface under OpenClaw — auto-detection is suppressed entirely."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "AGENTS.md").write_text("# Existing guidance\n")
            result = self._run_under_openclaw_context(cwd, "install", "--dry-run")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("agents: none", result.stdout)
            self.assertNotIn("agents: codex", result.stdout)
            self.assertNotIn(".codex/", result.stdout)

    def test_explicit_agents_still_overrides_no_harness_default(self) -> None:
        """The no-harness default is default-only; a deliberate --agents wins."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_openclaw_context(cwd, "install", "--dry-run", "--agents", "claude")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("agents: claude", result.stdout)

    def test_real_install_writes_agents_md_and_no_claude_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self._run_under_openclaw_context(cwd, "install")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("no agent harness", result.stdout)
            self.assertTrue((cwd / ".game-of-cards" / "deck" / ".goc-version").is_file())
            self.assertTrue((cwd / "AGENTS.md").is_file())
            self.assertFalse((cwd / "CLAUDE.md").exists())
            self.assertFalse((cwd / ".claude").exists())
            self.assertFalse((cwd / ".codex").exists())
            # Plugin path is pinned, so a later `goc validate` won't expect a
            # vendored skill tree.
            self.assertIn("skills_source: plugin", (cwd / ".game-of-cards" / "config.yaml").read_text())

    def test_upgrade_defaults_to_no_harness_not_claude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assertEqual(0, self._run_under_openclaw_context(cwd, "install").returncode)
            (cwd / ".game-of-cards" / "deck" / ".goc-version").write_text("0.0.1\n")
            result = self._run_under_openclaw_context(cwd, "upgrade", "--dry-run")
            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("agents: none", result.stdout)
            self.assertNotIn("agents: claude", result.stdout)
            self.assertNotIn("claude append CLAUDE.md", result.stdout)


class KickoffStage4StripSnippetTest(unittest.TestCase):
    """Regression coverage for `kickoff-crashes-when-user-declines-merge-question`.

    The original bug was that the kickoff skill body told the model to pass
    `--no-claude-md` / `--no-agents-md` flags that never existed in the
    parser. After the briefing-target unification (`--briefing-target`),
    install writes the briefing block to exactly one home; the per-file
    strip snippet that used to live in Stage 4 of the kickoff skill is no
    longer needed. The remaining contract:

      1. `goc install` runs without per-file flags.
      2. The kickoff skill body (and its claude-kickoff complement) must
         not reference the two flags that never existed.
    """

    SKILL_PATH = ROOT / "goc" / "templates" / "skills" / "kickoff" / "SKILL.md"
    PLUGIN_SKILL_PATH = ROOT / "claude-plugin" / "skills" / "kickoff" / "SKILL.md"

    def _install(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", "install"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_install_no_longer_accepts_no_claude_md_flag(self) -> None:
        """Reproduces the original bug: argparse rejects the flag the old
        skill body told the model to pass. Locks in that the new path does
        not depend on this flag existing."""
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "install", "--no-claude-md"],
                cwd=tmp,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unrecognized arguments: --no-claude-md", result.stderr)

    def test_skill_body_no_longer_references_removed_flags(self) -> None:
        """The two flags that never existed must not appear anywhere in the
        skill body — they were the original crash trigger. Also covers the
        Claude-specific complement `claude-kickoff`, which inherits the same
        contract for the CLAUDE.md / CLAUDE.local.md prompts it owns."""
        paths = [
            self.SKILL_PATH,
            self.PLUGIN_SKILL_PATH,
            ROOT / "goc" / "templates" / "skills" / "claude-kickoff" / "SKILL.md",
            ROOT / "claude-plugin" / "skills" / "claude-kickoff" / "SKILL.md",
        ]
        for path in paths:
            if not path.is_file():
                continue
            with self.subTest(path=path):
                text = path.read_text()
                self.assertNotIn("--no-claude-md", text)
                self.assertNotIn("--no-agents-md", text)


class AppendPrecommitHookWorktreeTest(unittest.TestCase):
    """Regression: `_append_precommit_hook` must treat a git worktree as
    a git checkout. In a worktree `<repo>/.git` is a *file* (containing
    `gitdir: …`), not a directory — the previous `is_dir()` guard
    silently skipped the pre-commit install in any worktree."""

    def _init_main_repo(self, path: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "x@x.com"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "x"], check=True, capture_output=True)
        (path / "README").write_text("init\n")
        subprocess.run(["git", "-C", str(path), "add", "README"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(path), "commit", "-qm", "init"], check=True, capture_output=True)

    def test_append_precommit_hook_writes_in_worktree(self) -> None:
        from goc.install import _append_precommit_hook  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_repo = root / "main"
            worktree = root / "worktree"
            main_repo.mkdir()
            self._init_main_repo(main_repo)
            subprocess.run(
                ["git", "-C", str(main_repo), "worktree", "add", "-q", "-b", "branch", str(worktree)],
                check=True, capture_output=True,
            )

            self.assertTrue((worktree / ".git").is_file())
            self.assertFalse((worktree / ".git").is_dir())

            target = worktree / ".pre-commit-config.yaml"
            _append_precommit_hook(target)

            self.assertTrue(target.is_file(), msg=f"{target} was not written")
            self.assertIn("id: goc-validate", target.read_text())

    def test_append_precommit_hook_skips_when_not_a_git_checkout(self) -> None:
        from goc.install import _append_precommit_hook  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".pre-commit-config.yaml"
            _append_precommit_hook(target)
            self.assertFalse(target.exists())


class UpgradeAppendsPrecommitHookTest(unittest.TestCase):
    """Regression: `goc upgrade`'s dry-run plan lists the pre-commit hook
    append, so the real upgrade must perform it too. The install path skips
    the hook when run before `git init` (no `.git` yet); the documented
    remedy (`git init` then `goc upgrade`) must actually install it instead
    of merely promising to in the dry-run plan."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd, env=env, text=True, capture_output=True, check=False,
        )

    def test_upgrade_appends_pre_commit_hook_after_late_git_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            cfg = cwd / ".pre-commit-config.yaml"

            # Install before the directory is a git checkout — hook skipped.
            install = self.run_goc(cwd, "install", "--agents", "claude", "--local-skills")
            self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
            self.assertFalse(cfg.exists())

            subprocess.run(["git", "init", "-q"], cwd=cwd, check=True, capture_output=True)

            # The dry-run plan promises the append...
            plan = self.run_goc(cwd, "upgrade", "--keep-local-skills", "--dry-run")
            self.assertEqual(plan.returncode, 0, msg=plan.stdout + plan.stderr)
            self.assertIn("append .pre-commit-config.yaml", plan.stdout)

            # ...so the real run must perform it (dry-run/real parity).
            real = self.run_goc(cwd, "upgrade", "--keep-local-skills")
            self.assertEqual(real.returncode, 0, msg=real.stdout + real.stderr)
            self.assertTrue(cfg.is_file(), msg=".pre-commit-config.yaml not written by upgrade")
            self.assertIn("id: goc-validate", cfg.read_text())

    def test_dry_run_omits_pre_commit_append_in_non_git_dir(self) -> None:
        # Inverse of the git-repo case: in a non-git dir the executor skips the
        # pre-commit append, so the dry-run plan must omit it too (no phantom
        # write, no inflated "N writes planned" count).
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            cfg = cwd / ".pre-commit-config.yaml"

            plan = self.run_goc(cwd, "install", "--agents", "claude", "--local-skills", "--dry-run")
            self.assertEqual(plan.returncode, 0, msg=plan.stdout + plan.stderr)
            self.assertNotIn(".pre-commit-config.yaml", plan.stdout)

            real = self.run_goc(cwd, "install", "--agents", "claude", "--local-skills")
            self.assertEqual(real.returncode, 0, msg=real.stdout + real.stderr)
            self.assertFalse(cfg.exists(), msg="real install wrote .pre-commit-config.yaml in non-git dir")

    def test_upgrade_does_not_duplicate_existing_pre_commit_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            cfg = cwd / ".pre-commit-config.yaml"

            subprocess.run(["git", "init", "-q"], cwd=cwd, check=True, capture_output=True)
            install = self.run_goc(cwd, "install", "--agents", "claude", "--local-skills")
            self.assertEqual(install.returncode, 0, msg=install.stdout + install.stderr)
            self.assertEqual(cfg.read_text().count("id: goc-validate"), 1)

            real = self.run_goc(cwd, "upgrade", "--keep-local-skills")
            self.assertEqual(real.returncode, 0, msg=real.stdout + real.stderr)
            self.assertEqual(cfg.read_text().count("id: goc-validate"), 1)


class RefreshStalePrecommitHookTest(unittest.TestCase):
    """Regression: `_append_precommit_hook` must migrate a stale GoC-managed
    `goc-validate` stanza in place. A repo installed before the deck moved
    from deck/ to .game-of-cards/deck/ carries a legacy `files: ^deck/.*$`
    glob; the no-op-when-present short-circuit left it dead (matching no card
    path) across `goc upgrade`."""

    LEGACY = (
        "repos:\n"
        "  - repo: local\n"
        "    hooks:\n"
        "      - id: goc-validate\n"
        "        name: goc validate\n"
        "        entry: goc validate\n"
        "        language: system\n"
        "        pass_filenames: false\n"
        "        files: ^deck/.*$\n"
    )

    def _git_dir(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / ".git").mkdir()
        return root

    def test_legacy_files_glob_is_migrated(self) -> None:
        from goc.install import _append_precommit_hook  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._git_dir(tmp) / ".pre-commit-config.yaml"
            cfg.write_text(self.LEGACY)
            _append_precommit_hook(cfg)
            text = cfg.read_text()
            self.assertNotIn("files: ^deck/.*$", text)
            self.assertIn(r"files: ^\.game-of-cards/deck/.*$", text)
            self.assertEqual(text.count("id: goc-validate"), 1)

    def test_current_block_is_byte_identical_noop(self) -> None:
        from goc.install import PRE_COMMIT_HOOK, _append_precommit_hook  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._git_dir(tmp) / ".pre-commit-config.yaml"
            cfg.write_text("repos:\n" + PRE_COMMIT_HOOK)
            before = cfg.read_text()
            _append_precommit_hook(cfg)
            self.assertEqual(cfg.read_text(), before)

    def test_unrelated_repo_local_hook_is_preserved(self) -> None:
        from goc.install import _append_precommit_hook  # noqa: PLC0415

        user_block = (
            "  - repo: local\n"
            "    hooks:\n"
            "      - id: my-linter\n"
            "        name: my linter\n"
            "        entry: ./lint.sh\n"
            "        language: system\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._git_dir(tmp) / ".pre-commit-config.yaml"
            cfg.write_text(self.LEGACY + user_block)
            _append_precommit_hook(cfg)
            text = cfg.read_text()
            # GoC stanza refreshed...
            self.assertIn(r"files: ^\.game-of-cards/deck/.*$", text)
            # ...user's own hook untouched.
            self.assertIn("id: my-linter", text)
            self.assertIn("entry: ./lint.sh", text)


if __name__ == "__main__":
    unittest.main()
