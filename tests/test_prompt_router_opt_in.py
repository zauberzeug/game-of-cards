"""The prompt router speaks only in a repo that opted in.

The plugin registers its hooks globally, so `deck_prompt_router.py` runs on
every prompt in every repo the user opens. It used to read only the prompt
text: in a repo with no deck it still announced "[Game of Cards | runtime
active]" and drove the silent card pipeline, so a work-shaped prompt
scaffolded a deck and auto-committed bookkeeping into a repo that never chose
GoC (runtime-hooks-fire-in-repos-that-never-opted-in). These tests drive the
hook over its stdin contract and require silence wherever the session-start
hook finds no deck, and the reminder, unchanged, wherever it finds one. The
project-dir walk itself is pinned to the engine's, beside the other hooks', by
tests/test_project_root_from_subdirectory.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py"

WORK_PROMPT = "can you fix the login redirect bug"
MARKER = "[Game of Cards | runtime active]"


class PromptRouterOptInTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        home = self.tmp / "home"
        home.mkdir()
        self.env = dict(os.environ, HOME=str(home))
        for key in ("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR", "GOC_WORKTREE_DECK"):
            self.env.pop(key, None)
        # The process cwd of every run unless a test says otherwise: no deck
        # here, so only the payload or a project-dir variable can name one.
        self.elsewhere = self.tmp / "elsewhere"
        self.elsewhere.mkdir()

    def repo(self, name: str, deck: str | None = ".game-of-cards/deck") -> Path:
        root = self.tmp / name
        root.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=root, env=self.env, check=True)
        if deck:
            (root / deck).mkdir(parents=True)
        return root

    def route(self, prompt: str = WORK_PROMPT, *, run_from: Path | None = None,
              env: dict | None = None, **payload: object) -> str:
        r = subprocess.run(
            [sys.executable, str(ROUTER)],
            input=json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt, **payload}),
            cwd=run_from or self.elsewhere, env=env or self.env,
            capture_output=True, text=True,
        )
        self.assertEqual(0, r.returncode, msg=r.stderr)
        self.assertEqual("", r.stderr)
        return r.stdout

    def test_work_prompt_in_a_repo_without_a_deck_is_silent(self) -> None:
        plain = self.repo("plain", deck=None)
        self.assertEqual("", self.route(cwd=str(plain)))

    def test_work_prompt_in_an_opted_in_repo_gets_the_reminder(self) -> None:
        opted_in = self.repo("opted-in")
        self.assertIn(MARKER, self.route(cwd=str(opted_in)))

    def test_exploration_prompt_in_an_opted_in_repo_stays_silent(self) -> None:
        opted_in = self.repo("opted-in")
        self.assertEqual("", self.route("explain how the cache works", cwd=str(opted_in)))

    def test_subdirectory_of_an_opted_in_repo_gets_the_reminder(self) -> None:
        opted_in = self.repo("opted-in")
        sub = opted_in / "src" / "pkg"
        sub.mkdir(parents=True)
        self.assertIn(MARKER, self.route(cwd=str(sub)))

    def test_foreign_repo_nested_in_an_opted_in_repo_is_silent(self) -> None:
        self.repo("host")
        inner = self.repo("host/vendor/inner", deck=None)
        self.assertEqual("", self.route(cwd=str(inner)))

    def test_legacy_deck_counts_as_opted_in(self) -> None:
        """As for the session-start hook, which reads a legacy `deck/` too."""
        legacy = self.repo("legacy", deck="deck")
        self.assertIn(MARKER, self.route(cwd=str(legacy)))

    def test_payload_cwd_decides_over_the_process_cwd(self) -> None:
        opted_in = self.repo("opted-in")
        plain = self.repo("plain", deck=None)
        self.assertEqual("", self.route(run_from=opted_in, cwd=str(plain)))

    def test_project_dir_variable_stands_in_for_a_missing_cwd(self) -> None:
        opted_in = self.repo("opted-in")
        plain = self.repo("plain", deck=None)
        for var in ("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR"):
            with self.subTest(var=var):
                self.assertIn(MARKER, self.route(env=dict(self.env, **{var: str(opted_in)})))
                self.assertEqual("", self.route(env=dict(self.env, **{var: str(plain)})))
        # A non-string cwd is no cwd: the variable still decides.
        env = dict(self.env, CLAUDE_PROJECT_DIR=str(opted_in))
        self.assertIn(MARKER, self.route(env=env, cwd=42))

    def test_without_cwd_or_variable_the_process_cwd_decides(self) -> None:
        opted_in = self.repo("opted-in")
        self.assertIn(MARKER, self.route(run_from=opted_in))
        self.assertEqual("", self.route())


if __name__ == "__main__":
    unittest.main()
