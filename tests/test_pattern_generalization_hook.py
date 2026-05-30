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

    def test_git_add_long_all_is_mutation(self):
        self.assertTrue(self._had_mutation("git add --all foo/"))

    def test_git_add_long_update_is_mutation(self):
        self.assertTrue(self._had_mutation("git add --update"))

    def test_git_add_long_patch_is_mutation(self):
        self.assertTrue(self._had_mutation("git add --patch"))

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


class CodeMutatingToolSetTest(unittest.TestCase):
    """Pin `CODE_MUTATING_TOOLS` membership.

    The hand-enumerated set has historically lagged Claude Code's mutating
    tool surface (e.g., omitted ``NotebookEdit``). These rows assert every
    canonical mutator fires the generalization reminder, and the canonical
    read-only tool does not.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _transcript_for_tool(self, tool_name: str) -> Path:
        entry = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "name": tool_name, "input": {}}
            ],
        }
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        fh.write(json.dumps(entry) + "\n")
        fh.close()
        return Path(fh.name)

    def _had_mutation_for_tool(self, tool_name: str) -> bool:
        return self.hook._had_code_mutation(str(self._transcript_for_tool(tool_name)))

    def test_edit_is_mutation(self):
        self.assertTrue(self._had_mutation_for_tool("Edit"))

    def test_write_is_mutation(self):
        self.assertTrue(self._had_mutation_for_tool("Write"))

    def test_notebook_edit_is_mutation(self):
        self.assertTrue(self._had_mutation_for_tool("NotebookEdit"))

    def test_read_is_not_mutation(self):
        self.assertFalse(self._had_mutation_for_tool("Read"))


class ToolResultBoundaryTest(unittest.TestCase):
    """The backward walk must cross tool_result user entries to reach the prior tool_use.

    Claude Code wraps every tool_result in a role=user message. A realistic
    Edit-then-explain turn ends with an assistant text reply preceded by a
    tool_result wrapper preceded by the tool_use; treating that tool_result
    as the prior-turn boundary suppresses the reminder on the typical shape.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _transcript(self, entries: list[dict]) -> Path:
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        fh.write("\n".join(json.dumps(e) for e in entries))
        fh.close()
        return Path(fh.name)

    def test_edit_then_tool_result_then_text_is_mutation(self):
        entries = [
            {"message": {"role": "user", "content": "please fix"}},
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "/x"}}
                    ],
                }
            },
            {
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "x", "content": "ok"}
                    ],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Done."}],
                }
            },
        ]
        self.assertTrue(self.hook._had_code_mutation(str(self._transcript(entries))))

    def test_prior_user_prompt_is_a_real_boundary(self):
        """A user entry with non-tool_result content still stops the walk so
        a mutation in an earlier turn does not bleed into this turn's check."""
        entries = [
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "/old"}}
                    ],
                }
            },
            {"message": {"role": "user", "content": "now do something else"}},
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Sure."}],
                }
            },
        ]
        self.assertFalse(self.hook._had_code_mutation(str(self._transcript(entries))))


if __name__ == "__main__":
    unittest.main()
