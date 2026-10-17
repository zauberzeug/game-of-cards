from __future__ import annotations

import errno
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine


# Not valid UTF-8: 0xe9 opens a multi-byte sequence the space does not
# continue, and 0xff can never start one.
UNDECODABLE = b"caf\xe9 \xff done\n"


def _check(cmd: list[str]) -> dict:
    return {"name": "project-check", "kind": "automated", "cmd": cmd}


def _emit(stream: str, exit_code: int) -> list[str]:
    """A real command that writes UNDECODABLE to `stream` and exits."""
    return [
        sys.executable,
        "-c",
        f"import sys; sys.{stream}.buffer.write({UNDECODABLE!r}); sys.exit({exit_code})",
    ]


@unittest.skipIf(os.name == "nt", "exec permission and shebang semantics are POSIX")
class AttestCheckCannotStartTest(unittest.TestCase):
    """A check that cannot be started is a failed check, not a crash.

    `_run_automated_check` already maps a missing command to
    `(False, "command not found: ...")`, which `_cmd_attest` records as a FAIL
    row before exiting 2. A command that exists but cannot be executed raises
    other `OSError`s from `Popen` — EACCES for a script without the executable
    bit, ENOEXEC for one without a shebang, since `subprocess` calls `execve`
    with no `/bin/sh` fallback. `_cmd_attest` catches only
    `KeyboardInterrupt`, so those escaped as a traceback that wrote no
    closure block and skipped every later check.
    """

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def _script(self, body: str, mode: int) -> Path:
        path = self.tmp / "check.sh"
        path.write_text(body)
        path.chmod(mode)
        return path

    def test_script_without_the_executable_bit_fails_the_check(self) -> None:
        path = self._script("#!/bin/sh\necho ok\n", 0o644)

        passed, summary = engine._run_automated_check(_check([str(path)]))

        self.assertFalse(passed)
        self.assertIn(str(path), summary)
        self.assertIn(os.strerror(errno.EACCES), summary)

    def test_executable_script_without_a_shebang_fails_the_check(self) -> None:
        path = self._script("echo ok\n", 0o755)

        passed, summary = engine._run_automated_check(_check([str(path)]))

        self.assertFalse(passed)
        self.assertIn(str(path), summary)
        self.assertIn(os.strerror(errno.ENOEXEC), summary)

    def test_missing_command_keeps_its_own_message(self) -> None:
        """The pre-existing branch is untouched: still `command not found`."""
        missing = self.tmp / "no-such-check"

        passed, summary = engine._run_automated_check(_check([str(missing)]))

        self.assertEqual((False, f"command not found: {missing}"), (passed, summary))


class AttestCheckUndecodableOutputTest(unittest.TestCase):
    """Output that does not decode leaves the verdict to the exit code.

    `text=True` decoded the check's output strictly, so one byte outside the
    host codec raised `UnicodeDecodeError` after the check had already
    finished — a passing check crashed `goc attest` exactly like a failing one.
    """

    def test_exit_code_alone_decides_the_verdict(self) -> None:
        for stream, exit_code, expected in (("stdout", 0, True), ("stderr", 1, False)):
            with self.subTest(stream=stream, exit_code=exit_code):
                passed, summary = engine._run_automated_check(_check(_emit(stream, exit_code)))

                self.assertIs(expected, passed)
                self.assertIn("done", summary)
                if not expected:
                    self.assertTrue(summary.startswith("exit 1: "), summary)

    def test_undecodable_bytes_render_as_ascii_escapes(self) -> None:
        # The codec `subprocess` decodes `text=True` pipes with.
        codec = io.TextIOWrapper(io.BytesIO()).encoding
        try:
            UNDECODABLE.decode(codec)
        except UnicodeDecodeError:
            pass
        else:
            self.skipTest(f"{codec} decodes every byte of the payload; nothing to escape")

        for stream, exit_code in (("stdout", 0), ("stderr", 1)):
            with self.subTest(stream=stream, exit_code=exit_code):
                _, summary = engine._run_automated_check(_check(_emit(stream, exit_code)))

                self.assertIn("\\xff", summary)
                # ASCII escapes stay printable and writable to log.md under any
                # host codec; U+FFFD from errors="replace" would not.
                summary.encode("ascii")


if __name__ == "__main__":
    unittest.main()
