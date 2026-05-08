"""Regression guard: validate_plugin_mirror_parity detects claude-plugin/ drift.

Patches goc.engine.REPO_ROOT directly so the test never spawns a subprocess and
never risks shadowing the real goc package via Python's cwd-first import search.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import goc.engine as eng

ROOT = Path(__file__).resolve().parents[1]


def _check(cwd: Path) -> list[str]:
    old = eng.REPO_ROOT
    try:
        eng.REPO_ROOT = cwd
        return eng.validate_plugin_mirror_parity()
    finally:
        eng.REPO_ROOT = old


def _sync_tree(cwd: Path, skill_content: str = "# test skill\n", hook_content: str = "# hook\n") -> None:
    """Populate a minimal in-sync plugin mirror structure under cwd."""
    # pair 1: goc/templates/skills ↔ claude-plugin/skills
    for base in (
        cwd / "goc" / "templates" / "skills" / "foo-skill",
        cwd / "claude-plugin" / "skills" / "foo-skill",
        cwd / "claude-plugin" / "goc" / "templates" / "skills" / "foo-skill",
    ):
        base.mkdir(parents=True, exist_ok=True)
        (base / "SKILL.md").write_text(skill_content)

    # pairs 2+3: hook files
    for hook in ("deck_prompt_router.py", "deck_session_start.py"):
        for base in (
            cwd / "goc" / "templates" / "hooks",
            cwd / "claude-plugin" / "hooks",
            cwd / "claude-plugin" / "goc" / "templates" / "hooks",
        ):
            base.mkdir(parents=True, exist_ok=True)
            (base / hook).write_text(hook_content)


class PluginMirrorParityTest(unittest.TestCase):
    def test_no_plugin_dir_skips_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], _check(Path(tmp)))

    def test_in_sync_mirrors_produce_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)
            self.assertEqual([], _check(cwd))

    def test_drifted_skills_mirror_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _sync_tree(cwd)

            # deliberately break pair 1 (skills mirror)
            (cwd / "claude-plugin" / "skills" / "foo-skill" / "SKILL.md").write_text("# drifted\n")

            errors = _check(cwd)
            self.assertEqual(1, len(errors), msg=f"expected 1 error, got: {errors}")
            self.assertIn("plugin mirror drift", errors[0])
            self.assertIn("foo-skill", errors[0])
            self.assertIn("SKILL.md", errors[0])
            self.assertIn("differs", errors[0])

    def test_missing_plugin_skills_dir_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # only create source, not the mirror
            (cwd / "goc" / "templates" / "skills" / "foo-skill").mkdir(parents=True)
            (cwd / "goc" / "templates" / "skills" / "foo-skill" / "SKILL.md").write_text("# skill\n")
            (cwd / "claude-plugin").mkdir(parents=True)  # plugin root exists but skills missing

            errors = _check(cwd)
            self.assertTrue(any("claude-plugin/skills" in e and "missing" in e for e in errors),
                            msg=f"expected missing-dir error, got: {errors}")

    def test_real_repo_passes(self) -> None:
        errors = _check(ROOT)
        self.assertEqual([], errors, msg=f"plugin mirror drift in the repo itself: {errors}")


if __name__ == "__main__":
    unittest.main()
