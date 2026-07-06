"""Detection of an installed Claude Code GoC plugin payload.

Regresses `_claude_plugin_present()` for the env-root fast-path — see card
`skills-source-auto-resolves-vendored-when-claude-plugin-root-names-a-versioned-payload`.
Claude Code sets `CLAUDE_PLUGIN_ROOT` to the running plugin's payload root,
which on a marketplace install is named for the version (e.g.
`.../game-of-cards/0.0.25`), not `game-of-cards`. `<root>/skills/` existing
must confirm presence regardless of the root's basename.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import _claude_plugin_present  # noqa: E402


class ClaudePluginPresentTest(unittest.TestCase):
    def _tmpdir(self) -> str:
        # `TestCase.enterContext` needs Python >= 3.11; CI still runs 3.10,
        # so register cleanup explicitly instead.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name

    def _empty_home(self) -> str:
        # A HOME with no ~/.claude/plugins tree so that candidate cannot mask
        # (or spuriously satisfy) detection — isolating the env-root path.
        return self._tmpdir()

    def test_env_root_versioned_payload_is_detected(self) -> None:
        """CLAUDE_PLUGIN_ROOT pointing at a versioned payload root is present."""
        home = self._empty_home()
        base = Path(self._tmpdir())
        payload = base / "game-of-cards" / "0.0.25"
        (payload / "skills" / "deck").mkdir(parents=True)
        (payload / "skills" / "deck" / "SKILL.md").write_text("x")
        with mock.patch.dict(
            os.environ,
            {"HOME": home, "CLAUDE_PLUGIN_ROOT": str(payload)},
            clear=False,
        ):
            self.assertTrue(_claude_plugin_present())

    def test_env_root_arbitrary_basename_is_detected(self) -> None:
        """The env-root fast-path ignores the root's basename entirely."""
        home = self._empty_home()
        base = Path(self._tmpdir())
        payload = base / "some-cache-dir" / "abc123"
        (payload / "skills").mkdir(parents=True)
        with mock.patch.dict(
            os.environ,
            {"HOME": home, "CLAUDE_PLUGIN_ROOT": str(payload)},
            clear=False,
        ):
            self.assertTrue(_claude_plugin_present())

    def test_home_plugins_dir_still_requires_goc_named_payload(self) -> None:
        """A bare `<home>/.claude/plugins/skills/` (no game-of-cards payload)
        must NOT be a false positive — the container candidate keeps the name
        guard so a non-GoC plugin's skills/ dir cannot satisfy detection."""
        home = self._empty_home()
        (Path(home) / ".claude" / "plugins" / "skills").mkdir(parents=True)
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env["HOME"] = home
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(_claude_plugin_present())

    def test_home_plugins_dir_with_goc_payload_is_detected(self) -> None:
        """The container candidate still finds a game-of-cards* payload under
        ~/.claude/plugins via the rglob descent (no regression)."""
        home = self._empty_home()
        payload = (
            Path(home) / ".claude" / "plugins" / "marketplace" / "game-of-cards"
        )
        (payload / "skills").mkdir(parents=True)
        env = dict(os.environ)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env["HOME"] = home
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(_claude_plugin_present())


if __name__ == "__main__":
    unittest.main()
