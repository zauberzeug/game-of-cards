"""A card README whose bytes do not decode takes the corrupt-card path.

`readme.read_text()` raises `UnicodeDecodeError`, a `ValueError` that is not a
`FrontmatterError`, so before `engine.read_card_text` it escaped every
broken-card handler: one mis-encoded card crashed `validate`, the queue, the
board, `triage` and `show` with a traceback naming no file. These tests run
the CLI against a scratch deck holding one healthy card and one card with a
single Latin-1 byte, with Python's UTF-8 mode forced so the byte is
undecodable on any host.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CARD = (
    "---\n"
    "title: {title}\n"
    'summary: "{summary}"\n'
    "status: open\n"
    "stage: null\n"
    "contribution: medium\n"
    'created: "2026-10-10T00:00:00Z"\n'
    "closed_at: null\n"
    "human_gate: none\n"
    "advances: []\n"
    "advanced_by: []\n"
    "tags: [bug]\n"
    "definition_of_done: |\n"
    "  - [ ] TDD: fixture\n"
    "---\n\n"
    "# {title}\n"
)
REASON = "README.md is not decodable text"


def _make_deck(root: Path) -> Path:
    deck = root / ".game-of-cards" / "deck"
    for title, summary in (("healthy-card", "fine"), ("bad-bytes", "caf\xe9")):
        card = deck / title
        card.mkdir(parents=True)
        (card / "README.md").write_bytes(CARD.format(title=title, summary=summary).encode("latin-1"))
        (card / "log.md").write_text("")
    return deck / "bad-bytes" / "README.md"


def _goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONUTF8="1")
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


class UndecodableCardReadmeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.cwd = Path(cls._tmp.name)
        _make_deck(cls.cwd)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def assertNoTraceback(self, proc: subprocess.CompletedProcess[str]) -> None:
        self.assertNotIn("Traceback", proc.stderr, proc.stderr)

    def test_validate_reports_the_card_by_name_and_exits_nonzero(self) -> None:
        proc = _goc(self.cwd, "validate", "--quiet")
        self.assertNoTraceback(proc)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(f"ERROR: bad-bytes: {REASON}", proc.stderr)

    def test_deck_views_warn_and_keep_the_healthy_card(self) -> None:
        for args in ([], ["--json"], ["--board"]):
            with self.subTest(args=args):
                proc = _goc(self.cwd, *args)
                self.assertNoTraceback(proc)
                self.assertEqual(proc.returncode, 0)
                self.assertIn(f"WARNING: bad-bytes: {REASON}", proc.stderr)
                self.assertIn("healthy-card", proc.stdout)

    def test_triage_warns_instead_of_crashing(self) -> None:
        proc = _goc(self.cwd, "triage")
        self.assertNoTraceback(proc)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(f"WARNING: bad-bytes: {REASON}", proc.stderr)

    def test_show_prints_the_card_with_replacement_characters(self) -> None:
        proc = _goc(self.cwd, "show", "bad-bytes")
        self.assertNoTraceback(proc)
        self.assertEqual(proc.returncode, 0)
        self.assertIn('summary: "caf�"', proc.stdout)
        self.assertIn(f"WARNING: bad-bytes: {REASON}", proc.stderr)


class UndecodableCardMutationTest(unittest.TestCase):
    def test_mutation_verb_exits_2_naming_the_cause(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            bad = _make_deck(cwd)
            before = bad.read_bytes()
            proc = _goc(cwd, "status", "bad-bytes", "active", "--no-commit")
            self.assertNotIn("Traceback", proc.stderr, proc.stderr)
            self.assertEqual(proc.returncode, 2)
            self.assertIn(REASON, proc.stderr)
            self.assertEqual(bad.read_bytes(), before)

    def test_migrate_list_style_skips_the_card_and_keeps_its_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            bad = _make_deck(cwd)
            before = bad.read_bytes()
            proc = _goc(cwd, "migrate-list-style")
            self.assertNotIn("Traceback", proc.stderr, proc.stderr)
            self.assertEqual(proc.returncode, 0)
            self.assertIn(f"WARNING: bad-bytes: {REASON}", proc.stderr)
            self.assertEqual(bad.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
