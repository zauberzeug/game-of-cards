"""Regression: `goc` must not leak a `BrokenPipeError` traceback to
stderr when its stdout consumer closes the pipe early.

Without a SIGPIPE handler, CPython translates the OS-level signal
into a `BrokenPipeError` exception that fires during interpreter
shutdown (when the partially-buffered `sys.stdout` flush hits the
closed pipe). The traceback pollutes terminals and propagates a
non-zero exit status under `set -o pipefail`. `goc.cli.main()`
restores the default SIGPIPE disposition (`signal.SIG_DFL`) before
any argv dispatch so the kernel terminates the process cleanly when
the pipe closes.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class SigpipeHandlerTest(unittest.TestCase):
    def test_done_listing_through_closed_pipe_emits_no_traceback(self) -> None:
        # Launch `goc --done` with stdout piped, read a few lines, then
        # close the consumer end. The producer should be terminated by
        # SIGPIPE without writing a Python-level traceback to stderr.
        with subprocess.Popen(
            [sys.executable, "-m", "goc.cli", "--done"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as proc:
            assert proc.stdout is not None and proc.stderr is not None
            for _ in range(3):
                if not proc.stdout.readline():
                    break
            proc.stdout.close()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                self.fail("goc --done did not exit within 30s after pipe close")
            err = proc.stderr.read() or ""
        self.assertNotIn("BrokenPipeError", err, f"stderr leaked traceback:\n{err}")
        self.assertNotIn("Exception ignored", err, f"stderr leaked shutdown noise:\n{err}")


if __name__ == "__main__":
    unittest.main()
