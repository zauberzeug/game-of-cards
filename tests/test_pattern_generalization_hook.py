"""Regression tests for the pattern_generalization_check stop hook matcher.

The bug (pre-fix): ``BASH_COMMIT_TOKENS = ("git commit", "git add -", ...)``
was matched via substring containment, so the staging-flag token
``"git add -"`` also matched the pathspec-separator form
``git add -- <path>`` — the canonical safe staging idiom from
AGENTS.md.  Pure-staging turns trained the agent to ignore spurious
generalization reminders.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("pattern_generalization_check", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PatternGeneralizationMatcherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _transcript(self, cmd: str) -> Path:
        entry = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}
            ],
        }
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        fh.write(json.dumps(entry) + "\n")
        fh.close()
        return Path(fh.name)

    def _had_mutation(self, cmd: str) -> bool:
        return self.hook._had_code_mutation(str(self._transcript(cmd)))

    def _transcript_for_tool(self, tool_name: str) -> Path:
        entry = {
            "role": "assistant",
            "content": [{"type": "tool_use", "name": tool_name, "input": {}}],
        }
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        fh.write(json.dumps(entry) + "\n")
        fh.close()
        return Path(fh.name)

    def _had_tool_mutation(self, tool_name: str) -> bool:
        return self.hook._had_code_mutation(str(self._transcript_for_tool(tool_name)))

    # --- positive cases: should still fire ---------------------------------

    def test_git_commit_with_pathspec_is_mutation(self):
        self.assertTrue(self._had_mutation("git commit -- foo.py"))

    def test_git_commit_with_message_is_mutation(self):
        self.assertTrue(self._had_mutation("git commit -m 'msg'"))

    def test_git_add_A_is_mutation(self):
        self.assertTrue(self._had_mutation("git add -A"))

    def test_git_add_p_is_mutation(self):
        self.assertTrue(self._had_mutation("git add -p"))

    def test_git_add_u_is_mutation(self):
        self.assertTrue(self._had_mutation("git add -u"))

    def test_git_add_dot_is_mutation(self):
        self.assertTrue(self._had_mutation("git add ."))

    def test_edit_tool_is_mutation(self):
        self.assertTrue(self._had_tool_mutation("Edit"))

    def test_write_tool_is_mutation(self):
        self.assertTrue(self._had_tool_mutation("Write"))

    def test_notebook_edit_tool_is_mutation(self):
        self.assertTrue(self._had_tool_mutation("NotebookEdit"))

    # --- negative cases: must NOT fire -------------------------------------

    def test_git_add_pathspec_separator_is_not_mutation(self):
        """The defect: `git add -- foo.py` was wrongly flagged as a mutation."""
        self.assertFalse(self._had_mutation("git add -- foo.py"))

    def test_git_add_bare_path_is_not_mutation(self):
        self.assertFalse(self._had_mutation("git add foo.py"))

    def test_git_status_is_not_mutation(self):
        self.assertFalse(self._had_mutation("git status"))

    def test_git_add_pathspec_with_multiple_paths_is_not_mutation(self):
        self.assertFalse(self._had_mutation("git add -- foo.py bar.py"))

    def test_read_tool_is_not_mutation(self):
        self.assertFalse(self._had_tool_mutation("Read"))


if __name__ == "__main__":
    unittest.main()
