"""Regression tests for the plugin+vendored hook double-fire validator.

`validate_plugin_hook_double_fire` warns when a repo fires its GoC lifecycle
hooks twice — once from an enabled Claude Code plugin and once from hooks
vendored into `.claude/`. The check is advisory and gated on plugin
*enablement* resolved across the settings cascade, not payload presence.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goc import engine, install

VENDORED_HOOKS = {
    "hooks": {
        "SessionStart": [{"hooks": [{"type": "command",
            "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py"}]}],
    }
}

GOC_KEY = "game-of-cards@zauberzeug-claude"

#: A not-yet-quoted `${CLAUDE_PROJECT_DIR}/….py` script path in a hook command.
_UNQUOTED_SCRIPT = re.compile(r'(?<!")(\$\{CLAUDE_PROJECT_DIR\}/[^\s"]+\.py)(?!")')


def _quoted_registry() -> dict[str, str]:
    """`GOC_CLAUDE_HOOKS` with every script path quoted, the shell-safe form
    `hook-command-registrations-word-split-on-install-paths-with-spaces`
    prescribes. Already-quoted paths are left alone, so once the shipped
    registry quotes them this is simply the shipped registry."""
    return {
        event: _UNQUOTED_SCRIPT.sub(r'"\1"', command)
        for event, command in install.GOC_CLAUDE_HOOKS.items()
    }


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
        # ...and the switch runs through `goc upgrade`'s cleanup: deleting
        # .claude/hooks/ by hand leaves the settings.json registrations
        # pointing at missing scripts, and the pin alone removes nothing.
        self.assertIn("goc upgrade", w.detail)
        self.assertNotIn("remove .claude/hooks", w.detail)

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

    # --- the script names come from the registry's one walk ------------------
    # `VENDORED_HOOKS` above is a hand-copied, unquoted fixture. Its commands
    # end in `.py`, so in `json.dumps` the JSON string's own closing quote
    # follows the script name, and a parse that kept a trailing `"` on each
    # name still matched it. The cases below write the settings the way
    # `goc install --local-skills` does, through `_merge_claude_settings`, so
    # they test whatever command shape the registry actually holds.
    def _assert_installed_registry_warns(self):
        home, repo = self._dirs()
        _write(home / ".claude" / "settings.json", {"enabledPlugins": {GOC_KEY: True}})
        install._merge_claude_settings(repo / ".claude" / "settings.json")
        warns = self._run(repo, home)
        self.assertEqual(len(warns), 1, "double-fire warning lost for the installed registry")
        names = ", ".join(sorted(install.claude_hook_bindings()[0]))
        self.assertIn(f"also vendored in .claude/ ({names})", warns[0].detail)

    def test_installed_registry_warns(self):
        self._assert_installed_registry_warns()

    def test_installed_quoted_registry_warns(self):
        quoted = _quoted_registry()
        self.assertTrue(
            all('"${CLAUDE_PROJECT_DIR}/' in command for command in quoted.values()),
            f"quoting did not reach every registry command: {quoted}",
        )
        with mock.patch.dict(install.GOC_CLAUDE_HOOKS, quoted, clear=True):
            self._assert_installed_registry_warns()

    def test_hook_names_come_from_claude_hook_bindings(self):
        """`claude_hook_bindings` is the registry's one command-to-script
        walk; a second hand-rolled parse is how this check went blind."""
        for registry in (dict(install.GOC_CLAUDE_HOOKS), _quoted_registry()):
            with self.subTest(command=next(iter(registry.values()))), \
                    mock.patch.dict(install.GOC_CLAUDE_HOOKS, registry, clear=True):
                self.assertEqual(
                    engine._goc_hook_basenames(), set(install.claude_hook_bindings()[0])
                )


if __name__ == "__main__":
    unittest.main()
