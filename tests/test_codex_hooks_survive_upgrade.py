"""Regression guard: codex-plugin hook commands survive an in-place plugin upgrade.

Codex materializes the plugin under a versioned cache dir
(`.../game-of-cards/game-of-cards/<version>/`) and expands ${PLUGIN_ROOT} in
hooks.json commands at session start. A marketplace upgrade deletes the old
version dir, so a naive `python3 ${PLUGIN_ROOT}/hooks/<script>.py` command
ENOENTs on every hook fire in an already-running session. The shipped
commands must fall back to the newest surviving install instead.

Exercises both plausible ${PLUGIN_ROOT} substitution models — textual template
replacement before execution, and env-var expansion by the shell — since the
fix must hold under either.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HOOK_SCRIPTS = {
    "SessionStart": "deck_session_start.py",
    "UserPromptSubmit": "deck_prompt_router.py",
    "Stop": "pattern_generalization_check.py",
}


def _commands() -> dict[str, str]:
    data = json.loads((ROOT / "codex-plugin" / "hooks" / "hooks.json").read_text())
    commands: dict[str, str] = {}
    for event, groups in data["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                commands[event] = hook["command"]
    return commands


def _run(command: str, plugin_root: Path, textual: bool) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin"}
    if textual:
        command = command.replace("${PLUGIN_ROOT}", str(plugin_root))
    else:
        env["PLUGIN_ROOT"] = str(plugin_root)
    return subprocess.run(
        command, shell=True, env=env, input="{}",
        capture_output=True, text=True, timeout=30,
    )


def _make_install(cache: Path, version: str) -> Path:
    root = cache / version
    (root / "hooks").mkdir(parents=True)
    for name in HOOK_SCRIPTS.values():
        (root / "hooks" / name).write_text("print(__file__)\n")
    return root


class CodexHooksSurviveUpgradeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name) / "plugins/cache/game-of-cards/game-of-cards"
        self.commands = _commands()

    def test_every_event_registers_a_plugin_root_python_command(self) -> None:
        self.assertEqual(set(self.commands), set(HOOK_SCRIPTS))
        for event, script in HOOK_SCRIPTS.items():
            command = self.commands[event]
            self.assertIn("${PLUGIN_ROOT}", command)
            self.assertIn(script, command)
            self.assertIn("python3", command)

    def test_valid_plugin_root_runs_its_own_script(self) -> None:
        current = _make_install(self.cache, "0.0.27")
        _make_install(self.cache, "0.0.28")  # a newer sibling must NOT win
        for event, script in HOOK_SCRIPTS.items():
            for textual in (True, False):
                result = _run(self.commands[event], current, textual)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"0.0.27/hooks/{script}", result.stdout)

    def test_deleted_plugin_root_falls_back_to_surviving_install(self) -> None:
        _make_install(self.cache, "0.0.27")
        stale = self.cache / "0.0.26"  # never created: the upgrade deleted it
        for event, script in HOOK_SCRIPTS.items():
            for textual in (True, False):
                result = _run(self.commands[event], stale, textual)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"0.0.27/hooks/{script}", result.stdout)

    def test_fallback_prefers_newest_install_beyond_lexical_order(self) -> None:
        _make_install(self.cache, "0.0.9")
        time.sleep(0.05)  # ensure distinct mtimes for ls -t
        _make_install(self.cache, "0.0.100")  # lexically before 0.0.9, but newer
        stale = self.cache / "0.0.10"
        for event, script in HOOK_SCRIPTS.items():
            result = _run(self.commands[event], stale, textual=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"0.0.100/hooks/{script}", result.stdout)

    def test_no_surviving_install_fails_loudly(self) -> None:
        stale = self.cache / "0.0.26"
        result = _run(self.commands["UserPromptSubmit"], stale, textual=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
