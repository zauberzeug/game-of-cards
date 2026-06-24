from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine


class ClosureOnIntegrationGitErrorTest(unittest.TestCase):
    """`_enforce_closure_on_integration_or_exit` must distinguish the three
    `git merge-base --is-ancestor` exit codes:

      0   -> HEAD is an ancestor (integrated)         -> allow closure
      1   -> HEAD is not an ancestor (not integrated) -> block (sys.exit 2)
      128 -> git error (e.g. origin/main unresolvable) -> warn-and-skip

    The previous `!= 0` test collapsed 1 and 128, failing closed on a git
    error with a misleading "HEAD is not reachable" message — when the
    sibling fetch-failure branch warns-and-skips on a git failure.
    """

    def _invoke_with_merge_base_rc(self, rc: int):
        real_run = engine.subprocess.run

        def fake_run(cmd, *args, **kwargs):
            if cmd[:2] == ["git", "fetch"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if cmd[:2] == ["git", "merge-base"]:
                return SimpleNamespace(returncode=rc, stdout=b"", stderr=b"")
            return real_run(cmd, *args, **kwargs)

        with mock.patch.object(engine.subprocess, "run", fake_run), \
                mock.patch.object(
                    engine, "load_deck_config",
                    return_value={"workflow": {"closure_on_integration": True}},
                ), \
                mock.patch.object(engine, "_deck_is_git_tracked", return_value=True):
            engine._enforce_closure_on_integration_or_exit("demo-card")

    def test_integrated_allows_closure(self) -> None:
        # exit 0 -> no SystemExit
        self._invoke_with_merge_base_rc(0)

    def test_not_an_ancestor_blocks_closure(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self._invoke_with_merge_base_rc(1)
        self.assertEqual(ctx.exception.code, 2)

    def test_git_error_warns_and_skips(self) -> None:
        # exit 128 (git error) must NOT block closure — it warns and returns.
        try:
            self._invoke_with_merge_base_rc(128)
        except SystemExit:
            self.fail(
                "a git error (merge-base exit 128) wrongly blocked closure "
                "instead of warning and skipping"
            )


if __name__ == "__main__":
    unittest.main()
