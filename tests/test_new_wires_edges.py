from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NewWiresEdgesTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "new":
            (cwd / ".game-of-cards" / "deck").mkdir(parents=True, exist_ok=True)
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

    def assert_goc_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
        )

    def readme(self, cwd: Path, title: str) -> str:
        return (cwd / ".game-of-cards" / "deck" / title / "README.md").read_text()

    def test_new_repeatable_edge_flags_write_both_sides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for title in ("target-one", "target-two", "parent-one", "parent-two"):
                self.assert_goc_ok(self.run_goc(cwd, "new", title, "--gate", "none", "--tag", "story"))

            created = self.run_goc(
                cwd,
                "new",
                "linked-card",
                "--gate",
                "none",
                "--tag",
                "story",
                "--advances",
                "target-one",
                "--advances",
                "target-two",
                "--advanced-by",
                "parent-one",
                "--advanced-by",
                "parent-two",
            )

            self.assert_goc_ok(created)
            linked = self.readme(cwd, "linked-card")
            self.assertIn("advances:\n  - target-one\n  - target-two\n", linked)
            self.assertIn("advanced_by:\n  - parent-one\n  - parent-two\n", linked)
            self.assertIn("advanced_by:\n  - linked-card\n", self.readme(cwd, "target-one"))
            self.assertIn("advanced_by:\n  - linked-card\n", self.readme(cwd, "target-two"))
            self.assertIn("advances:\n  - linked-card\n", self.readme(cwd, "parent-one"))
            self.assertIn("advances:\n  - linked-card\n", self.readme(cwd, "parent-two"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_new_missing_edge_target_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "new", "known-card", "--gate", "none", "--tag", "story"))

            result = self.run_goc(
                cwd,
                "new",
                "missing-link-card",
                "--gate",
                "none",
                "--tag",
                "story",
                "--advances",
                "known-card",
                "--advanced-by",
                "missing-card",
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("referenced card(s) not found: missing-card", result.stderr)
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "missing-link-card").exists())
            self.assertNotIn("missing-link-card", self.readme(cwd, "known-card"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_new_cycle_rejection_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "new", "child-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "advance", "child-card", "--by", "parent-card", "--no-commit"))

            result = self.run_goc(
                cwd,
                "new",
                "cycle-card",
                "--gate",
                "none",
                "--tag",
                "story",
                "--advances",
                "parent-card",
                "--advanced-by",
                "child-card",
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("would create a cycle in the advances graph", result.stderr)
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "cycle-card").exists())
            self.assertNotIn("cycle-card", self.readme(cwd, "parent-card"))
            self.assertNotIn("cycle-card", self.readme(cwd, "child-card"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_new_help_lists_edge_flags_with_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_goc(Path(tmp), "new", "--help")

            self.assert_goc_ok(result)
            self.assertIn("--advances TITLE", result.stdout)
            self.assertIn("--advanced-by TITLE", result.stdout)
            self.assertIn("--commit", result.stdout)
            self.assertIn("--no-commit", result.stdout)
            self.assertIn("goc new child-card --advances parent-card", result.stdout)
            self.assertIn("goc new child-card --advanced-by parent-card", result.stdout)

    def _init_git_repo(self, cwd: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)
        # Identity required for commits in CI environments that don't ship
        # a default git user.
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=cwd, check=True)

    def _git_status(self, cwd: Path) -> str:
        return subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def test_new_with_commit_flag_commits_both_endpoints_and_new_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)

            # Scaffold the parent card and commit it so the next `goc new
            # --advances parent --commit` runs against a clean worktree.
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "parent"], cwd=cwd, check=True)

            # The defect: without --commit, the parent's edge mutation
            # lingers as ambient ` M` in the worktree.
            self.assertEqual(self._git_status(cwd), "")
            self.assert_goc_ok(self.run_goc(
                cwd, "new", "child-card",
                "--gate", "none", "--tag", "story",
                "--advances", "parent-card",
                "--commit",
            ))
            status = self._git_status(cwd)

            # --commit closes the half-edge: the parent's README mutation
            # AND the new card directory are committed atomically.
            self.assertNotIn("parent-card/README.md", status)
            self.assertNotIn("child-card", status)
            self.assertEqual(status, "")

    def test_new_default_does_not_commit(self) -> None:
        # Option C's contract: the default `goc new` (no --commit flag)
        # preserves today's scaffold-then-fill-in behavior — neither the
        # new card directory nor any edge endpoints are committed.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "parent"], cwd=cwd, check=True)

            self.assert_goc_ok(self.run_goc(
                cwd, "new", "child-card",
                "--gate", "none", "--tag", "story",
                "--advances", "parent-card",
            ))
            status = self._git_status(cwd)
            # The default leaves the new card untracked AND the parent
            # README as modified — both must be present for the option C
            # contract to hold.
            self.assertIn("child-card", status)
            self.assertIn("parent-card/README.md", status)

    # The release verbs below are the auto-committing step that follows a
    # default `goc new` filing: `goc publish` and the `goc status active`
    # claim. Card: publish-and-claim-commit-a-new-card-without-the-parent-edge-goc-new-wrote

    _RELEASES = {
        "publish": ("publish", "child-card"),
        "claim": ("status", "child-card", "active"),
    }

    def _author(self, cwd: Path, title: str) -> None:
        readme = cwd / ".game-of-cards" / "deck" / title / "README.md"
        readme.write_text(
            readme.read_text()
            .replace("- [ ] (replace with real criteria)", "- [ ] MECHANICAL: real criterion")
            .replace("(write the design doc here)", "Authored body.")
        )

    def _committed_parent(self, cwd: Path) -> None:
        """A git repo whose HEAD holds one authored, published `parent-card`."""
        self._init_git_repo(cwd)
        self.assert_goc_ok(self.run_goc(
            cwd, "new", "parent-card", "--summary", "parent", "--gate", "none", "--tag", "story", "--commit",
        ))
        self._author(cwd, "parent-card")
        self.assert_goc_ok(self.run_goc(cwd, "publish", "parent-card"))
        self.assertEqual(self._git_status(cwd), "")

    def _file_child(self, cwd: Path, *wiring: str) -> None:
        """`goc new child-card <wiring>` without --commit, then author it."""
        self.assert_goc_ok(self.run_goc(
            cwd, "new", "child-card", *wiring, "--summary", "child", "--gate", "none", "--tag", "story",
        ))
        self._author(cwd, "child-card")

    def _head_readme(self, cwd: Path, title: str) -> str:
        return subprocess.run(
            ["git", "show", f"HEAD:.game-of-cards/deck/{title}/README.md"],
            cwd=cwd, check=True, capture_output=True, text=True,
        ).stdout

    def _validate_fresh_clone(self, cwd: Path) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as clone_tmp:
            clone = Path(clone_tmp) / "clone"
            subprocess.run(["git", "clone", "-q", str(cwd), str(clone)], check=True, capture_output=True)
            return self.run_goc(clone, "validate", "--quiet")

    def test_release_verbs_commit_the_edge_half_goc_new_left_uncommitted(self) -> None:
        for wire, parent_field in (("--advances", "advanced_by"), ("--advanced-by", "advances")):
            for release, verb in self._RELEASES.items():
                with self.subTest(wire=wire, release=release), tempfile.TemporaryDirectory() as tmp:
                    cwd = Path(tmp)
                    self._committed_parent(cwd)
                    self._file_child(cwd, wire, "parent-card")
                    self.assertIn("parent-card/README.md", self._git_status(cwd))

                    released = self.run_goc(cwd, *verb)

                    self.assert_goc_ok(released)
                    self.assertIn("also committed parent-card", released.stdout)
                    self.assertEqual(self._git_status(cwd), "")
                    self.assertIn(f"{parent_field}:\n  - child-card\n", self._head_readme(cwd, "parent-card"))
                    self.assert_goc_ok(self._validate_fresh_clone(cwd))

    def test_release_commit_takes_only_the_readme_of_a_tracked_counterpart(self) -> None:
        # The edge lives in the README; the counterpart's journal is its own
        # owner's uncommitted work and stays out of someone else's release.
        for release, verb in self._RELEASES.items():
            with self.subTest(release=release), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                self._committed_parent(cwd)
                parent_log = cwd / ".game-of-cards" / "deck" / "parent-card" / "log.md"
                parent_log.write_text("## parent's own uncommitted journal entry\n")
                self._file_child(cwd, "--advances", "parent-card")

                self.assert_goc_ok(self.run_goc(cwd, *verb))

                self.assertEqual(self._git_status(cwd), " M .game-of-cards/deck/parent-card/log.md\n")
                self.assert_goc_ok(self._validate_fresh_clone(cwd))

    def test_release_commit_leaves_out_a_counterpart_head_already_agrees_with(self) -> None:
        # `--commit` committed both halves at filing time, so the parent's
        # later, unrelated README edit has no edge reason to join the claim.
        for release, verb in self._RELEASES.items():
            with self.subTest(release=release), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                self._committed_parent(cwd)
                self._file_child(cwd, "--advances", "parent-card", "--commit")
                parent = cwd / ".game-of-cards" / "deck" / "parent-card" / "README.md"
                parent.write_text(parent.read_text() + "\nAn unrelated edit in progress.\n")

                released = self.run_goc(cwd, *verb)

                self.assert_goc_ok(released)
                self.assertNotIn("also committed", released.stdout)
                self.assertEqual(self._git_status(cwd), " M .game-of-cards/deck/parent-card/README.md\n")
                self.assertNotIn("An unrelated edit in progress.", self._head_readme(cwd, "parent-card"))

    def test_release_commit_follows_counterparts_to_cards_head_has_not_seen(self) -> None:
        # The parent's README is committed whole, so it brings its edge to
        # `sibling-card` (authored, released with --no-commit, never committed)
        # and that card must come along, log.md and all, for HEAD to validate.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._committed_parent(cwd)
            self.assert_goc_ok(self.run_goc(
                cwd, "new", "sibling-card", "--advances", "parent-card",
                "--summary", "sibling", "--gate", "none", "--tag", "story",
            ))
            self._author(cwd, "sibling-card")
            self.assert_goc_ok(self.run_goc(cwd, "publish", "sibling-card", "--no-commit"))
            self._file_child(cwd, "--advances", "parent-card")

            released = self.run_goc(cwd, "publish", "child-card")

            self.assert_goc_ok(released)
            self.assertIn("also committed parent-card, sibling-card", released.stdout)
            self.assertEqual(self._git_status(cwd), "")
            self.assert_goc_ok(self._validate_fresh_clone(cwd))

    def test_release_commit_never_adds_a_draft_counterpart(self) -> None:
        # A draft is never committed implicitly. The dangling edge this leaves
        # in HEAD is the open decision on
        # auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft;
        # this pins only that the draft guard still holds.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            self._file_child(cwd, "--advances", "parent-card")

            released = self.run_goc(cwd, "publish", "child-card")

            self.assert_goc_ok(released)
            self.assertIn("  committed", released.stdout)
            self.assertNotIn("also committed", released.stdout)
            self.assertEqual(self._git_status(cwd), "?? .game-of-cards/deck/parent-card/\n")

    def test_new_commit_and_no_commit_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_goc(
                cwd, "new", "card-x",
                "--gate", "none", "--tag", "story",
                "--commit", "--no-commit",
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("pass only one of --commit / --no-commit", result.stderr)
            # The flag conflict aborts BEFORE any disk write — no card dir
            # is left behind.
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "card-x").exists())


if __name__ == "__main__":
    unittest.main()
