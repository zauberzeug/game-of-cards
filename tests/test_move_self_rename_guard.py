from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MoveSelfRenameGuardTest(unittest.TestCase):
    """`goc move <X> <X>` (old title == new title) must name the real
    condition, not report a phantom collision.

    Regression for goc-move-self-rename-reports-misleading-already-exists-error:
    `_cmd_move` had no identity guard, so a self-rename resolved src and dst to
    the same path and tripped the `dst.exists()` collision check, dying with
    `ERROR: ... already exists` — as if a *different* card occupied the slug.
    The fix adds an early `old_title == new_title` guard matching the
    identity-guard convention of `_cmd_advance` / `_cmd_status --by`.
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

    def _init_repo_with_card(self, cwd: Path, slug: str) -> None:
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@t.t"],
            ["git", "config", "user.name", "t"],
        ):
            subprocess.run(args, cwd=cwd, check=True, capture_output=True)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
        self.run_goc(cwd, "new", slug, "--contribution", "low", "--tag", "bug")

    def test_self_rename_errors_without_phantom_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            slug = "card-renamed-to-itself"
            self._init_repo_with_card(cwd, slug)

            mv = self.run_goc(cwd, "move", slug, slug)
            self.assertEqual(2, mv.returncode, msg=mv.stdout + mv.stderr)
            self.assertNotIn("already exists", mv.stderr)
            self.assertIn("itself", mv.stderr)
            # The card directory is untouched.
            self.assertTrue((cwd / ".game-of-cards" / "deck" / slug).is_dir())


if __name__ == "__main__":
    unittest.main()
