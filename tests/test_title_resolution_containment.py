"""Title arguments must resolve strictly inside DECK_DIR — and canonically.

`DECK_DIR / title` with a path-shaped title escapes the deck: joining an
absolute path replaces DECK_DIR entirely, and a `../` component walks out
of the tree. Every verb that resolves an existing card's title must refuse
such titles with exit 2 *before* any read or write — covered here for one
read verb (show), one overlay verb (wait), and one closure verb (done),
plus the move source path.

Containment alone is not enough. Callers keep using the raw argument
string as the card's *identity* after resolution — writing it into
frontmatter edge fields and comparing it against sibling arguments — so a
non-canonical spelling of an in-deck card (`a/`, `./a`, `a//`, all folded
by `Path` to the same directory) must be refused too, or one card reads as
two downstream. `CanonicalTitleSpellingTest` covers that.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

OUTSIDE_CARD = """---
title: outside-card
status: active
stage: null
contribution: low
created: 2026-05-01
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] item-0
---

# outside-card
"""


class TitleResolutionContainmentTest(unittest.TestCase):
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

    def make_repo(self, tmp: str) -> tuple[Path, Path]:
        """Return (repo_cwd, outside_card_dir) — the outside card lives next
        to the repo so both an absolute path and `../../outside-card`
        (relative to DECK_DIR) reach it."""
        base = Path(tmp)
        cwd = base / "repo"
        card_dir = cwd / "deck" / "real-card"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            "title: real-card\n"
            "summary: real-card\n"
            "status: active\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-01\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] item-0\n"
            "---\n\n"
            "# real-card\n"
        )
        (card_dir / "log.md").write_text("")
        outside = base / "outside-card"
        outside.mkdir()
        (outside / "README.md").write_text(OUTSIDE_CARD)
        return cwd, outside

    def assert_refused(self, result: subprocess.CompletedProcess[str], title: str) -> None:
        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("invalid card title", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("outside-card", result.stdout)

    def escape_titles(self, outside: Path) -> list[str]:
        return [str(outside), "../../outside-card"]

    def test_show_refuses_path_shaped_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            for title in self.escape_titles(outside):
                result = self.run_goc(cwd, "show", title)
                self.assert_refused(result, title)

    def test_wait_refuses_path_shaped_titles_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            for title in self.escape_titles(outside):
                result = self.run_goc(cwd, "wait", title, "--reason", "external")
                self.assert_refused(result, title)
                self.assertNotIn("waiting_on", (outside / "README.md").read_text())

    def test_done_refuses_path_shaped_titles_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            for title in self.escape_titles(outside):
                result = self.run_goc(cwd, "done", title)
                self.assert_refused(result, title)
                self.assertIn("status: active", (outside / "README.md").read_text())

    def test_move_refuses_path_shaped_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            result = self.run_goc(cwd, "move", str(outside), "captured-card")
            self.assert_refused(result, str(outside))
            self.assertTrue(outside.exists())
            self.assertFalse((cwd / "deck" / "captured-card").exists())

    def test_bare_titles_still_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, _outside = self.make_repo(tmp)
            result = self.run_goc(cwd, "show", "real-card")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("# real-card", result.stdout)

            result = self.run_goc(cwd, "wait", "real-card", "--reason", "external", "--no-commit")
            self.assertEqual(0, result.returncode, msg=result.stderr)

            result = self.run_goc(cwd, "done", "real-card")
            self.assertEqual(0, result.returncode, msg=result.stderr)


NON_CANONICAL = ["real-card/", "./real-card", "real-card//", "././real-card"]


class CanonicalTitleSpellingTest(unittest.TestCase):
    """A title argument is the bare directory name — not every spelling of it.

    `Path` folds a trailing slash and a `./` prefix away, so these spellings
    resolve into the deck and passed the containment guard while still
    reading as a distinct identity to the callers that store and compare the
    raw string.
    """

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

    def make_deck(self, tmp: str, titles: tuple[str, ...] = ("real-card",)) -> Path:
        cwd = Path(tmp) / "repo"
        (cwd / ".game-of-cards").mkdir(parents=True)
        (cwd / ".game-of-cards" / "config.yaml").write_text("auto_commit: false\n")
        for title in titles:
            card_dir = cwd / ".game-of-cards" / "deck" / title
            card_dir.mkdir(parents=True)
            (card_dir / "README.md").write_text(
                "---\n"
                f"title: {title}\n"
                f"summary: {title}\n"
                "status: open\n"
                "stage: null\n"
                "contribution: low\n"
                "created: 2026-05-01\n"
                "closed_at: null\n"
                "human_gate: none\n"
                "advances: []\n"
                "advanced_by: []\n"
                "tags: [bug]\n"
                "definition_of_done: |\n"
                "  - [x] item-0\n"
                "---\n\n"
                f"# {title}\n"
            )
            (card_dir / "log.md").write_text("")
        return cwd

    def test_resolve_card_dir_refuses_non_canonical_spellings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp) / ".game-of-cards" / "deck"
            (deck / "real-card").mkdir(parents=True)
            orig = engine.DECK_DIR
            try:
                engine.DECK_DIR = deck
                for title in NON_CANONICAL:
                    with self.subTest(title=title), self.assertRaises(SystemExit) as ctx:
                        engine.resolve_card_dir(title)
                    self.assertEqual(2, ctx.exception.code)
                self.assertEqual(deck / "real-card", engine.resolve_card_dir("real-card"))
            finally:
                engine.DECK_DIR = orig

    def test_advance_refuses_non_canonical_self_spelling(self) -> None:
        """The self-edge guard is a string compare; `a/` must not slip past it."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp)
            readme = cwd / ".game-of-cards" / "deck" / "real-card" / "README.md"
            before = readme.read_text()
            result = self.run_goc(cwd, "advance", "real-card", "--by", "real-card/")
            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("invalid card title", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_advance_refuses_non_canonical_counterpart_spelling(self) -> None:
        """A `./`-spelled advancer must not land in the edge field verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp, ("real-card", "other-card"))
            deck = cwd / ".game-of-cards" / "deck"
            result = self.run_goc(cwd, "advance", "real-card", "--by", "./other-card")
            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertNotIn("./other-card", (deck / "real-card" / "README.md").read_text())
            self.assertIn("advances: []", (deck / "other-card" / "README.md").read_text())

    def test_done_bundle_refuses_one_card_under_two_spellings(self) -> None:
        """The duplicate-member guard is a string compare over raw arguments."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp)
            deck = cwd / ".game-of-cards" / "deck"
            result = self.run_goc(cwd, "done", "--bundle", "real-card", "real-card/")
            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("status: open", (deck / "real-card" / "README.md").read_text())
            self.assertEqual("", (deck / "real-card" / "log.md").read_text())

    def test_status_superseded_refuses_non_canonical_successor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp, ("real-card", "other-card"))
            deck = cwd / ".game-of-cards" / "deck"
            result = self.run_goc(cwd, "status", "real-card", "superseded", "--by", "other-card/")
            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("status: open", (deck / "real-card" / "README.md").read_text())
            self.assertNotIn("supersedes", (deck / "other-card" / "README.md").read_text())

    def test_read_verbs_still_accept_the_bare_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp)
            result = self.run_goc(cwd, "show", "real-card")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("# real-card", result.stdout)


if __name__ == "__main__":
    unittest.main()
