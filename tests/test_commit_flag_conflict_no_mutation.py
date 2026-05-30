from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CARD_TEMPLATE = """---
title: {title}
summary: ""
status: open
stage: null
contribution: medium
created: "2026-05-30T00:00:00Z"
closed_at: null
human_gate: {gate}
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] (replace)
---

# {title}

body
"""


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CommitFlagConflictNoMutationTest(unittest.TestCase):
    """Mutating verbs (`status`, `wait`, `advance`, `unadvance`, `decide`)
    must reject a `--commit --no-commit` flag conflict BEFORE writing
    any card to disk. The early-validation invariant is what keeps a
    CLI usage error from leaving a card half-mutated without an
    auto-commit.
    """

    def _run(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env.pop("GOC_WORKTREE_DECK", None)
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=str(cwd),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _setup(self, tmp: Path, *, gate: str = "none") -> None:
        (tmp / "pyproject.toml").write_text('[project]\nname = "stub"\nversion = "0"\n')
        deck = tmp / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        for title in ("probe-target", "probe-target-2"):
            card_dir = deck / title
            card_dir.mkdir()
            (card_dir / "README.md").write_text(
                CARD_TEMPLATE.format(title=title, gate=gate)
            )
            (card_dir / "log.md").write_text("")

    def _assert_conflict_leaves_file_untouched(
        self,
        cwd: Path,
        watched: Path,
        verb_args: list[str],
        label: str,
    ) -> None:
        before = _hash(watched)
        res = self._run(cwd, *verb_args, "--commit", "--no-commit")
        after = _hash(watched)
        self.assertEqual(
            res.returncode,
            2,
            msg=f"[{label}] expected exit 2 on flag conflict; got {res.returncode}\n"
                f"stdout: {res.stdout}\nstderr: {res.stderr}",
        )
        self.assertEqual(
            before,
            after,
            msg=f"[{label}] {watched} mutated before flag-conflict check ran\n"
                f"stderr: {res.stderr}",
        )
        self.assertIn(
            "pass only one of --commit / --no-commit",
            res.stderr,
            msg=f"[{label}] missing canonical flag-conflict error\nstderr: {res.stderr}",
        )

    def test_status_leaves_card_untouched_on_flag_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._setup(tmp)
            readme = tmp / ".game-of-cards" / "deck" / "probe-target" / "README.md"
            self._assert_conflict_leaves_file_untouched(
                tmp, readme, ["status", "probe-target", "active"], "status"
            )

    def test_wait_leaves_card_untouched_on_flag_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._setup(tmp)
            readme = tmp / ".game-of-cards" / "deck" / "probe-target" / "README.md"
            self._assert_conflict_leaves_file_untouched(
                tmp,
                readme,
                ["wait", "probe-target", "--reason", "external"],
                "wait",
            )

    def test_advance_leaves_card_untouched_on_flag_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._setup(tmp)
            readme = tmp / ".game-of-cards" / "deck" / "probe-target" / "README.md"
            self._assert_conflict_leaves_file_untouched(
                tmp,
                readme,
                ["advance", "probe-target", "--by", "probe-target-2"],
                "advance",
            )

    def test_unadvance_leaves_card_untouched_on_flag_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._setup(tmp)
            # Establish a baseline edge so unadvance has something to remove.
            pre = self._run(
                tmp, "advance", "probe-target", "--by", "probe-target-2"
            )
            self.assertEqual(pre.returncode, 0, msg=pre.stderr)
            readme = tmp / ".game-of-cards" / "deck" / "probe-target" / "README.md"
            self._assert_conflict_leaves_file_untouched(
                tmp,
                readme,
                ["unadvance", "probe-target", "--by", "probe-target-2"],
                "unadvance",
            )

    def test_decide_leaves_card_and_log_untouched_on_flag_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self._setup(tmp, gate="decision")
            card_dir = tmp / ".game-of-cards" / "deck" / "probe-target"
            readme = card_dir / "README.md"
            log_path = card_dir / "log.md"
            readme_before = _hash(readme)
            log_before = _hash(log_path)
            res = self._run(
                tmp,
                "decide",
                "probe-target",
                "--decision",
                "go with X",
                "--because",
                "simplest",
                "--commit",
                "--no-commit",
            )
            self.assertEqual(
                res.returncode,
                2,
                msg=f"expected exit 2; stdout={res.stdout} stderr={res.stderr}",
            )
            self.assertEqual(readme_before, _hash(readme),
                             msg=f"decide mutated README before flag-conflict check\nstderr: {res.stderr}")
            self.assertEqual(log_before, _hash(log_path),
                             msg=f"decide mutated log.md before flag-conflict check\nstderr: {res.stderr}")


if __name__ == "__main__":
    unittest.main()
