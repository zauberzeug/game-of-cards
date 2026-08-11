"""Regression: deck resolution from a subdirectory of the deck-owning repo.

`_resolve_deck_root` (`goc/engine.py`) walks from cwd to the nearest ancestor
carrying `.game-of-cards/`, shipped in 3e17e3b3. Its sibling module
`tests/test_new_resolves_existing_deck_root.py` pins the `goc new` write path
across workspace and foreign-tree shapes; this module pins the half nothing
covered — the READ path.

Every aggregate reader must address the real deck when run below the deck
root, because the pre-fix failure is silent: readers exit 0 with zero cards,
which is indistinguishable from a drained deck. A downstream consumer's
refine pass took exactly that reading and treated a full deck as done.

The read-side boundary is pinned too: a nested *foreign* git tree must not
inherit the enclosing repo's deck, and no reader may scaffold anything at cwd
while finding that out.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ZERO_CARD_NOTICE = "No cards found in"


class SubdirectoryDeckResolutionTest(unittest.TestCase):
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

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode, 0, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )

    def make_repo(self, root: Path) -> None:
        """A git repo whose root owns the deck — the canonical consumer shape."""
        (root / ".game-of-cards" / "deck").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    def add_card(self, root: Path, title: str) -> None:
        """File and publish an authored card at the deck root."""
        self.assert_ok(
            self.run_goc(
                root, "new", title,
                "--gate", "none", "--tag", "infra",
                "--summary", "A fixture card standing in for a real deck entry.",
                "--no-commit",
            )
        )
        path = root / ".game-of-cards" / "deck" / title / "README.md"
        path.write_text(
            path.read_text()
            .replace("- [ ] (replace with real criteria)", "- [ ] MECHANICAL: a real criterion")
            .replace("(write the design doc here)", "A real body.")
        )
        self.assert_ok(self.run_goc(root, "publish", title, "--no-commit"))

    def test_readers_from_subdirectory_address_the_real_deck(self) -> None:
        """Every aggregate reader resolves upward, not to cwd."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            nested = repo / "src" / "deep" / "nested"
            nested.mkdir(parents=True)
            self.make_repo(repo)
            self.add_card(repo, "fixture-card")

            # --status all --json and --ready --json both carry the card.
            for args in (("--status", "all", "--json"), ("--ready", "--json")):
                with self.subTest(reader=" ".join(args)):
                    result = self.run_goc(nested, *args)
                    self.assert_ok(result)
                    self.assertEqual(
                        ["fixture-card"], [c["title"] for c in json.loads(result.stdout)]
                    )

            # validate reports the card, not an empty deck. The zero-card
            # notice is a stderr-only false-green guard, so check both streams.
            result = self.run_goc(nested, "validate")
            self.assert_ok(result)
            self.assertIn("fixture-card", result.stdout)
            self.assertNotIn(ZERO_CARD_NOTICE, result.stdout + result.stderr)

            # quality-pass surveys the real deck's cards.
            result = self.run_goc(nested, "quality-pass")
            self.assert_ok(result)
            self.assertIn("1 card", result.stdout)

            # show addresses the card by title without a path.
            result = self.run_goc(nested, "show", "fixture-card")
            self.assert_ok(result)
            self.assertIn("title: fixture-card", result.stdout)

            # No reader scaffolded a shadow deck beside itself.
            self.assertFalse((nested / ".game-of-cards").exists())

    def test_new_from_subdirectory_files_into_the_repo_root_deck(self) -> None:
        """The write half, in the shape the read half fails in: a plain
        subdirectory of the git repo that owns the deck at its root."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            nested = repo / "src" / "deep"
            nested.mkdir(parents=True)
            self.make_repo(repo)

            result = self.run_goc(
                nested, "new", "filed-from-a-subdirectory", "--gate", "none", "--tag", "infra"
            )

            self.assert_ok(result)
            self.assertTrue(
                (
                    repo / ".game-of-cards" / "deck" / "filed-from-a-subdirectory" / "README.md"
                ).is_file()
            )
            self.assertFalse((nested / ".game-of-cards").exists())
            self.assertFalse((repo / "src" / ".game-of-cards").exists())

    def test_readers_in_a_nested_foreign_tree_do_not_inherit_the_enclosing_deck(self) -> None:
        """The walk stops before a different git working tree — on the read
        path too. A vendored repo must not read its host's deck."""
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "outer"
            inner = outer / "vendor" / "inner"
            inner.mkdir(parents=True)
            self.make_repo(outer)
            self.add_card(outer, "host-repo-card")
            subprocess.run(["git", "init", "-q"], cwd=inner, check=True)

            result = self.run_goc(inner, "--status", "all", "--json")
            self.assert_ok(result)
            self.assertEqual([], json.loads(result.stdout))

            result = self.run_goc(inner, "validate")
            self.assert_ok(result)
            self.assertIn(ZERO_CARD_NOTICE, result.stderr)
            self.assertNotIn("host-repo-card", result.stdout + result.stderr)

            result = self.run_goc(inner, "show", "host-repo-card")
            self.assertNotEqual(0, result.returncode)

            # Falling back to cwd is a read fallback, never a scaffold.
            self.assertFalse((inner / ".game-of-cards").exists())


if __name__ == "__main__":
    unittest.main()
