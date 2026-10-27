"""Regression: a verb that writes a card back restores a `created` stamp an agent rewrote away.

Card: goc-done-closes-cards-whose-created-stamp-was-overwritten.

`goc new` stamps `created:`; an agent that fills the scaffold by rewriting README.md wholesale,
without reading it first, drops the stamp. `publish`, `status`, `done` and `done --bundle` then
released such a card and only `goc validate` noticed, long after the session that could still say
when the card was filed. These verbs now restore the stamp from evidence — the earlier of the card
directory's birth time and the commit that first added README.md — and refuse when neither exists.
The current time is never written: it is not when the card was created.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMITTED_AT = "2026-01-02T03:04:05Z"

# What an agent writes when it fills a scaffold from scratch: the fields it remembers,
# without the generated `created:` stamp (and, outside `publish`, without `draft`).
REWRITTEN = """---
title: {title}
summary: "Rewritten wholesale by an agent."
status: open
human_gate: none
contribution: low
advances: []
advanced_by: []
tags: [story]
definition_of_done: |
  - [x] MECHANICAL: real criterion met
{draft}---

# {title}

Real authored body.
"""


def birth_time(path: Path) -> str | None:
    """The directory's creation time as the platform records it, or None."""
    birth = getattr(os.stat(path), "st_birthtime", None)
    if birth:
        return datetime.fromtimestamp(birth, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = subprocess.run(["stat", "-c", "%W", str(path)], capture_output=True, text=True, check=False)
    value = out.stdout.strip()
    if out.returncode != 0 or not value.isdigit() or int(value) == 0:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReleaseVerbsRestoreALostCreatedStampTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str, path_prefix: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "new":
            (cwd / ".game-of-cards" / "deck").mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        if path_prefix is not None:
            env["PATH"] = f"{path_prefix}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=120,
        )

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")

    def readme(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title / "README.md"

    def created(self, path: Path) -> str | None:
        for line in path.read_text().splitlines():
            if line.startswith("created:"):
                return line.split(":", 1)[1].strip().strip('"')
        return None

    def new_card(self, cwd: Path, title: str) -> Path:
        self.assert_ok(self.run_goc(cwd, "new", title, "--gate", "none", "--tag", "story",
                                    "--summary", "Filed by goc new."))
        path = self.readme(cwd, title)
        self.assertIsNotNone(self.created(path), "goc new stamps created")
        return path

    def rewrite_without_created(self, path: Path, *, keep_draft: bool) -> None:
        title = path.parent.name
        path.write_text(REWRITTEN.format(title=title, draft="draft: true\n" if keep_draft else ""))
        self.assertIsNone(self.created(path))

    def git(self, cwd: Path, *args: str, **env: str) -> None:
        subprocess.run(["git", "-c", "user.name=goc-test", "-c", "user.email=goc-test@example.invalid", *args],
                       cwd=cwd, check=True, capture_output=True, timeout=60, env={**os.environ, **env})

    def commit_cards(self, cwd: Path) -> None:
        when = COMMITTED_AT.replace("Z", "+00:00")
        self.git(cwd, "add", ".game-of-cards")
        self.git(cwd, "commit", "-q", "-m", "file cards", GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)

    VERBS = {
        "publish": (("publish", "card-a", "--no-commit"), True),
        "status active": (("status", "card-a", "active", "--no-commit"), False),
        "status blocked": (("status", "card-a", "blocked", "--no-commit"), False),
        "done": (("done", "card-a"), False),
    }

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_each_verb_restores_created_from_the_commit_that_added_the_card(self) -> None:
        for name, (argv, keep_draft) in self.VERBS.items():
            with self.subTest(verb=name), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                self.git(cwd, "init", "-q")
                path = self.new_card(cwd, "card-a")
                self.commit_cards(cwd)
                self.rewrite_without_created(path, keep_draft=keep_draft)

                result = self.run_goc(cwd, *argv)

                self.assert_ok(result)
                # the commit predates the directory's birth in this checkout: the earlier bound wins
                self.assertEqual(self.created(path), COMMITTED_AT)
                self.assertIn(f"created: restored {COMMITTED_AT}", result.stdout)
                self.assert_ok(self.run_goc(cwd, "validate"))

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_done_bundle_restores_every_card_it_closes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.git(cwd, "init", "-q")
            paths = [self.new_card(cwd, title) for title in ("card-a", "card-b")]
            self.commit_cards(cwd)
            for path in paths:
                self.rewrite_without_created(path, keep_draft=False)

            self.assert_ok(self.run_goc(cwd, "done", "--bundle", "card-a", "card-b"))

            for path in paths:
                self.assertEqual(self.created(path), COMMITTED_AT, path.parent.name)
            self.assert_ok(self.run_goc(cwd, "validate"))

    def test_outside_git_the_card_directory_birth_time_restores_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            path = self.new_card(cwd, "card-a")
            born = birth_time(path.parent)
            if born is None:
                self.skipTest("this filesystem records no directory birth time")
            self.rewrite_without_created(path, keep_draft=False)
            time.sleep(1.1)  # a clock-based stamp would now differ from the birth time

            result = self.run_goc(cwd, "done", "card-a")

            self.assert_ok(result)
            self.assertEqual(self.created(path), born)

    @unittest.skipIf(hasattr(os.stat("."), "st_birthtime"), "birth time comes from os.stat on this platform")
    def test_without_any_evidence_the_verb_refuses_and_leaves_the_card_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as bin_dir:
            cwd = Path(tmp)
            fake_stat = Path(bin_dir) / "stat"
            fake_stat.write_text("#!/bin/sh\nexit 1\n")
            fake_stat.chmod(fake_stat.stat().st_mode | stat.S_IXUSR)
            path = self.new_card(cwd, "card-a")
            self.rewrite_without_created(path, keep_draft=False)
            before = path.read_text()

            result = self.run_goc(cwd, "done", "card-a", path_prefix=Path(bin_dir))

            self.assertEqual(result.returncode, 2, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            self.assertIn("card-a: created:", result.stderr)
            self.assertIn("never from the current time", result.stderr)
            self.assertEqual(path.read_text(), before, "a refused verb must not mutate the card")

    def test_a_card_that_keeps_its_stamp_is_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            path = self.new_card(cwd, "card-a")
            stamped = self.created(path)
            text = path.read_text()
            text = text.replace("- [ ] (replace with real criteria)", "- [x] MECHANICAL: real criterion met")
            path.write_text(text.replace("(write the design doc here)", "Real authored body."))

            result = self.run_goc(cwd, "done", "card-a")

            self.assert_ok(result)
            self.assertEqual(self.created(path), stamped)
            self.assertNotIn("created: restored", result.stdout)

    def test_new_tells_the_agent_to_edit_the_scaffold_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_goc(Path(tmp), "new", "card-a", "--gate", "none")
            self.assert_ok(result)
            self.assertIn("keep the generated frontmatter", result.stdout)


if __name__ == "__main__":
    unittest.main()
