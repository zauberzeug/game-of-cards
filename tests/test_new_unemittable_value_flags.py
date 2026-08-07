"""`goc new` must reject an unemittable --summary/--worker before it mkdirs.

The inline emitter refuses a scalar carrying a character `str.splitlines()`
treats as a line boundary (see `_contains_line_break`), because the vendored
parser would split the document there and drop every field below it. That
refusal is correct, but `_cmd_new` used to reach it only at the README write —
*after* `card_dir.mkdir(parents=True)` — so the CLI exited 1 with a raw
`FrontmatterError` traceback and stranded an empty card directory that turns
`goc validate` red.

The guards now sit beside the other pre-mkdir input checks. These tests pin
both halves of the contract: the clean `ERROR:` + exit 2, and — the part a
"did it fail?" assertion would miss — that no directory survives the refusal.

The two fields differ on purpose. `summary` is routed into a literal block
scalar when it carries only LF, so LF must still be accepted; every other
break character must be refused. `worker` has no block form (`_emit_worker`
sends every scalar through `_yaml_inline`), so any break is refused.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# One per character str.splitlines() breaks on, minus LF (legal in a summary).
NON_LF_BREAKS = ["\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", " ", " "]


class NewUnemittableValueFlagsTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_refused_cleanly(self, *flags: str, expect: str) -> None:
        """Run `goc new` with `flags` and assert the full refusal contract."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".game-of-cards" / "deck").mkdir(parents=True)
            title = "unemittable-value-probe"

            result = self.run_goc(repo, "new", title, "--gate", "none", *flags)

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertNotIn("Traceback (most recent call last)", result.stderr)
            self.assertTrue(
                result.stderr.startswith("ERROR:"),
                msg=f"expected a clean ERROR: line, got {result.stderr!r}",
            )
            self.assertIn(expect, result.stderr)
            # The refusal must leave the deck exactly as it found it: no
            # partially-created card dir for `goc validate` to trip over.
            self.assertFalse(
                (repo / ".game-of-cards" / "deck" / title).exists(),
                msg="refused `goc new` stranded a card directory",
            )

            validate = self.run_goc(repo, "validate")
            self.assertNotIn("card directory missing README.md", validate.stdout + validate.stderr)

    def test_summary_with_each_non_lf_break_is_refused_before_mkdir(self) -> None:
        for ch in NON_LF_BREAKS:
            with self.subTest(char=repr(ch)):
                self.assert_refused_cleanly(
                    "--summary",
                    f"first{ch}second",
                    expect="--summary contains a line-break character",
                )

    def test_worker_with_line_break_is_refused_before_mkdir(self) -> None:
        for ch in ["\n", *NON_LF_BREAKS]:
            with self.subTest(char=repr(ch)):
                self.assert_refused_cleanly(
                    "--summary",
                    "emittable summary",
                    "--worker",
                    f"alice{ch}bob",
                    expect="--worker must not contain a line break",
                )

    def test_trailing_carriage_return_from_a_crlf_paste_is_refused(self) -> None:
        """The realistic door: `--worker "$(cat file)"` on a CRLF-terminated
        file. Command substitution strips a trailing LF but not the CR."""
        self.assert_refused_cleanly(
            "--summary",
            "emittable summary",
            "--worker",
            "alice\r",
            expect="--worker must not contain a line break",
        )

    def test_multi_line_lf_summary_still_scaffolds(self) -> None:
        """LF is emittable (literal block scalar) — the new guard must not
        widen into rejecting the multi-line summaries `goc new` supports."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".game-of-cards" / "deck").mkdir(parents=True)

            result = self.run_goc(
                repo, "new", "lf-summary-card", "--gate", "none", "--summary", "first\nsecond"
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            readme = repo / ".game-of-cards" / "deck" / "lf-summary-card" / "README.md"
            self.assertTrue(readme.is_file())
            text = readme.read_text()
            self.assertIn("summary: |-", text)
            self.assertIn("  first\n  second\n", text)

    def test_single_line_worker_still_scaffolds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".game-of-cards" / "deck").mkdir(parents=True)

            result = self.run_goc(
                repo,
                "new",
                "plain-worker-card",
                "--gate",
                "none",
                "--summary",
                "emittable summary",
                "--worker",
                "alice",
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            readme = repo / ".game-of-cards" / "deck" / "plain-worker-card" / "README.md"
            self.assertIn("worker: alice", readme.read_text())


if __name__ == "__main__":
    unittest.main()
