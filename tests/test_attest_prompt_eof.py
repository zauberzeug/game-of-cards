from __future__ import annotations

import ast
import builtins
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine


def _answers(*lines: str):
    """An `input` stand-in that replays `lines`, then raises EOFError.

    Matches the real builtin: `input` raises `EOFError` once stdin is
    exhausted, which is what an agent harness (stdin at /dev/null) hits on the
    very first prompt.
    """
    queue = list(lines)

    def fake_input(prompt: str = "") -> str:
        print(prompt, end="")
        if not queue:
            raise EOFError("EOF when reading a line")
        return queue.pop(0)

    return fake_input


class AttestPromptEofTest(unittest.TestCase):
    """Interactive closure checks degrade to "declined" at EOF, never crash.

    `_cmd_attest` catches only `KeyboardInterrupt` around the per-check
    dispatch, so an `EOFError` escaping a prompt aborts `goc attest` with a
    traceback and exit 1 — before the attestation block is written. Reaching
    EOF means the same thing `--non-interactive` already names ("declined"),
    and `confirm` / `install._confirm` already implement that non-TTY
    contract, so the prompts must too.
    """

    def test_manual_check_at_eof_declines_instead_of_raising(self) -> None:
        check = {"name": "docs-updated", "kind": "manual", "prompt": "Docs updated? (y/n)"}

        with mock.patch.object(builtins, "input", _answers()), redirect_stdout(io.StringIO()):
            passed, summary = engine._prompt_manual(check)

        self.assertFalse(passed)
        self.assertEqual("(declined)", summary)

    def test_agent_check_at_eof_declines_instead_of_raising(self) -> None:
        check = {"name": "docs-updated", "kind": "agent"}

        with mock.patch.object(builtins, "input", _answers()), redirect_stdout(io.StringIO()):
            passed, summary = engine._prompt_agent(check)

        self.assertFalse(passed)
        self.assertEqual("(declined)", summary)

    def test_eof_on_the_rationale_alone_keeps_the_yes_no_verdict(self) -> None:
        """A yes/no that IS answered survives EOF on the follow-up rationale."""
        check = {
            "name": "docs-updated",
            "kind": "manual",
            "prompt": "Docs updated? (y/n)",
            "rationale_prompt": "Which docs?",
        }

        with mock.patch.object(builtins, "input", _answers("y")), redirect_stdout(io.StringIO()):
            passed, summary = engine._prompt_manual(check)

        self.assertTrue(passed)
        self.assertEqual("OK", summary)

    def test_piped_answers_are_still_honoured(self) -> None:
        """The working path stays working: a supplied answer is read as before."""
        manual = {
            "name": "docs-updated",
            "kind": "manual",
            "prompt": "Docs updated? (y/n)",
            "rationale_prompt": "Which docs?",
        }

        with mock.patch.object(builtins, "input", _answers("y", "README")), redirect_stdout(io.StringIO()):
            self.assertEqual((True, "README"), engine._prompt_manual(manual))

        agent = {"name": "docs-updated", "kind": "agent", "rationale_prompt": "Reason:"}

        with mock.patch.object(builtins, "input", _answers("n", "not run")), redirect_stdout(io.StringIO()):
            self.assertEqual((False, "not run"), engine._prompt_agent(agent))

    def test_agent_n_a_answer_still_passes_with_its_rationale(self) -> None:
        """`n-a` keeps its documented pass-with-reason meaning."""
        check = {"name": "docs-updated", "kind": "agent", "rationale_prompt": "Reason:"}

        with mock.patch.object(builtins, "input", _answers("n-a", "no doc changes")), redirect_stdout(io.StringIO()):
            passed, summary = engine._prompt_agent(check)

        self.assertTrue(passed)
        self.assertEqual("N/A — no doc changes", summary)

    def test_every_attest_prompt_reads_through_the_eof_safe_helper(self) -> None:
        """No prompt helper may call `input` directly and re-open the crash."""
        tree = ast.parse((ROOT / "goc" / "engine.py").read_text())
        funcs = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name in ("_prompt_line", "_prompt_yes_no", "_prompt_manual", "_prompt_agent")
        }
        self.assertEqual(4, len(funcs), sorted(funcs))

        def input_calls(node: ast.AST) -> int:
            return sum(
                1
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id == "input"
            )

        # `_prompt_line` is the single sanctioned `input()` call site...
        self.assertEqual(1, input_calls(funcs["_prompt_line"]))
        # ...and it guards that call against EOF.
        handlers = [
            handler
            for node in ast.walk(funcs["_prompt_line"])
            if isinstance(node, ast.Try)
            for handler in node.handlers
        ]
        self.assertTrue(
            any(
                isinstance(h.type, ast.Name) and h.type.id == "EOFError"
                or isinstance(h.type, ast.Tuple)
                and any(isinstance(e, ast.Name) and e.id == "EOFError" for e in h.type.elts)
                for h in handlers
            ),
            "_prompt_line must handle EOFError",
        )
        # Every other prompt helper goes through it.
        for name in ("_prompt_yes_no", "_prompt_manual", "_prompt_agent"):
            self.assertEqual(0, input_calls(funcs[name]), f"{name} calls input() directly")


if __name__ == "__main__":
    unittest.main()
