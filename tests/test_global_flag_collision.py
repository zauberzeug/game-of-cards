"""Regression guard: global CLI flags survive into subcommand handlers.

Several `goc` subcommands used to redeclare a global flag's `dest` with
a hard default; argparse then silently overwrote the parent value, so
`goc --status done quality-pass`, `goc --done quality-pass`,
`goc --contribution high new <t>`, and `goc --worker alice triage` all
behaved as if the user had not passed the global flag. The fix:
`default=argparse.SUPPRESS` on the redeclared subparser flags so the
parent value survives when the subparser flag is not passed; plus
`_cmd_quality_pass` consults `done_flag` when `status_flag` is unset.

A tripwire enumerates the parser and asserts the invariant directly, so
a future subcommand that redeclares a parent dest without SUPPRESS fails
the build.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _parent_dests(parser: argparse.ArgumentParser) -> set[str]:
    out: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        if action.dest in (argparse.SUPPRESS, "help"):
            continue
        out.add(action.dest)
    return out


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


class GlobalFlagPreservedTest(unittest.TestCase):
    """DoD items 1–4: each global flag survives when paired with its subcommand."""

    def setUp(self) -> None:
        from goc.engine import _build_parser

        self.parser = _build_parser()

    def test_global_status_survives_into_quality_pass(self) -> None:
        args = self.parser.parse_args(["--status", "done", "quality-pass"])
        self.assertEqual(args.status_flag, "done")

    def test_done_shortcut_filters_quality_pass_to_done(self) -> None:
        # The parser writes `done_flag=True`; `_cmd_quality_pass` must
        # consult it and treat it as the documented shortcut for
        # `--status done`. We exercise the handler directly to avoid a
        # full integration setup.
        from goc.engine import _cmd_quality_pass

        args = self.parser.parse_args(["--done", "quality-pass"])
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for title, status in (("done-card", "done"), ("open-card", "open")):
                card_dir = cwd / "deck" / title
                card_dir.mkdir(parents=True)
                done_box = "x" if status == "done" else " "
                closed_at = "2026-05-04" if status == "done" else "null"
                (card_dir / "README.md").write_text(
                    "---\n"
                    f"title: {title}\n"
                    f"summary: {title}\n"
                    f"status: {status}\n"
                    "stage: null\n"
                    "contribution: low\n"
                    "created: 2026-05-04\n"
                    f"closed_at: {closed_at}\n"
                    "human_gate: none\n"
                    "advances: []\n"
                    "advanced_by: []\n"
                    "tags: [bug]\n"
                    "definition_of_done: |\n"
                    f"  - [{done_box}] test card\n"
                    "---\n\n"
                    f"# {title}\n"
                )
            env = os.environ.copy()
            pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "--done", "quality-pass"],
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            combined = result.stdout + result.stderr
            self.assertEqual(0, result.returncode, msg=combined)
            self.assertIn("status=done", result.stdout)
            # Quiet the unused-symbol lint: _cmd_quality_pass is the
            # handler whose contract this test pins.
            self.assertTrue(callable(_cmd_quality_pass))

    def test_global_contribution_survives_into_new(self) -> None:
        args = self.parser.parse_args(["--contribution", "high", "new", "demo-card-x"])
        self.assertEqual(args.contribution, "high")

    def test_global_worker_survives_into_triage(self) -> None:
        # Argparse reads the global default lazily, so isolate from
        # whatever GOC_WORKER is in the test environment.
        env_worker = os.environ.pop("GOC_WORKER", None)
        try:
            from goc.engine import _build_parser

            parser = _build_parser()
        finally:
            if env_worker is not None:
                os.environ["GOC_WORKER"] = env_worker
        args = parser.parse_args(["--worker", "alice", "triage"])
        self.assertEqual(args.worker, "alice")


class SubparserDestCollisionTripwireTest(unittest.TestCase):
    """DoD item 6: any subparser that redeclares a global dest must use SUPPRESS."""

    def test_no_silent_default_overrides_global_flag(self) -> None:
        from goc.engine import _build_parser

        parser = _build_parser()
        parent_dests = _parent_dests(parser)
        offenders: list[tuple[str, str, object]] = []
        for sub_name, sub in _subparsers(parser).items():
            for action in sub._actions:
                if action.dest in (argparse.SUPPRESS, "help"):
                    continue
                if action.dest not in parent_dests:
                    continue
                if action.default is not argparse.SUPPRESS:
                    offenders.append((sub_name, action.dest, action.default))
        self.assertEqual(
            offenders,
            [],
            msg=(
                "Subparser arguments shadow a parent dest without "
                "default=argparse.SUPPRESS. Argparse will silently "
                "overwrite the parent value when the subparser flag is "
                "not passed. Offenders: " + repr(offenders)
            ),
        )


if __name__ == "__main__":
    unittest.main()
