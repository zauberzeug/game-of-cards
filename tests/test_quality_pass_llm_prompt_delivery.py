"""Regression guard: `goc quality-pass --llm` reaches `claude` with a deck of any size.

`_run_sonnet_quality_pass` once handed the whole prompt -- the title, summary
and DoD of every selected card -- to `claude -p` as ONE argv element. Linux
refuses any single argument over MAX_ARG_STRLEN (32 pages: 131,072 bytes on
4 KiB pages), so a deck past about 80 cards of this repo's average size could
never start Claude, and the `OSError` escaped the call site as a traceback.
The prompt now travels on stdin, which has no per-argument cap.

The launch failures that remain -- `claude` missing, not executable, or not a
valid executable -- end the run with one `ERROR:` line and exit 1, and none
of them is reported as an unparseable response.

Every fake `claude` here is the ONLY entry on PATH. CPython's exec loop tries
each PATH entry in turn, so a fake that failed to start must never fall
through to a real `claude` and hand it the deck.
"""

from __future__ import annotations

import argparse
import errno
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


# Linux's MAX_ARG_STRLEN on 4 KiB pages: the largest single argv string
# `execve` accepts, however large the total ARG_MAX is.
PER_ARGUMENT_LIMIT = 131_072

# Records each call as one JSON line -- its argv and its stdin -- so a test sees
# the prompt wherever the engine sends it, then answers with an empty verdict
# list in the `--output-format json` envelope.
FAKE_CLAUDE = """\
import json, os, sys
stdin = sys.stdin.buffer.read().decode("utf-8")
with open(os.environ["FAKE_CLAUDE_CAPTURE"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps({"argv": sys.argv[1:], "stdin": stdin}) + "\\n")
print(json.dumps({"result": "[]"}))
"""

_TITLE_IN_PROMPT_RE = re.compile(r'"title": "([a-z0-9-]+)"')


def _dod(i: int) -> str:
    # Six method-tagged items of ~270 characters: ~1.7 KB per card, about the
    # mean summary + DoD size of this repo's open queue on 2026-11-02.
    filler = (
        "the fix lands in the engine, the plugin mirrors are re-synced, and a "
        "regression test pins the behaviour so a later refactor cannot quietly "
        "bring the defect back without turning the suite red on the same commit"
    )
    return "".join(f"  - [ ] TDD: criterion {k} of synthetic card {i}: {filler}.\n" for k in range(1, 7))


def _write_deck(deck: Path, count: int) -> list[str]:
    deck.mkdir(parents=True)
    titles = []
    for i in range(1, count + 1):
        title = f"synthetic-card-{i:03d}"
        titles.append(title)
        card = deck / title
        card.mkdir()
        (card / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f'summary: "Synthetic open card {i} for the quality-pass prompt-delivery guard."\n'
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            'created: "2026-11-02T00:00:00Z"\n'
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            f"{_dod(i)}"
            "---\n\n"
            f"# {title}\n\nSynthetic card body.\n",
            encoding="utf-8",
        )
        (card / "log.md").write_text("", encoding="utf-8")
    return titles


def _llm_help() -> str:
    parser = engine._build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    qp = sub.choices["quality-pass"]
    return next(a.help for a in qp._actions if "--llm" in a.option_strings)


class QualityPassCliTest(unittest.TestCase):
    """Drives `goc quality-pass --llm` through the real CLI."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.project = self.root / "project"
        self.deck = self.project / ".game-of-cards" / "deck"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.capture = self.root / "claude-calls.jsonl"

    def _install_fake_claude(self) -> None:
        fake = self.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE, encoding="utf-8")
        shim = self.bin / "claude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)

    def _goc(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env.pop("GOC_WORKTREE_DECK", None)
        # The fake's directory is the WHOLE PATH (see the module docstring).
        # The engine needs nothing else from it: it is started by absolute
        # interpreter path and the shim names its interpreter absolutely.
        env["PATH"] = str(self.bin)
        env["FAKE_CLAUDE_CAPTURE"] = str(self.capture)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=str(self.project), env=env, stdin=subprocess.DEVNULL,
            text=True, capture_output=True, check=False, timeout=300,
        )

    def _calls(self) -> list[dict]:
        if not self.capture.exists():
            return []
        return [json.loads(line) for line in self.capture.read_text(encoding="utf-8").splitlines()]

    def test_a_prompt_larger_than_one_argument_reaches_claude_whole(self) -> None:
        titles = _write_deck(self.deck, 100)
        self._install_fake_claude()
        res = self._goc("quality-pass", "--llm", "--dry-run")
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        self.assertNotIn("Traceback", res.stderr)
        self.assertIn("auditing 100 cards", res.stdout)
        calls = self._calls()
        self.assertTrue(calls, msg="`claude` was never started")
        delivered = "".join(" ".join(c["argv"]) + c["stdin"] for c in calls)
        # The guard is only meaningful while the prompt really is over the
        # limit a single argument may carry.
        self.assertGreater(len(delivered.encode("utf-8")), PER_ARGUMENT_LIMIT)
        self.assertEqual(sorted(set(_TITLE_IN_PROMPT_RE.findall(delivered))), titles)
        # No argv element carries the cards: the prompt is on stdin.
        for call in calls:
            self.assertTrue(all(len(arg.encode("utf-8")) < 1024 for arg in call["argv"]), msg=call["argv"])

    def test_the_llm_help_describes_the_single_call_the_pass_makes(self) -> None:
        # The help once promised a "Sonnet-batched" audit while the pass sent
        # every card in one unbounded call. It must describe what the pass does.
        _write_deck(self.deck, 3)
        self._install_fake_claude()
        res = self._goc("quality-pass", "--llm", "--dry-run")
        self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
        self.assertEqual(len(self._calls()), 1)
        help_text = _llm_help()
        self.assertNotIn("batch", help_text.lower())
        self.assertIn("one `claude -p` call", help_text)

    def test_a_missing_claude_is_one_error_line_not_a_parse_failure(self) -> None:
        # No fake installed: the PATH directory is empty.
        _write_deck(self.deck, 2)
        res = self._goc("quality-pass", "--llm", "--dry-run")
        self.assertEqual(res.returncode, 1, msg=res.stdout + res.stderr)
        self.assertNotIn("Traceback", res.stderr)
        lines = [ln for ln in res.stderr.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, msg=res.stderr)
        self.assertTrue(lines[0].startswith("ERROR: cannot run claude:"), msg=lines[0])
        self.assertIn("not on PATH", lines[0])
        self.assertNotIn("could not parse", lines[0])


class QualityPassLaunchFailureTest(unittest.TestCase):
    """Each way `claude` can fail is reported as what it is, in one line."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        deck = Path(tmp.name) / ".game-of-cards" / "deck"
        _write_deck(deck, 2)
        prev = engine.DECK_DIR
        engine.DECK_DIR = deck
        self.addCleanup(setattr, engine, "DECK_DIR", prev)

    def _run(self, **run_mock: object) -> tuple[object, str]:
        """Run the pass with `subprocess.run` replaced; return (exit code, stderr)."""
        args = engine._build_parser().parse_args(["quality-pass", "--llm", "--dry-run"])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(engine.subprocess, "run", **run_mock) as run, \
                redirect_stdout(out), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                engine._cmd_quality_pass(args)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], "claude")
        return cm.exception.code, err.getvalue()

    def _assert_one_error_line(self, stderr: str) -> str:
        lines = [ln for ln in stderr.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, msg=stderr)
        self.assertTrue(lines[0].startswith("ERROR: "), msg=lines[0])
        return lines[0]

    def test_an_oserror_starting_claude_ends_in_one_error_line(self) -> None:
        cases = (
            (errno.E2BIG, "Argument list too long", OSError),
            (errno.EACCES, "Permission denied", PermissionError),
            (errno.ENOEXEC, "Exec format error", OSError),
        )
        for code, strerror, exc_type in cases:
            with self.subTest(strerror=strerror):
                rc, err = self._run(side_effect=exc_type(code, strerror, "claude"))
                self.assertEqual(rc, 1)
                line = self._assert_one_error_line(err)
                self.assertEqual(line, f"ERROR: cannot run claude: {strerror}")

    def test_a_missing_claude_is_not_reported_as_an_unparseable_response(self) -> None:
        rc, err = self._run(side_effect=FileNotFoundError(errno.ENOENT, "No such file or directory", "claude"))
        self.assertEqual(rc, 1)
        line = self._assert_one_error_line(err)
        self.assertTrue(line.startswith("ERROR: cannot run claude:"), msg=line)
        self.assertIn("not on PATH", line)
        self.assertNotIn("could not parse", line)

    def test_an_error_envelope_is_reported_as_claude_s_error(self) -> None:
        reply = subprocess.CompletedProcess(
            ["claude"], 0, stdout=json.dumps({"is_error": True, "result": "Not logged in"}), stderr="",
        )
        rc, err = self._run(return_value=reply)
        self.assertEqual(rc, 1)
        line = self._assert_one_error_line(err)
        self.assertIn("Not logged in", line)
        self.assertNotIn("could not parse", line)

    def test_an_unparseable_reply_is_still_reported_as_one(self) -> None:
        reply = subprocess.CompletedProcess(["claude"], 0, stdout="not json", stderr="")
        rc, err = self._run(return_value=reply)
        self.assertEqual(rc, 1)
        line = self._assert_one_error_line(err)
        self.assertTrue(line.startswith("ERROR: could not parse Sonnet response:"), msg=line)


if __name__ == "__main__":
    unittest.main()
