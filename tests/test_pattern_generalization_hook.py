"""Regression tests for the pattern_generalization_check stop hook matcher.

The bug (pre-fix): ``BASH_COMMIT_TOKENS = ("git commit", "git add -", ...)``
was matched via substring containment, so the staging-flag token
``"git add -"`` also matched the pathspec-separator form
``git add -- <path>`` — the canonical safe staging idiom from
AGENTS.md.  Pure-staging turns trained the agent to ignore spurious
generalization reminders.
"""

from __future__ import annotations

import codecs
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "goc" / "templates" / "hooks" / "pattern_generalization_check.py"
TEMPLATE_CONFIG = ROOT / "goc" / "templates" / "game_of_cards" / "config.yaml"


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

    def test_read_tool_is_not_mutation(self):
        self.assertFalse(self._had_tool_mutation("Read"))


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


class ReminderWordingTest(unittest.TestCase):
    """The REMINDER must offer the three-branch (no / connect / file) form.

    The binary "file or don't" wording nudged toward the redundant-umbrella
    anti-pattern: it had no branch for the mature-deck case where the pattern
    is general but a root card already exists, so the right move is to CONNECT
    the instance, not file a duplicate.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def test_no_branch_present(self):
        self.assertIn('"no generalization needed"', self.hook.REMINDER)

    def test_connect_to_existing_root_branch_present(self):
        self.assertIn("CONNECT this instance", self.hook.REMINDER)
        self.assertIn("do not file a duplicate", self.hook.REMINDER)

    def test_file_branch_is_gated_on_none_existing(self):
        self.assertIn("only if none exists", self.hook.REMINDER)
        self.assertIn("Skill(create-card)", self.hook.REMINDER)

    def test_dedup_first(self):
        self.assertIn("dedup first", self.hook.REMINDER)


class OptInDefaultTest(unittest.TestCase):
    """The hook is opt-in (default off): it runs only when
    `.game-of-cards/config.yaml` explicitly sets
    `pattern_generalization_check: true`. Absent config, an absent key, or an
    explicit `false` all leave it a no-op — even on a code-mutating turn.
    """

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _project_dir(self, config_text: str | None) -> str:
        d = Path(tempfile.mkdtemp())
        if config_text is not None:
            goc = d / ".game-of-cards"
            goc.mkdir(parents=True, exist_ok=True)
            (goc / "config.yaml").write_text(config_text, encoding="utf-8")
        return str(d)

    # --- the _enabled gate -------------------------------------------------
    def test_absent_config_is_disabled(self):
        self.assertFalse(self.hook._enabled(self._project_dir(None)))

    def test_config_without_key_is_disabled(self):
        self.assertFalse(
            self.hook._enabled(self._project_dir("workflow:\n  auto_commit: true\n"))
        )

    def test_explicit_false_is_disabled(self):
        self.assertFalse(
            self.hook._enabled(
                self._project_dir("hooks:\n  pattern_generalization_check: false\n")
            )
        )

    def test_explicit_true_is_enabled(self):
        self.assertTrue(
            self.hook._enabled(
                self._project_dir("hooks:\n  pattern_generalization_check: true\n")
            )
        )

    def test_capitalized_and_yes_true_spellings_are_enabled(self):
        # Every YAML-true spelling yaml_lite coerces to True must enable the
        # hook, matching the sibling deck_session_start.py _TRUE_SET.
        for spelling in ("True", "TRUE", "yes", "Yes", "YES"):
            with self.subTest(spelling=spelling):
                self.assertTrue(
                    self.hook._enabled(
                        self._project_dir(
                            f"hooks:\n  pattern_generalization_check: {spelling}\n"
                        )
                    )
                )

    def test_false_spellings_stay_disabled(self):
        for spelling in ("false", "False", "FALSE", "no", "No"):
            with self.subTest(spelling=spelling):
                self.assertFalse(
                    self.hook._enabled(
                        self._project_dir(
                            f"hooks:\n  pattern_generalization_check: {spelling}\n"
                        )
                    )
                )

    # --- main() end-to-end: no-op when disabled, blocks when enabled -------
    def _run_main(self, config_text: str | None, *, mutation: bool = True):
        content = (
            [{"type": "tool_use", "name": "Edit", "input": {}}]
            if mutation
            else [{"type": "text", "text": "hi"}]
        )
        tf = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        tf.write(json.dumps({"role": "assistant", "content": content}) + "\n")
        tf.close()

        project_dir = self._project_dir(config_text)
        stdin = io.StringIO(
            json.dumps(
                {
                    "transcript_path": tf.name,
                    "cwd": project_dir,
                    "stop_hook_active": False,
                }
            )
        )
        err = io.StringIO()
        with mock.patch.object(self.hook.sys, "stdin", stdin), mock.patch.dict(
            self.hook.os.environ, {"CLAUDE_PROJECT_DIR": project_dir}
        ), contextlib.redirect_stderr(err):
            rc = self.hook.main()
        return rc, err.getvalue()

    def test_main_is_noop_when_disabled_even_on_mutation(self):
        rc, err = self._run_main("hooks:\n  pattern_generalization_check: false\n")
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_main_is_noop_when_key_absent_even_on_mutation(self):
        rc, _ = self._run_main(None)
        self.assertEqual(rc, 0)

    def test_main_blocks_when_enabled_on_mutation(self):
        rc, err = self._run_main("hooks:\n  pattern_generalization_check: true\n")
        self.assertEqual(rc, 2)
        self.assertIn("pattern-check", err)


class UndecodableInputTest(unittest.TestCase):
    """A config.yaml or transcript that does not decode must not crash the hook.

    `_enabled` and `_had_code_mutation` read in the host's default encoding
    inside `except OSError`, and a decode failure is a ValueError. `main`
    calls `_enabled` on every Stop event, so a config.yaml the host could not
    decode made the hook exit 1 at every turn end, even with the hook off.
    """

    # LC_ALL=C names the C locale; PYTHONUTF8=0 and PYTHONCOERCECLOCALE=0 stop
    # Python from swapping it for UTF-8. The child's default encoding is then
    # ASCII, standing in for a host whose default encoding is not UTF-8.
    ASCII_DEFAULT = {"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}

    @classmethod
    def setUpClass(cls):
        cls.hook = _load_hook()

    def _project(self, config: bytes) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        project = Path(tmp.name)
        (project / ".game-of-cards").mkdir()
        (project / ".game-of-cards" / "config.yaml").write_bytes(config)
        return project

    def _run_with_ascii_default(self, project: Path, transcript: Path | None):
        env = {**os.environ, **self.ASCII_DEFAULT}
        probe = subprocess.run(
            [sys.executable, "-c", "import locale; print(locale.getpreferredencoding(False))"],
            capture_output=True, text=True, env=env,
        )
        try:
            default = codecs.lookup(probe.stdout.strip()).name
        except LookupError:
            default = probe.stdout.strip()
        if default != "ascii":
            self.skipTest(f"cannot force an ASCII default encoding here ({default!r})")
        payload = {
            "stop_hook_active": False,
            "cwd": str(project),
            "transcript_path": str(transcript) if transcript else "",
        }
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload).encode("ascii"),
            capture_output=True, cwd=project, env=env, timeout=60,
        )

    def test_config_that_does_not_decode_leaves_the_hook_off(self):
        # Even when it opts in: a config that does not decode reads as
        # absent, the way the engine's load_deck_config reads it.
        project = self._project(b"pattern_generalization_check: true\n# owner: Ren\xe9\n")
        self.assertFalse(self.hook._enabled(str(project)))

    def test_transcript_that_does_not_decode_counts_as_no_mutation(self):
        project = self._project(b"pattern_generalization_check: true\n")
        transcript = project / "transcript.jsonl"
        entry = {"role": "assistant", "content": [{"type": "tool_use", "name": "Edit", "input": {}}]}
        transcript.write_bytes(b"\xff\n" + json.dumps(entry).encode("ascii") + b"\n")
        self.assertFalse(self.hook._had_code_mutation(str(transcript)))

    def test_shipped_template_config_under_ascii_default_encoding_exits_zero(self):
        project = self._project(TEMPLATE_CONFIG.read_bytes())
        proc = self._run_with_ascii_default(project, None)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))

    def test_utf8_transcript_under_ascii_default_encoding_still_reminds(self):
        project = self._project(b"pattern_generalization_check: true\n")
        transcript = project / "transcript.jsonl"
        entries = [
            {"role": "user", "content": "fix the typo \U0001F601"},
            {"role": "assistant", "content": [{"type": "tool_use", "name": "Edit", "input": {}}]},
        ]
        transcript.write_bytes(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries).encode("utf-8")
        )
        proc = self._run_with_ascii_default(project, transcript)
        stderr = proc.stderr.decode("utf-8", "replace")
        self.assertEqual(proc.returncode, 2, stderr)
        self.assertIn("pattern-check", stderr)


if __name__ == "__main__":
    unittest.main()
