"""Ctrl-D at a confirmation prompt must decline, not raise.

`engine.confirm`, `install._confirm` and the briefing-target picker all branch
on `sys.stdin.isatty()`. That branch is about prompt *echo*: `readline()`
signals end of input by returning `""`, while `input()` raises `EOFError` —
which is exactly what Ctrl-D produces. So the terminal branch is the only one
that can crash, and it is the branch a human takes.

Before the fix all three called bare `input()` there, so an empty pipe declined
cleanly and a Ctrl-D produced a traceback out of `goc migrate` (in front of its
`shutil.rmtree`) and out of both `goc upgrade` prompts.
"""

from __future__ import annotations

import ast
import builtins
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from goc import engine, install

ROOT = Path(__file__).resolve().parent.parent

#: The three prompt sites, as (label, callable, expected-value-at-EOF).
#: Each expectation is the site's own documented empty-answer default, so EOF
#: is asserted to be indistinguishable from pressing Enter.
PROMPT_DEFAULT_FALSE = "engine.confirm"


def _at_eof(prompt: str = "") -> str:
    """An `input` stand-in that is already at end of file, like the builtin."""
    raise EOFError("EOF when reading a line")


def _answers(*lines: str):
    """An `input` stand-in replaying `lines`, then raising EOFError as input does."""
    remaining = list(lines)

    def fake_input(prompt: str = "") -> str:
        if not remaining:
            raise EOFError("EOF when reading a line")
        return remaining.pop(0)

    return fake_input


class ConfirmEofTests(unittest.TestCase):
    """`confirm` / `_confirm` on a terminal, with Ctrl-D at the prompt."""

    def _tty(self):
        return mock.patch.object(engine.sys.stdin, "isatty", lambda: True)

    def _install_tty(self):
        return mock.patch.object(install.sys.stdin, "isatty", lambda: True)

    def test_engine_confirm_at_eof_returns_default_false(self) -> None:
        with self._tty(), mock.patch.object(builtins, "input", _at_eof), \
                redirect_stdout(io.StringIO()):
            self.assertIs(False, engine.confirm("Remove legacy tree?"))

    def test_engine_confirm_at_eof_returns_default_true(self) -> None:
        """EOF takes the caller's `default`, whichever way it points."""
        with self._tty(), mock.patch.object(builtins, "input", _at_eof), \
                redirect_stdout(io.StringIO()):
            self.assertIs(True, engine.confirm("Proceed?", default=True))

    def test_install_confirm_at_eof_returns_default(self) -> None:
        with self._install_tty(), mock.patch.object(builtins, "input", _at_eof), \
                redirect_stdout(io.StringIO()):
            self.assertIs(False, install._confirm("Remove leftover vendored layout?"))
            self.assertIs(True, install._confirm("Proceed?", default=True))

    def test_typed_answers_are_unchanged(self) -> None:
        """The working paths keep working: y/n, case folding, bare Enter."""
        for answer, default, expected in (
            ("y", False, True),
            ("Y", False, True),
            ("yes", False, True),
            ("n", True, False),
            ("no", True, False),
            ("", True, True),      # bare Enter takes the default...
            ("", False, False),    # ...whichever way it points
            ("maybe", True, False),  # anything not starting with y is a no
        ):
            with self.subTest(answer=answer, default=default):
                with self._tty(), mock.patch.object(builtins, "input", _answers(answer)), \
                        redirect_stdout(io.StringIO()):
                    self.assertIs(expected, engine.confirm("Q?", default=default))
                with self._install_tty(), mock.patch.object(builtins, "input", _answers(answer)), \
                        redirect_stdout(io.StringIO()):
                    self.assertIs(expected, install._confirm("Q?", default=default))

    def test_piped_stdin_paths_are_unchanged(self) -> None:
        """The non-TTY branch behaved correctly already and must keep doing so."""
        for text, default, expected in (
            ("y\n", False, True),
            ("n\n", True, False),
            ("", False, False),  # empty pipe == EOF on the guarded branch
            ("", True, True),
        ):
            with self.subTest(piped=text, default=default):
                with mock.patch.object(engine.sys, "stdin", io.StringIO(text)):
                    self.assertIs(expected, engine.confirm("Q?", default=default))
                with mock.patch.object(install.sys, "stdin", io.StringIO(text)):
                    self.assertIs(expected, install._confirm("Q?", default=default))

    def test_piped_branch_does_not_echo_the_prompt(self) -> None:
        """Why the isatty() branch exists at all — echo, not EOF safety.

        Pinning it keeps a future "just always use _prompt_line" simplification
        from silently interleaving the question into captured stdout.
        """
        buf = io.StringIO()
        with mock.patch.object(engine.sys, "stdin", io.StringIO("y\n")), redirect_stdout(buf):
            engine.confirm("Migrate 1 card(s)?")
        self.assertEqual("", buf.getvalue())


class BriefingTargetPickerEofTests(unittest.TestCase):
    """The third copy of the branch: `goc upgrade`'s multi-target picker."""

    def _resolve(self, fake_input):
        found = ("AGENTS.md", "CLAUDE.md")
        with mock.patch.object(install, "_detect_briefing_targets_on_disk", lambda _t: found), \
                mock.patch.object(install.sys.stdin, "isatty", lambda: True), \
                mock.patch.object(builtins, "input", fake_input), \
                redirect_stdout(io.StringIO()):
            return install._resolve_upgrade_briefing_target(
                ROOT, explicit_target=None, dry_run=False
            )

    def test_eof_takes_the_first_candidate(self) -> None:
        """EOF must reach `if not raw: choice = found[0]`, not exit(2) or raise."""
        self.assertEqual("AGENTS.md", self._resolve(_at_eof))

    def test_typed_selection_is_unchanged(self) -> None:
        self.assertEqual("CLAUDE.md", self._resolve(_answers("2")))
        self.assertEqual("AGENTS.md", self._resolve(_answers("1")))
        self.assertEqual("AGENTS.md", self._resolve(_answers("")))

    def test_out_of_range_selection_still_aborts(self) -> None:
        """EOF folding into the default must not soften a real bad answer."""
        for bad in ("0", "3", "-1", "nope"):
            with self.subTest(answer=bad), self.assertRaises(SystemExit) as ctx:
                self._resolve(_answers(bad))
            self.assertEqual(2, ctx.exception.code)


class InputCallSiteGuard(unittest.TestCase):
    """Shape guard: a fourth copy of the bare branch must fail the build.

    Widened from `tests/test_attest_prompt_eof.py`, which asserts the same
    invariant over the four `attest` prompt helpers alone. The behavioural tests
    above only cover the sites that exist today; this covers the ones nobody has
    written yet.
    """

    def _input_call_sites(self, module_path: Path) -> list[str]:
        """Return the enclosing function name of every `input(...)` call."""
        tree = ast.parse(module_path.read_text())
        parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        sites = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "input"
            ):
                continue
            enclosing = parents.get(node)
            while enclosing is not None and not isinstance(
                enclosing, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                enclosing = parents.get(enclosing)
            sites.append(enclosing.name if enclosing is not None else "<module>")
        return sites

    def _guards_eof(self, module_path: Path, func_name: str) -> bool:
        tree = ast.parse(module_path.read_text())
        func = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == func_name
        )
        for node in ast.walk(func):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                caught = handler.type
                names = (
                    [caught.id]
                    if isinstance(caught, ast.Name)
                    else [e.id for e in caught.elts if isinstance(e, ast.Name)]
                    if isinstance(caught, ast.Tuple)
                    else []
                )
                if "EOFError" in names:
                    return True
        return False

    def test_input_is_only_called_from_an_eof_safe_reader(self) -> None:
        for module in ("engine.py", "install.py"):
            path = ROOT / "goc" / module
            with self.subTest(module=module):
                sites = self._input_call_sites(path)
                self.assertEqual(
                    ["_prompt_line"],
                    sorted(set(sites)),
                    f"goc/{module} calls input() outside _prompt_line: "
                    f"{sorted(set(sites))} — route it through the EOF-safe reader",
                )
                self.assertEqual(1, len(sites), f"goc/{module}: _prompt_line calls input() twice")
                self.assertTrue(
                    self._guards_eof(path, "_prompt_line"),
                    f"goc/{module}: _prompt_line must handle EOFError",
                )


if __name__ == "__main__":
    unittest.main()
