"""Regression tests for the plugin+vendored hook double-fire validator.

`validate_plugin_hook_double_fire` warns when a repo fires its GoC lifecycle
hooks twice — once from an enabled Claude Code plugin and once from hooks
vendored into `.claude/`. The check is advisory and gated on plugin
*enablement* resolved across the settings cascade, not payload presence.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from goc import engine

VENDORED_HOOKS = {
    "hooks": {
        "SessionStart": [{"hooks": [{"type": "command",
            "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py"}]}],
    }
}

GOC_KEY = "game-of-cards@zauberzeug-claude"


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


class PluginHookDoubleFireTest(unittest.TestCase):
    def _dirs(self):
        return Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())

    def _run(self, repo, home):
        return engine.validate_plugin_hook_double_fire(repo_root=repo, home=home)

    # --- the warning fires --------------------------------------------------
    def test_enabled_plugin_plus_vendored_warns(self):
        home, repo = self._dirs()
        _write(home / ".claude" / "settings.json", {"enabledPlugins": {GOC_KEY: True}})
        _write(repo / ".claude" / "settings.json", VENDORED_HOOKS)
        warns = self._run(repo, home)
        self.assertEqual(len(warns), 1)
        w = warns[0]
        self.assertEqual(w.klass, "PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE")
        self.assertEqual(w.card, GOC_KEY)
        self.assertIn("pattern_generalization_check.py", w.detail)
        self.assertIn("deck_session_start.py", w.detail)
        # remediation names both escape hatches
        self.assertIn("false", w.detail)
        self.assertIn("skills_source: plugin", w.detail)

    # --- silent cases -------------------------------------------------------
    def test_plugin_disabled_is_silent(self):
        home, repo = self._dirs()
        _write(home / ".claude" / "settings.json", {"enabledPlugins": {GOC_KEY: False}})
        _write(repo / ".claude" / "settings.json", VENDORED_HOOKS)
        self.assertEqual(self._run(repo, home), [])

    def test_plugin_absent_is_silent(self):
        home, repo = self._dirs()
        _write(home / ".claude" / "settings.json", {"enabledPlugins": {"other@mkt": True}})
        _write(repo / ".claude" / "settings.json", VENDORED_HOOKS)
        self.assertEqual(self._run(repo, home), [])

    def test_enabled_plugin_without_vendored_is_silent(self):
        home, repo = self._dirs()
        _write(home / ".claude" / "settings.json", {"enabledPlugins": {GOC_KEY: True}})
        _write(repo / ".claude" / "settings.json", {"hooks": {}})
        self.assertEqual(self._run(repo, home), [])

    def test_missing_settings_is_silent_no_crash(self):
        home, repo = self._dirs()  # neither file written
        self.assertEqual(self._run(repo, home), [])

    def test_malformed_json_is_silent_no_crash(self):
        home, repo = self._dirs()
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text("{not json", encoding="utf-8")
        (repo / ".claude").mkdir(parents=True)
        (repo / ".claude" / "settings.json").write_text("nope", encoding="utf-8")
        self.assertEqual(self._run(repo, home), [])

    # --- cascade precedence -------------------------------------------------
    def test_project_local_disable_overrides_user_enable(self):
        home, repo = self._dirs()
        _write(home / ".claude" / "settings.json", {"enabledPlugins": {GOC_KEY: True}})
        _write(repo / ".claude" / "settings.json", VENDORED_HOOKS)
        _write(repo / ".claude" / "settings.local.json", {"enabledPlugins": {GOC_KEY: False}})
        self.assertEqual(self._run(repo, home), [])

    def test_project_enable_with_user_absent_warns(self):
        home, repo = self._dirs()  # no user settings
        merged: dict = dict(VENDORED_HOOKS)
        merged["enabledPlugins"] = {GOC_KEY: True}
        _write(repo / ".claude" / "settings.json", merged)
        self.assertEqual(len(self._run(repo, home)), 1)


if __name__ == "__main__":
    unittest.main()
